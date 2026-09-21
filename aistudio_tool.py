#!/usr/bin/env python3
"""
AI Studio / Gemini Tool Runner & Search-Replace Orchestrator
------------------------------------------------------------
Processes raw AI Studio / Gemini outputs with full atomic safety.
Supports:
 - Search-and-replace & whole file writes
 - Terminal command execution with confirmation prompts
 - Recursive unwrapping of nested 'queries' payloads
 - Smart Path Healing (finds files across subdirectories)
"""

import os
import sys
import json
import argparse
import difflib
import subprocess
from typing import List, Dict, Any, Tuple, Optional


def extract_json_blocks(raw_text: str) -> List[Dict[str, Any]]:
    """Extracts all tool JSON objects, unwrapping nested strings/queries."""
    results = []

    def _scan_raw_string(text: str) -> List[Any]:
        found = []
        decoder = json.JSONDecoder()
        idx = 0
        n = len(text)
        while idx < n:
            if text[idx] in ('{', '['):
                try:
                    obj, end_idx = decoder.raw_decode(text, idx)
                    found.append(obj)
                    idx = end_idx
                    continue
                except json.JSONDecodeError:
                    pass
            idx += 1
        return found

    def _extract_recursive(data: Any):
        if isinstance(data, str):
            s = data.strip()
            if not s:
                return
            try:
                parsed = json.loads(s)
                _extract_recursive(parsed)
                return
            except (json.JSONDecodeError, TypeError):
                pass

            try:
                parsed = json.loads(f"[{s}]")
                _extract_recursive(parsed)
                return
            except (json.JSONDecodeError, TypeError):
                pass

            for b in _scan_raw_string(s):
                _extract_recursive(b)

        elif isinstance(data, dict):
            # Check for file patch OR terminal command
            is_file_tool = any(k in data for k in ("filepath", "path", "file", "filename"))
            is_cmd_tool = any(k in data for k in ("command", "cmd", "bash", "shell"))

            if is_file_tool or is_cmd_tool:
                results.append(data)
            else:
                for v in data.values():
                    _extract_recursive(v)

        elif isinstance(data, list):
            for item in data:
                _extract_recursive(item)

    for initial_obj in _scan_raw_string(raw_text):
        _extract_recursive(initial_obj)

    return results


def find_file_on_disk(base_dir: str, filepath: str) -> Optional[str]:
    """Resolves file path with auto-healing if Gemini omitted root folders."""
    direct = os.path.normpath(os.path.join(base_dir, filepath))
    if os.path.exists(direct) and os.path.isfile(direct):
        return direct

    norm_suffix = os.path.normpath(filepath).lower()
    candidates = []

    for root, _, files in os.walk(base_dir):
        if any(ign in root for ign in (".git", "node_modules", "Saved", "Cooked", "__pycache__", ".venv")):
            continue
        for file in files:
            full_path = os.path.normpath(os.path.join(root, file))
            if full_path.lower().endswith(norm_suffix):
                candidates.append(full_path)

    if len(candidates) == 1:
        return candidates[0]
    elif len(candidates) > 1:
        return min(candidates, key=len)

    return None


def normalize_newlines(text: str) -> Tuple[str, str]:
    if "\r\n" in text:
        return text.replace("\r\n", "\n"), "\r\n"
    return text, "\n"


def run_terminal_command(cmd_str: str, base_dir: str = ".", auto_approve: bool = False) -> Dict[str, Any]:
    """Executes system commands strictly in base_dir, preserving local paths and forcing UTF-8 mode."""
    print("\n" + "=" * 70)
    print(" GEMINI SYSTEM COMMAND REQUEST")
    print("=" * 70)
    print(cmd_str.strip())
    print("=" * 70)

    if not auto_approve:
        try:
            choice = input("\n[?] Execute this command on your machine? [y/N]: ").strip().lower()
            if choice not in ('y', 'yes'):
                return {"status": "cancelled", "command": cmd_str, "stdout": "", "stderr": "User declined.", "exit_code": -1}
        except KeyboardInterrupt:
            return {"status": "cancelled", "command": cmd_str, "stdout": "", "stderr": "Aborted.", "exit_code": -1}

    abs_base = os.path.abspath(base_dir)
    print(f"\n[*] Executing in: {abs_base} ...")

    # Set UTF-8 environment so Windows never defaults to cp1252
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    temp_script = None
    exec_cmd = cmd_str
    if "\n" in cmd_str and cmd_str.strip().startswith("python -c"):
        raw_code = cmd_str.strip()[len("python -c"):].strip().strip('"\'')
        temp_script = os.path.join(abs_base, "._gemini_exec_temp.py")
        with open(temp_script, "w", encoding="utf-8") as f:
            f.write(raw_code)
        # -X utf8 forces Python to default to UTF-8 encoding across all open() calls
        exec_cmd = f'python -X utf8 "._gemini_exec_temp.py"'

    try:
        proc = subprocess.run(
            exec_cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            cwd=abs_base,
            env=env,
            encoding="utf-8",
            errors="replace"  # Prevents crash if stdout contains odd binary bytes
        )
        output = proc.stdout.strip()
        errors = proc.stderr.strip()
    finally:
        if temp_script and os.path.exists(temp_script):
            try:
                os.remove(temp_script)
            except OSError:
                pass

    print("\n--- Command Output ---")
    if output:
        print(output)
    if errors:
        print(f"[STDERR]:\n{errors}")
    print(f"--- Exit Code: {proc.returncode} ---\n")

    return {
        "status": "success" if proc.returncode == 0 else "failed",
        "command": cmd_str,
        "stdout": output,
        "stderr": errors,
        "exit_code": proc.returncode
    }


def execute_patches(
    patches: List[Dict[str, Any]], 
    base_dir: str = ".", 
    dry_run: bool = False,
    auto_approve_cmd: bool = False
) -> Dict[str, Any]:
    """Executes all tool operations (edits and commands)."""
    file_patches = [p for p in patches if any(k in p for k in ("filepath", "path", "file", "filename"))]
    cmd_patches = [p for p in patches if any(k in p for k in ("command", "cmd", "bash", "shell"))]

    # Handle commands
    if cmd_patches:
        cmd_results = []
        for p in cmd_patches:
            cmd = p.get("command") or p.get("cmd") or p.get("bash") or p.get("shell")
            if cmd:
                res = run_terminal_command(cmd, auto_approve=auto_approve_cmd)
                cmd_results.append(res)
        return {
            "status": "success",
            "type": "command_execution",
            "commands": cmd_results,
            "modified_files": []
        }

    # Handle file modifications
    file_buffers: Dict[str, str] = {}
    file_line_endings: Dict[str, str] = {}
    file_original_content: Dict[str, Optional[str]] = {}
    file_ops_count: Dict[str, int] = {}
    errors: List[Dict[str, Any]] = []

    for i, patch in enumerate(file_patches, start=1):
        patch_id = i
        raw_filepath = patch.get("filepath") or patch.get("path") or patch.get("file")
        search_str = patch.get("search") or patch.get("find") or patch.get("old_str")
        
        # Support 'content' as 'replace' if 'search' is present
        replace_str = (
            patch.get("replace") or 
            patch.get("replacement") or 
            patch.get("new_str") or 
            (patch.get("content") if search_str is not None else None)
        )
        full_content = patch.get("content") if search_str is None else None

        if not raw_filepath:
            continue

        resolved_path = find_file_on_disk(base_dir, raw_filepath)
        if not resolved_path:
            if full_content is not None and search_str is None:
                resolved_path = os.path.normpath(os.path.join(base_dir, raw_filepath))
            else:
                errors.append({
                    "patch_index": patch_id,
                    "filepath": raw_filepath,
                    "reason": f"File could not be found anywhere in workspace: '{raw_filepath}'"
                })
                continue

        # Whole-file write
        if full_content is not None and search_str is None:
            norm_content, nl_style = normalize_newlines(full_content)
            if resolved_path not in file_original_content:
                if os.path.exists(resolved_path):
                    try:
                        with open(resolved_path, "r", encoding="utf-8-sig") as f:
                            raw = f.read()
                        orig_norm, orig_nl = normalize_newlines(raw)
                        file_original_content[resolved_path] = orig_norm
                        file_line_endings[resolved_path] = orig_nl
                    except Exception as e:
                        errors.append({"patch_index": patch_id, "filepath": raw_filepath, "reason": str(e)})
                        continue
                else:
                    file_original_content[resolved_path] = None
                    file_line_endings[resolved_path] = "\n"

            file_buffers[resolved_path] = norm_content
            file_ops_count[resolved_path] = file_ops_count.get(resolved_path, 0) + 1
            continue

        # Search-and-replace
        if search_str is not None and replace_str is not None:
            if resolved_path not in file_buffers:
                try:
                    with open(resolved_path, "r", encoding="utf-8-sig") as f:
                        raw_content = f.read()
                except Exception as e:
                    errors.append({"patch_index": patch_id, "filepath": raw_filepath, "reason": str(e)})
                    continue

                norm_content, nl_style = normalize_newlines(raw_content)
                file_buffers[resolved_path] = norm_content
                file_line_endings[resolved_path] = nl_style
                file_original_content[resolved_path] = norm_content
                file_ops_count[resolved_path] = 0

            norm_search, _ = normalize_newlines(search_str)
            norm_replace, _ = normalize_newlines(replace_str)
            current_content = file_buffers[resolved_path]

            count = current_content.count(norm_search)
            if count == 0:
                search_head = norm_search.strip().splitlines()
                preview = search_head[0][:80] if search_head else "(empty)"
                errors.append({
                    "patch_index": patch_id,
                    "filepath": raw_filepath,
                    "reason": f"Search block not found. Starts with: '{preview}'"
                })
            elif count > 1:
                errors.append({
                    "patch_index": patch_id,
                    "filepath": raw_filepath,
                    "reason": f"Ambiguous match: found {count} occurrences."
                })
            else:
                file_buffers[resolved_path] = current_content.replace(norm_search, norm_replace, 1)
                file_ops_count[resolved_path] += 1

    if errors:
        return {
            "status": "error",
            "message": f"TRANSACTION ABORTED: {len(errors)} error(s) detected. 0 files modified.",
            "errors": errors,
            "modified_files": []
        }

    if not file_buffers:
        return {"status": "warning", "message": "No operations performed.", "errors": [], "modified_files": []}

    file_summaries = []
    for path, new_content in file_buffers.items():
        orig_content = file_original_content.get(path)
        rel_display = os.path.relpath(path, base_dir)

        if orig_content is None:
            added = len(new_content.splitlines())
            removed = 0
            op_type = "Created"
        else:
            orig_lines = orig_content.splitlines()
            new_lines = new_content.splitlines()
            matcher = difflib.SequenceMatcher(None, orig_lines, new_lines)
            added = sum(j2 - j1 for tag, i1, i2, j1, j2 in matcher.get_opcodes() if tag in ('replace', 'insert'))
            removed = sum(i2 - i1 for tag, i1, i2, j1, j2 in matcher.get_opcodes() if tag in ('replace', 'delete'))
            op_type = "Modified"

        if not dry_run:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            nl = file_line_endings.get(path, "\n")
            content_to_write = new_content.replace("\n", nl)
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(content_to_write)

        file_summaries.append({
            "filepath": rel_display,
            "operation": op_type,
            "patches_applied": file_ops_count.get(path, 1),
            "lines_added": added,
            "lines_removed": removed
        })

    return {
        "status": "success",
        "dry_run": dry_run,
        "message": f"Successfully processed {len(file_summaries)} file(s).",
        "errors": [],
        "modified_files": file_summaries
    }


def read_clipboard() -> str:
    try:
        import pyperclip
        return pyperclip.paste()
    except ImportError:
        pass
    if sys.platform == "win32":
        try:
            return subprocess.check_output(["powershell", "-command", "Get-Clipboard"], text=True)
        except Exception:
            pass
    raise RuntimeError("Clipboard unavailable. Pass a file path or install pyperclip: pip install pyperclip")


def main():
    parser = argparse.ArgumentParser(description="Tool runner for Gemini & AI Studio JSON payloads.")
    parser.add_argument("files", nargs="*", help="File path(s) to JSON payload.")
    parser.add_argument("-f", "--file", "-i", "--input", dest="flag_files", action="append", default=[])
    parser.add_argument("-c", "--clipboard", action="store_true", help="Read from clipboard.")
    parser.add_argument("-y", "--yes", action="store_true", help="Auto-approve terminal commands.")
    parser.add_argument("-d", "--dry-run", action="store_true", help="Test patches without writing.")
    parser.add_argument("-b", "--base-dir", default=".")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON.")
    args = parser.parse_args()

    target_files = list(args.files) + list(args.flag_files)
    raw_inputs = []

    if target_files:
        for fp in target_files:
            with open(fp, "r", encoding="utf-8-sig") as f:
                raw_inputs.append(f.read())
    elif args.clipboard:
        raw_inputs.append(read_clipboard())
    elif not sys.stdin.isatty():
        raw_inputs.append(sys.stdin.read())
    else:
        try:
            raw_inputs.append(read_clipboard())
        except Exception:
            parser.print_help()
            sys.exit(1)

    combined_input = "\n".join(raw_inputs)
    patches = extract_json_blocks(combined_input)
    if not patches:
        print("Error: No valid JSON tool blocks found in input.", file=sys.stderr)
        sys.exit(1)

    result = execute_patches(patches, base_dir=args.base_dir, dry_run=args.dry_run, auto_approve_cmd=args.yes)

    if args.json:
        print(json.dumps(result, indent=2))
    elif result.get("type") != "command_execution":
        print(f"\n[{result['status'].upper()}] {result['message']}")
        for f in result.get("modified_files", []):
            print(f"  ✓ [{f['operation']}] {f['filepath']} (+{f['lines_added']} / -{f['lines_removed']})")


if __name__ == "__main__":
    main()
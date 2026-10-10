#!/usr/bin/env python3
"""
AI Studio / Gemini Tool Runner & Search-Replace Orchestrator (Tab-Sensitive)
--------------------------------------------------------------------------
Processes raw AI Studio / Gemini outputs with full atomic safety.
Supports:
 - Strict Python tab and indentation sensitivity
 - Multi-tier matching (Exact -> Trailing Whitespace -> Indentation for non-Python)
 - Tab vs Space mismatch detection for Python code
 - Closest-match locator with visible whitespace & unified diffs on failure
 - Terminal command execution with confirmation prompts
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
    """Resolves file path with auto-healing if root folders were omitted."""
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


def is_python_file(filepath: str) -> bool:
    """Returns True if the target file is Python code where indentation is structural syntax."""
    if not filepath:
        return False
    return filepath.lower().endswith((".py", ".pyw"))


def render_visible_whitespace(line: str) -> str:
    """Replaces tab characters with a visible symbol for console diagnostics."""
    return line.replace("\t", "⇥   ")


def detect_line_indentation_style(lines: List[str]) -> Tuple[bool, bool]:
    """Returns (has_tabs, has_spaces) for leading indentation."""
    has_tabs = False
    has_spaces = False
    for l in lines:
        leading = l[:len(l) - len(l.lstrip())]
        if "\t" in leading:
            has_tabs = True
        if " " in leading:
            has_spaces = True
    return has_tabs, has_spaces


def find_closest_match_diagnostics(c_lines: List[str], s_lines: List[str], is_py: bool = False) -> Tuple[int, int, float, str, str, str]:
    """
    Finds the candidate region in c_lines that most closely resembles s_lines.
    Returns: (start_line_1idx, end_line_1idx, similarity_ratio, surrounding_code, diff_text, indent_hint)
    """
    if not c_lines or not s_lines:
        return 1, 1, 0.0, "", "", ""

    s_clean = [l.strip() for l in s_lines]
    c_clean = [l.strip() for l in c_lines]

    target_window = max(1, len(s_lines))
    best_start = 0
    best_end = min(len(c_lines), target_window)
    best_ratio = 0.0

    # 1. Anchor scan: look for starting lines that closely match
    anchor = s_clean[0] if s_clean else ""
    candidate_starts = []
    if anchor:
        for idx, line in enumerate(c_clean):
            if line == anchor or anchor in line or difflib.SequenceMatcher(None, line, anchor).ratio() > 0.7:
                candidate_starts.append(idx)

    # 2. Score candidate anchors or sample windows
    test_starts = candidate_starts if candidate_starts else range(max(1, len(c_lines) - target_window + 1))
    for start in test_starts:
        end = min(len(c_lines), start + target_window)
        ratio = difflib.SequenceMatcher(None, s_clean, c_clean[start:end]).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_start = start
            best_end = end

    # 3. Detect tab vs space differences in Python candidate region
    indent_hint = ""
    candidate_file_lines = c_lines[best_start:best_end]
    if is_py:
        file_has_tabs, file_has_spaces = detect_line_indentation_style(candidate_file_lines)
        search_has_tabs, search_has_spaces = detect_line_indentation_style(s_lines)

        if file_has_tabs and not search_has_tabs:
            indent_hint = "⚠️ TAB MISMATCH: File on disk uses TAB characters ('\\t'), but search block uses SPACES."
        elif not file_has_tabs and search_has_tabs:
            indent_hint = "⚠️ TAB MISMATCH: File on disk uses SPACES, but search block uses TAB characters ('\\t')."
        elif file_has_tabs and file_has_spaces:
            indent_hint = "⚠️ MIXED INDENTATION: File on disk has mixed tabs and spaces."

    # 4. Build surrounding context preview with visible tabs
    ctx_start = max(0, best_start - 3)
    ctx_end = min(len(c_lines), best_end + 3)

    context_lines = []
    for l_idx in range(ctx_start, ctx_end):
        marker = ">>>" if best_start <= l_idx < best_end else "   "
        rendered_line = render_visible_whitespace(c_lines[l_idx]) if is_py else c_lines[l_idx]
        context_lines.append(f"{marker} {l_idx + 1:4d} | {rendered_line}")
    surrounding_code = "\n".join(context_lines)

    # 5. Generate unified diff
    disp_file_lines = [render_visible_whitespace(l) for l in candidate_file_lines] if is_py else candidate_file_lines
    disp_search_lines = [render_visible_whitespace(l) for l in s_lines] if is_py else s_lines

    diff_generator = difflib.unified_diff(
        disp_file_lines,
        disp_search_lines,
        fromfile=f"file_on_disk (lines {best_start + 1}–{best_end})",
        tofile="search_block",
        lineterm=""
    )
    diff_text = "\n".join(diff_generator)

    return best_start + 1, best_end, best_ratio, surrounding_code, diff_text, indent_hint


def apply_flexible_search_replace(
    content: str,
    search_str: str,
    replace_str: str,
    filepath: str = ""
) -> Tuple[Optional[str], Optional[str], Optional[Dict[str, Any]]]:
    """
    Tiered search-and-replace:
      Tier 1: Exact string match
      Tier 2: Trailing whitespace tolerance (.rstrip per line, keeps all leading tabs/spaces 100% intact)
      Tier 3: Indentation-tolerant line slice (NON-PYTHON ONLY! Preserves tab strictness for Python files)
    """
    is_py = is_python_file(filepath)

    # --- Tier 1: Exact Match ---
    count = content.count(search_str)
    if count == 1:
        return content.replace(search_str, replace_str, 1), "exact", None
    elif count > 1:
        return None, None, {
            "reason": f"Ambiguous exact match: found {count} occurrences."
        }

    c_lines = content.splitlines()
    s_lines = search_str.splitlines()
    r_lines = replace_str.splitlines()
    s_len = len(s_lines)

    # --- Tier 2: Trailing-Whitespace-Tolerant Match ---
    # .rstrip() ONLY strips invisible spaces at the end of lines; leading tabs/spaces are untouched!
    c_lines_rstrip = [l.rstrip() for l in c_lines]
    s_lines_rstrip = [l.rstrip() for l in s_lines]

    matches_t2 = []
    for i in range(len(c_lines_rstrip) - s_len + 1):
        if c_lines_rstrip[i : i + s_len] == s_lines_rstrip:
            matches_t2.append(i)

    if len(matches_t2) == 1:
        start = matches_t2[0]
        new_lines = c_lines[:start] + r_lines + c_lines[start + s_len:]
        new_content = "\n".join(new_lines)
        if content.endswith("\n") and not new_content.endswith("\n"):
            new_content += "\n"
        return new_content, "trailing_whitespace_tolerant", None
    elif len(matches_t2) > 1:
        return None, None, {
            "reason": f"Ambiguous match (Tier 2 trailing-whitespace): found {len(matches_t2)} occurrences."
        }

    # --- Tier 3: Indentation-Tolerant Match (STRICTLY SKIPPED FOR PYTHON FILES) ---
    if not is_py:
        c_lines_strip = [l.strip() for l in c_lines]
        s_lines_strip = [l.strip() for l in s_lines]

        matches_t3 = []
        for i in range(len(c_lines_strip) - s_len + 1):
            if c_lines_strip[i : i + s_len] == s_lines_strip:
                matches_t3.append(i)

        if len(matches_t3) == 1:
            start = matches_t3[0]
            matched_slice = c_lines[start : start + s_len]

            # Calculate indentation delta
            indent_delta = 0
            for fl, sl in zip(matched_slice, s_lines):
                if fl.strip() and sl.strip():
                    f_indent = len(fl) - len(fl.lstrip())
                    s_indent = len(sl) - len(sl.lstrip())
                    indent_delta = f_indent - s_indent
                    break

            # Adapt replacement indentation
            adjusted_r_lines = []
            for rl in r_lines:
                if rl.strip():
                    if indent_delta > 0:
                        adjusted_r_lines.append((" " * indent_delta) + rl)
                    elif indent_delta < 0:
                        trim = min(abs(indent_delta), len(rl) - len(rl.lstrip()))
                        adjusted_r_lines.append(rl[trim:])
                    else:
                        adjusted_r_lines.append(rl)
                else:
                    adjusted_r_lines.append("")

            new_lines = c_lines[:start] + adjusted_r_lines + c_lines[start + s_len:]
            new_content = "\n".join(new_lines)
            if content.endswith("\n") and not new_content.endswith("\n"):
                new_content += "\n"
            return new_content, "indentation_tolerant", None
        elif len(matches_t3) > 1:
            return None, None, {
                "reason": f"Ambiguous match (Tier 3 indentation-tolerant): found {len(matches_t3)} occurrences."
            }

    # --- Failure Diagnostics & Diagnostics Visualizer ---
    l_start, l_end, ratio, surrounding, diff, indent_hint = find_closest_match_diagnostics(c_lines, s_lines, is_py)
    preview = s_lines[0].strip()[:80] if s_lines else "(empty)"

    reason_msg = f"Search block not found. Starts with: '{preview}'"
    if is_py and indent_hint:
        reason_msg += f"\n     ↳ {indent_hint}"

    return None, None, {
        "reason": reason_msg,
        "closest_line_start": l_start,
        "closest_line_end": l_end,
        "similarity": ratio,
        "surrounding_code": surrounding,
        "diff": diff,
        "indent_hint": indent_hint,
        "is_python": is_py
    }


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
        exec_cmd = 'python -X utf8 "._gemini_exec_temp.py"'

    try:
        proc = subprocess.run(
            exec_cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            cwd=abs_base,
            env=env,
            encoding="utf-8",
            errors="replace"
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
    """Executes all tool operations with multi-tier matching and detailed diff diagnostics."""
    file_patches = [p for p in patches if any(k in p for k in ("filepath", "path", "file", "filename"))]
    cmd_patches = [p for p in patches if any(k in p for k in ("command", "cmd", "bash", "shell"))]

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

    file_buffers: Dict[str, str] = {}
    file_line_endings: Dict[str, str] = {}
    file_original_content: Dict[str, Optional[str]] = {}
    file_ops_count: Dict[str, int] = {}
    errors: List[Dict[str, Any]] = []

    for i, patch in enumerate(file_patches, start=1):
        patch_id = i
        raw_filepath = patch.get("filepath") or patch.get("path") or patch.get("file")
        search_str = patch.get("search") or patch.get("find") or patch.get("old_str")
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

            new_content, match_mode, err_data = apply_flexible_search_replace(
                current_content, norm_search, norm_replace, filepath=raw_filepath
            )

            if err_data:
                err_data["patch_index"] = patch_id
                err_data["filepath"] = raw_filepath
                errors.append(err_data)
            else:
                file_buffers[resolved_path] = new_content
                file_ops_count[resolved_path] = file_ops_count.get(resolved_path, 0) + 1

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

        # Reveal failure diagnostics, surrounding code, and diffs
        if result.get("errors"):
            print("\n" + "=" * 70)
            print(" ❌ TRANSACTION FAILED: PATCH ERRORS & SURROUNDING CODE")
            print("=" * 70)
            for err in result["errors"]:
                p_idx = err.get("patch_index", "?")
                fp = err.get("filepath", "unknown")
                reason = err.get("reason", "unknown error")
                is_py = err.get("is_python", False)

                print(f"\n[Patch #{p_idx}] {fp}")
                print(f"  Reason: {reason}")

                if err.get("surrounding_code"):
                    l_start = err.get("closest_line_start", "?")
                    l_end = err.get("closest_line_end", "?")
                    sim = int(err.get("similarity", 0) * 100)
                    ws_label = " (⇥ = TAB)" if is_py else ""
                    print(f"\n  🔍 Closest code area in file (lines {l_start}–{l_end}, ~{sim}% match){ws_label}:")
                    print("  " + "-" * 66)
                    for cl in err["surrounding_code"].splitlines():
                        print(f"  {cl}")
                    print("  " + "-" * 66)

                if err.get("diff"):
                    print(f"\n  📋 Difference (File on Disk vs Search Block):")
                    print("  " + "-" * 66)
                    for dl in err["diff"].splitlines()[:30]:
                        print(f"  {dl}")
                    print("  " + "-" * 66)
            print("\n" + "=" * 70 + "\n")

        for f in result.get("modified_files", []):
            print(f"  ✓ [{f['operation']}] {f['filepath']} (+{f['lines_added']} / -{f['lines_removed']})")


if __name__ == "__main__":
    main()
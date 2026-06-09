Here is the hyper-detailed v1.0 Architecture and Refactoring Plan to transition PalBaker to a headless, CLI-first, API-driven architecture. 

This plan is structured into **Core Architecture**, **JSON Data Contracts**, and **Phased Milestones**, designed specifically so you (and future LLM sessions) can implement this sequentially without breaking the app.

---

# 🚀 PalBaker v1.0: Headless CLI-First Architecture Plan

## 1. Executive Summary
**The Goal:** Completely sever the Flet UI from the underlying Python business logic. The backend will become a standalone Command Line Interface (`palbaker-cli.py`). The Flet UI will be downgraded to a "dumb client" that executes CLI commands via `asyncio.subprocess` and parses standard output (STDOUT) formatted strictly as JSON/JSONL to render the visual state.

**The Benefits:**
*   **Zero WebSocket Clogging:** The UI only processes structured JSON payloads instead of raw, high-frequency log streams.
*   **Headless Automation:** CI/CD pipelines, Discord bots, or automated file watchers can now build Palworld mods without a GUI.
*   **Frontend Agnostic:** You can swap Flet for a Web UI (React/Vue), PyQt, or Electron in the future with zero backend rewrites.

---

## 2. System Architecture

### The Execution Layers
1. **`palbaker_cli.py` (The Backend/Server):** Uses `argparse` (or a library like `click`/`typer`) to route commands. It suppresses all random `print()` statements. It *only* outputs valid JSON.
2. **`CliDispatcher` (The Bridge):** A new Python class inside the UI that replaces `controllers/`. It wraps `subprocess.Popen` to call `palbaker_cli.py` and returns parsed JSON `dict`s to the Flet views.
3. **`views/` (The Frontend):** Takes the dicts and maps them to visual Flet components.

### The JSON Data Contract (STDOUT Protocol)
To ensure the UI can parse command outputs without breaking, the CLI must adhere to strict JSON envelopes.

**A. Standard Response (for Queries/Instant Actions):**
```json
{
  "status": "success", 
  "message": "Pal database rebuilt successfully.",
  "data": { ... } // Array of mods, settings dict, etc.
}
```
*If error:* `{"status": "error", "message": "Failed to locate Blender."}`

**B. Streaming Response / JSONL (for Long Pipelines like `mod push`):**
During builds, the CLI will output newline-delimited JSON (JSONL). The UI reads line-by-line.
```json
{"type": "log", "level": "stage", "message": ">>> EXECUTING PUSH: WeaselDragon"}
{"type": "progress", "percent": 0.15, "message": "Importing Assets into Unreal..."}
{"type": "log", "level": "warning", "message": "Missing skeletal hierarchy."}
{"type": "result", "status": "success", "summary": {"total_warnings": 1}}
```

---

## 3. Implementation Milestones

### 🟢 Phase 1: CLI Scaffold & Read-Only Queries
**Objective:** Build the entry point and migrate all "getters" (scanning disks, reading configs) to JSON CLI commands.

*   **Step 1.1: Create `palbaker_cli.py`.**
    *   Set up sub-parsers for `manager`, `mod`, `altermatic`, `creator`, `audio`, `env`.
    *   Create a global `json_print()` helper that formats outputs and forces `sys.stdout.flush()`.
*   **Step 1.2: Migrate `utils/config.py`.**
    *   Implement `palbaker_cli.py config get` -> outputs settings as JSON.
    *   Implement `palbaker_cli.py config set <key> <value>`.
*   **Step 1.3: Migrate `utils/scanner.py` (The heavy lifter).**
    *   Implement `palbaker_cli.py manager list`.
    *   Ensure `get_mod_info()` suppresses stray `print()` calls and outputs the massive array of mod states (badges, paths, modified status) as a JSON array.
*   **Step 1.4: Migrate UI Loading.**
    *   Update `ModsView.refresh_mods()` to execute `palbaker_cli.py manager list`, `json.loads()` the output, and pass it to `render_mods()`.

### 🟡 Phase 2: Action Commands (The Fast Mutations)
**Objective:** Migrate instant actions (Altermatic JSON editing, Audio staging, Creator schemas).

*   **Step 2.1: Altermatic CLI commands.**
    *   Migrate `ManifestManager` logic.
    *   `palbaker_cli.py altermatic add <mod> <variant> --source <base>` -> Output success JSON.
    *   `palbaker_cli.py altermatic update <mod> <variant> --data '{"MatReplace": [...]}'`
*   **Step 2.2: Creator CLI commands.**
    *   Migrate `PalManager` logic.
    *   `palbaker_cli.py creator add <custom_id> --template <parent_id>`
*   **Step 2.3: Audio CLI commands.**
    *   Migrate `AudioController`.
    *   `palbaker_cli.py audio set <mod> <cry> <path_to_mp3>` -> This calls `vgmstream` & `wwise`, then returns `{"status": "success"}`.
*   **Step 2.4: Update UI.**
    *   Replace `AltermaticController`, `CreatorController`, and `AudioController` inside the Flet app with dispatchers that call these new CLI endpoints.

### 🟠 Phase 3: The Build Pipeline (JSONL Streaming)
**Objective:** Refactor `build_mod.py` to stream JSON lines instead of raw text, and connect the UI to it.

*   **Step 3.1: Modify `build_mod.py` logging.**
    *   Change all `print()` statements in `build_mod.py`, `unreal_scripts/`, and `utils/builder/` to emit the `{type: log/progress}` JSON structure.
    *   *Crucial:* Prevent `subprocess.run` (like UE Cooker or Blender) from dumping raw text into STDOUT. Capture their outputs (`capture_output=True`) and wrap them in `{"type": "log", "message": "<raw_line>"}` before printing.
*   **Step 3.2: Hook CLI to the Pipeline.**
    *   `palbaker_cli.py mod execute <mod> <action>` simply acts as a passthrough to `build_mod.py`.
*   **Step 3.3: Refactor UI `PipelineExecutor`.**
    *   Update `run_pipeline_async` to use `json.loads(line)`.
    *   If `type == 'progress'`, update `self.progress_bar.value`.
    *   If `type == 'log'`, append to `self.log_view`.
    *   This entirely eliminates the need for `LogAnalyzer.py` in the UI, moving the analysis directly into the CLI.

### 🔴 Phase 4: Environment, Diagnostics & Cleanup
**Objective:** Move all C++ compilation and prerequisite checks to the CLI.

*   **Step 4.1: Env Commands.**
    *   `palbaker_cli.py env verify` -> outputs `{"needs_compile": true, "missing_assets": [...]}`.
    *   `palbaker_cli.py env install-plugin`
    *   `palbaker_cli.py env ue4ss install`
*   **Step 4.2: Replace UI Settings Controller.**
    *   The Settings tab now purely reads from `env verify` and displays the buttons. When clicked, it calls the CLI and awaits the JSON response.

---

## 4. The New `CliDispatcher` (Example UI Bridge)

To implement this cleanly in your Flet app, you will replace your current `controllers/` directory with a unified interface. 

Here is what the architecture of your new UI client will look like:

```python
# ui_client/dispatcher.py
import asyncio
import json
import subprocess

class PalBakerCLI:
    def __init__(self, cli_path="python palbaker_cli.py"):
        self.cli_path = cli_path.split(" ")

    async def _execute(self, args: list) -> dict:
        """Executes a standard CLI command and returns the parsed JSON dict."""
        cmd = self.cli_path + args
        # CREATE_NO_WINDOW ensures no rogue cmd prompts pop up on Windows
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        stdout, stderr = await proc.communicate()
        
        try:
            return json.loads(stdout.decode().strip())
        except json.JSONDecodeError:
            return {"status": "error", "message": f"CLI Error: {stderr.decode()}"}

    async def list_mods(self, show_unextracted=False):
        args = ["manager", "list"]
        if show_unextracted:
            args.append("--show-unextracted")
        return await self._execute(args)

    async def run_pipeline_stream(self, mod_name: str, action: str, log_cb, progress_cb, done_cb):
        """Yields JSONL output line-by-line for live UI updates."""
        cmd = self.cli_path + ["mod", action, mod_name]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
                
            try:
                payload = json.loads(line.decode().strip())
                if payload["type"] == "log":
                    log_cb(payload["message"], payload.get("level", "standard"))
                elif payload["type"] == "progress":
                    progress_cb(payload["percent"], payload["message"])
            except json.JSONDecodeError:
                pass # Ignore malformed output
                
        await proc.wait()
        done_cb(proc.returncode == 0)
```

---

## 5. Execution Rules & Best Practices for the Refactor

1. **Silence the Noise:** `cue4parse`, `Blender`, and `UnrealEditor-Cmd` naturally spam STDOUT. You **must** wrap their execution in the CLI with `capture_output=True` (or redirect to DEVNULL) so they don't corrupt the JSON output of `palbaker_cli.py`.
2. **Atomic Commits:** Do not do this all at once. 
   * *PR 1:* Create `palbaker_cli.py` and implement `manager list`. Update UI to use it.
   * *PR 2:* Move Altermatic/Creator/Audio.
   * *PR 3:* Tackle the `build_mod.py` JSONL streaming (the hardest part).
3. **The Global Try/Catch:** The root of `palbaker_cli.py` must have a global `try...except Exception as e:` block that catches fatal Python crashes and prints them as `{"status": "fatal", "error": str(e)}`. If the CLI spits out a Python traceback instead of JSON, the Flet UI will crash trying to parse it.
### 1. Architectural Strategy: The "Sandbox Config" Lifecycle

Because this script manipulates your active production configuration, it must be wrapped in a strict **Double-Decker Restoration Safeguard**. If a test assertion fails midway through an invalid path test, or if you cancel the test via `Ctrl+C`, the script must guarantee that your real `manager_settings.json` is restored [build_mod.py].

#### Execution Lifecycle:
```text
[Start] ──> Read & copy "manager_settings.json" to "manager_settings.json.bak"
             │
             ├──> [Try Block]
             │     ├──> Scenario 1: Empty Paths (Assert clean error stdout)
             │     ├──> Scenario 2: Invalid/Garbage Paths (Assert path validation warnings)
             │     └──> Scenario 3: Real Paths (Assert successful path/multicast resolution)
             │
             └──> [Finally Block] (Wipe temp settings, restore backup, delete .bak) ──> [End]
```

---

### 2. Scenario-by-Scenario Execution Plan

Each scenario must run sequentially inside the isolation block to verify how the CLI handles different states.

#### Scenario 1: The "Empty Config" Graceful Exit Test
* **Objective:** Verify CLI behavior when configurations are completely unconfigured.
* **Setup:** Write an empty settings template to `manager_settings.json` [build_mod.py]:
  ```json
  {
      "fmodel_output": "", 
      "ue_root": "", 
      "uproject": "", 
      "blender": "",
      "palworld_exe": ""
  }
  ```
* **Execution:** Run a command that requires paths (e.g., `python palbaker_cli.py mod extract BadCatgirl` or `python palbaker_cli.py altermatic metadata BadCatgirl`) [palbaker_cli.py].
* **Assertions:**
  * [ ] Assert the process exit code is non-zero (preferably `1`) [test_decompile_cli.py].
  * [ ] Assert the stdout parses as valid JSON [test_decompile_cli.py].
  * [ ] Assert the output JSON matches the error schema: `{"status": "error", "message": "..."}` [test_decompile_cli.py].
  * [ ] Assert the `message` contains helpful user instructions (e.g., `"Please configure your paths in Settings"` or `"Workspace Folder not set"`) [palbaker_cli.py].
  * [ ] Assert that no Python `Traceback` text exists in either `stdout` or `stderr` [test_decompile_cli.py].

#### Scenario 2: The "Malformed/Garbage Path" Validation Test
* **Objective:** Verify CLI behavior when paths are filled with garbage strings that do not exist on disk.
* **Setup:** Write invalid paths to `manager_settings.json`:
  ```json
  {
      "fmodel_output": "C:\\This\\Is\\A\\Fake\\Path", 
      "ue_root": "D:\\Unreal\\NotReal", 
      "uproject": "E:\\NoProject\\test.uproject", 
      "blender": "F:\\NoBlender\\blender.exe",
      "palworld_exe": "G:\\NoGame\\Palworld.exe"
  }
  ```
* **Execution:** Run `python palbaker_cli.py env verify` [palbaker_cli.py].
* **Assertions:**
  * [ ] Assert the output parses as valid JSON [test_decompile_cli.py].
  * [ ] Assert the status returned is `"error"` or contains specific flags identifying which paths failed validation [test_decompile_cli.py].
  * [ ] Assert that the CLI handles the check gracefully without attempting to execute a subprocess against `F:\NoBlender\blender.exe`, which would throw an OS-level `FileNotFoundError` in Python.

#### Scenario 3: Real Paths & Positive Lightweight Verification
* **Objective:** Verify that correct paths resolve successfully and communicate with external daemons *without* running heavy pipeline steps.
* **Setup:** Restore your actual paths from the `.bak` file and write them to `manager_settings.json` [build_mod.py].
* **Execution:** Run `python palbaker_cli.py mod ping BadCatgirl` [palbaker_cli.py].
* **Mechanics:** 
  In your CLI, the `ping` subcommand should perform a lightweight network handshake with the open Unreal Editor [palbaker_cli.py]. It verifies the project path, locates the remote execution UDP node [utils/builder/unreal_helper.py], and returns a connection diagnostic payload [palbaker_cli.py]. It aborts immediately after verifying the socket connection [palbaker_cli.py].
* **Assertions:**
  * [ ] Assert the exit code is `0` [test_decompile_cli.py].
  * [ ] Assert the JSON key `unreal_running` matches your editor's physical state (True/False) [palbaker_cli.py].
  * [ ] If the editor is open, assert `diagnostic_code` equals `"FULLY_CONNECTED"` [palbaker_cli.py].
  * [ ] If the editor is closed, assert the CLI does not hang, but exits under a tight timeout (e.g., < 2 seconds) with `diagnostic_code` set to `"UNREAL_CLOSED"` [palbaker_cli.py].

---

### 3. Implementation checklist for `test_01_preflight.py`

- [ ] Import `json`, `os`, `sys`, `shutil`, and `subprocess` [test_decompile_cli.py].
- [ ] Define helper `run_cli_command(args)` that executes the subcommand and captures STDOUT/STDERR safely [test_decompile_cli.py].
- [ ] Implement `backup_config()` to safely rename or copy the file [build_mod.py].
- [ ] Implement `restore_config()` inside a `finally:` block to ensure settings are never permanently lost [test_decompile_cli.py].
- [ ] Implement **Scenario 1** (Empty values) and assert JSON error contracts.
- [ ] Implement **Scenario 2** (Invalid paths) and assert clean error strings without Python tracebacks.
- [ ] Implement **Scenario 3** (Real paths) and assert lightweight `ping` socket validation [palbaker_cli.py].
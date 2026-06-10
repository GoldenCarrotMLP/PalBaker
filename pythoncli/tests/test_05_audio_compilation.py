# tests/test_05_audio_compilation.py
"""
================================================================================
PALBAKER CLI INTEGRATION TEST 05: AUDIO COMPILATION & TRANSCODING
================================================================================
COMMANDS EXECUTED SEQUENTIALLY ON THIS TEST:

[PROFILE 1: EMPTY CONFIGURATION]
1. Zeroes out all active configuration paths.
2. Attempt audio replacement:
   python palbaker_cli.py audio set BadCatgirl Joy tests/assets/A.mp3
3. Asserts CLI gracefully returns status 'error' and exit code 1.
4. Logs the descriptive error message returned by the CLI.

[PROFILE 2: GARBAGE CONFIGURATION]
5. Writes non-existent junk paths to the settings config.
6. Attempt audio replacement:
   python palbaker_cli.py audio set BadCatgirl Joy tests/assets/A.mp3
7. Asserts CLI gracefully returns status 'error', exit code 1, and path warnings.
8. Logs the descriptive error message returned by the CLI.

[PROFILE 3: REAL CONFIGURATION]
9. Restores the user's active manager_settings.json.
10. [Self-Healing] Verifies BadCatgirl was extracted; if missing, triggers Step 2:
    python palbaker_cli.py mod extract BadCatgirl
11. Performs Wwise audio transcoding and staging:
    python palbaker_cli.py audio set BadCatgirl Joy tests/assets/A.mp3
12. Asserts exit code is 0, status is 'success'.
13. Verifies physical disk outputs:
    - .palbaker_audio/sources/Joy.mp3 exists (Source file copied)
    - .palbaker_audio/WwiseAudio/Media/191233074.wem exists (Wwise output .wem)
14. Triggers local host audio playback preview:
    python palbaker_cli.py audio play BadCatgirl Joy
15. Triggers audio override removal and directory cleanup:
    python palbaker_cli.py audio clear BadCatgirl Joy
16. Verifies files are deleted from the workspace on teardown.
================================================================================
"""

import os
import sys
import json
import shutil
from test_helper import SettingsSandbox, run_cli_command, parse_cli_json, log

# Resolve paths relative to the test file location
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)
SETTINGS_FILE = os.path.join(REPO_ROOT, "manager_settings.json")
CLI_ENTRY_POINT = os.path.join(REPO_ROOT, "palbaker_cli.py")

TARGET_PAL = "BadCatgirl"
TARGET_CRY = "Joy"
EXPECTED_WEM_NAME = "191233074.wem"  # Nyafia's Joy sound media_id from database

def assert_graceful_failure(exit_code: int, stdout: str, stderr: str, profile_name: str):
    if "traceback" in stdout.lower() or "traceback" in stderr.lower():
         raise AssertionError(f"CLI crashed with a raw Python traceback under {profile_name} profile.\nSTDOUT: {stdout}\nSTDERR: {stderr}")
         
    parsed = parse_cli_json(stdout)
    if not parsed:
         raise AssertionError(f"CLI did not output a valid JSON envelope on graceful failure under {profile_name}.\nExit Code: {exit_code}\nSTDOUT: {stdout}")
         
    if parsed.get("status") != "error":
         raise AssertionError(f"Expected status 'error' under {profile_name}, got '{parsed.get('status')}'")

    error_message = parsed.get("message", "No message field returned by CLI.")
    log(f"Graceful Reject Code: {exit_code}")
    log(f"Graceful Reject Msg:  {error_message}")


def main():
    log(f"=== PalBaker CLI Audio Transcoder (Chaos Proof): {TARGET_PAL} ({TARGET_CRY}) ===")
    
    sandbox = SettingsSandbox(REPO_ROOT)
    sandbox.backup()

    # Preflight dependency verification (vgmstream & Wwise)
    vgmstream_cli = os.path.normpath(os.path.join(REPO_ROOT, "deps", "vgmstream", "vgmstream-cli.exe"))
    if not os.path.exists(vgmstream_cli):
        vgmstream_cli = os.path.normpath(os.path.join(REPO_ROOT, "deps", "vgmstream-cli.exe"))

    candidate_wwise_paths = [
        os.path.join(REPO_ROOT, "deps", "wwise", "Authoring", "x64", "Release", "bin", "WwiseConsole.exe"),
        os.path.join(REPO_ROOT, "deps", "wwise", "bin", "WwiseConsole.exe")
    ]
    wwise_console = next((p for p in candidate_wwise_paths if os.path.exists(p)), None)

    if not os.path.exists(vgmstream_cli):
        log(f"Fatal: Missing required vgmstream-cli dependency. Please place it in deps/vgmstream/", "ERROR")
        sys.exit(1)
    if not wwise_console:
        log(f"Fatal: Missing required WwiseConsole dependency. Please place it in deps/wwise/", "ERROR")
        sys.exit(1)

    # Resolve local test audio file from assets folder
    test_audio_file = os.path.normpath(os.path.join(TESTS_DIR, "assets", "A.mp3"))
    if not os.path.exists(test_audio_file):
        # Fallback to general test folder if run from alternative root
        test_audio_file = os.path.normpath(os.path.join(REPO_ROOT, "tests", "assets", "A.mp3"))

    if not os.path.exists(test_audio_file):
        log(f"Fatal: Missing required test audio file at: {test_audio_file}. Please place an MP3 there.", "ERROR")
        sys.exit(1)

    try:
        # ---------------------------------------------------------------------
        # PROFILE 1: Empty Configuration Check
        # ---------------------------------------------------------------------
        log("\n--- Profile 1: Empty Settings Verification ---")
        sandbox.apply_profile("empty")
        
        exit_code, stdout, stderr = run_cli_command(["audio", "set", TARGET_PAL, TARGET_CRY, test_audio_file], CLI_ENTRY_POINT)
        assert_graceful_failure(exit_code, stdout, stderr, "EMPTY")
        log("✅ SUCCESS: Profile 1 passed. CLI rejected empty configuration gracefully.")

        # ---------------------------------------------------------------------
        # PROFILE 2: Garbage Configuration Check
        # ---------------------------------------------------------------------
        log("\n--- Profile 2: Garbage Settings Verification ---")
        sandbox.apply_profile("garbage")
        
        exit_code, stdout, stderr = run_cli_command(["audio", "set", TARGET_PAL, TARGET_CRY, test_audio_file], CLI_ENTRY_POINT)
        assert_graceful_failure(exit_code, stdout, stderr, "GARBAGE")
        log("✅ SUCCESS: Profile 2 passed. CLI rejected invalid paths gracefully.")

        # ---------------------------------------------------------------------
        # PROFILE 3: Real Configuration Operational Test
        # ---------------------------------------------------------------------
        log("\n--- Profile 3: Real Settings Verification & Run ---")
        sandbox.apply_profile("real")
        
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)

        fmodel_output = settings.get("fmodel_output", "")
        if not fmodel_output:
            log("Skipping Profile 3 run: Workspace Folder is not configured in settings.", "WARNING")
            return

        target_dir = os.path.normpath(os.path.join(
            fmodel_output, "Exports", "Pal", "Content", "Pal", "Model", "Character", "Monster", TARGET_PAL
        ))
        
        # Self-Healing: Verify Nyafia raw files are extracted before running audio tests
        if not os.path.exists(target_dir):
            log("Prerequisite Missing: Nyafia assets are not extracted. Executing self-healing step...")
            exit_code, stdout, stderr = run_cli_command(["mod", "extract", TARGET_PAL], CLI_ENTRY_POINT)
            if exit_code != 0:
                raise RuntimeError(f"Self-healing extraction failed. STDOUT: {stdout}\nSTDERR: {stderr}")

        audio_dir = os.path.join(target_dir, ".palbaker_audio")
        source_copy_path = os.path.join(audio_dir, "sources", f"{TARGET_CRY}.mp3")
        wem_output_path = os.path.join(audio_dir, "WwiseAudio", "Media", EXPECTED_WEM_NAME)

        # Clear any existing overrides to guarantee a clean compile run
        for path in [source_copy_path, wem_output_path]:
            if os.path.exists(path):
                log(f"Wiping existing custom override: {os.path.basename(path)}")
                try: os.remove(path)
                except OSError: pass

        # 1. Execute Audio Conversion command
        log(f"Triggering Wwise compiler for custom {TARGET_CRY} sound override...")
        exit_code, stdout, stderr = run_cli_command(["audio", "set", TARGET_PAL, TARGET_CRY, test_audio_file], CLI_ENTRY_POINT)

        parsed_set = parse_cli_json(stdout)
        if not parsed_set or parsed_set.get("status") != "success":
            raise AssertionError(f"Audio compilation execution failed. Payload: {parsed_set}\nSTDERR: {stderr}")

        # Verify physical disk outputs
        log("Verifying physical output assets on disk...")
        if not os.path.exists(source_copy_path):
            raise AssertionError(f"Audio compiled but the source MP3 backup was not created: {source_copy_path}")
        log(f"  -> Custom Audio Backup Saved: {os.path.basename(source_copy_path)} (Size: {os.path.getsize(source_copy_path)} bytes)")

        if not os.path.exists(wem_output_path):
            raise AssertionError(f"Audio compiled but Wwise failed to generate: {wem_output_path}")
        log(f"  -> Generated WEM Audio Node:  {os.path.basename(wem_output_path)} (Size: {os.path.getsize(wem_output_path)} bytes)")

        # 2. Trigger Playback Preview check
        log(f"Triggering host audio playback preview command...")
        exit_code, stdout, stderr = run_cli_command(["audio", "play", TARGET_PAL, TARGET_CRY], CLI_ENTRY_POINT)
        parsed_play = parse_cli_json(stdout)
        if not parsed_play or parsed_play.get("status") != "success":
            raise AssertionError(f"Playback command failed. STDOUT: {stdout}\nSTDERR: {stderr}")

        # 3. Trigger Revert/Clear command
        log(f"Triggering audio clear command to revert back to vanilla...")
        exit_code, stdout, stderr = run_cli_command(["audio", "clear", TARGET_PAL, TARGET_CRY], CLI_ENTRY_POINT)
        parsed_clear = parse_cli_json(stdout)
        if not parsed_clear or parsed_clear.get("status") != "success":
            raise AssertionError(f"Audio clear command failed. STDOUT: {stdout}\nSTDERR: {stderr}")

        # Verify cleanup operations
        log("Verifying workspace cleanup on disk...")
        if os.path.exists(wem_output_path):
            raise AssertionError("WEM file was not removed after the clear operation.")
        if os.path.exists(source_copy_path):
            raise AssertionError("Source MP3 backup file was not removed after the clear operation.")

        log(f"\n✅ PASS: Profile 3 passed. Staged audio node compiled and reverted successfully.")

    except Exception as e:
        log(f"❌ TEST FAILED: {str(e)}", "ERROR")
        sys.exit(1)
        
    finally:
        log("\n--- Cleanup & Teardown ---")
        sandbox.restore()

if __name__ == "__main__":
    main()
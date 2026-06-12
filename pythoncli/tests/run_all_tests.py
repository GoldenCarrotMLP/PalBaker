# tests/run_all_tests.py
"""
================================================================================
PALBAKER CLI END-TO-END MASTER TEST ORCHESTRATOR
================================================================================
This script headlessly executes the complete integration test suite sequentially.
It acts as a strict state machine, automatically failing if any submodule crashes.

SEQUENTIAL PIPELINE TARGETS:
1.  test_01_preflight.py              - Path Verification & Lightweight Ping Check
2.  test_02_extract_assets.py         - Cue4Parse Ingestion (Raw Asset extraction)
3.  test_03_blueprint_mutation.py     - Dynamic Blueprint Patching & Verification
4.  test_04_blender_reconstruction.py  - Headless Blender .blend Reconstruction
5.  test_05_audio_compilation.py      - Wwise Audio Override & Transcoding
6.  test_05b_plugin_setup.py          - C++ Plugin Compilation & Master Asset Ingestion
7.  test_06_unreal_import.py          - Unreal Engine Ingestion & Memory Verification
8.  test_07_unreal_decompile.py       - Unreal Decompilation & Reverse Ingestion
9.  test_08_altermatic.py             - Altermatic Workspace & Sidecar Lifecycle
10. test_10_altermatic_compile.py     - Full Altermatic Ingestion, Cooking, & Stripping
11. test_11_material_preservation.py  - Material Preservation State Machine
================================================================================
"""

import os
import sys
import time
import subprocess

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)

TEST_PIPELINE_FILES = [
    "test_01_preflight.py",
    "test_02_extract_assets.py",
    "test_03_blueprint_mutation.py",
    "test_04_blender_reconstruction.py",
    "test_05_audio_compilation.py",
    "test_05b_plugin_setup.py",
    "test_06_unreal_import.py",
    "test_07_unreal_decompile.py",
    "test_08_altermatic.py",
    "test_10_altermatic_compile.py",
    "test_11_material_preservation.py" # <-- ADDED!
]

def log(message: str, category: str = "INFO"):
    print(f"[ORCHESTRATOR] {message}", flush=True)

def main():
    log("======================================================================")
    log("=== STARTING PALBAKER HEADLESS END-TO-END SUITE ===")
    log("======================================================================")
    
    start_time = time.time()
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    
    try:
        for idx, filename in enumerate(TEST_PIPELINE_FILES):
            script_path = os.path.join(TESTS_DIR, filename)
            log(f"\n[{idx+1}/{len(TEST_PIPELINE_FILES)}] Executing: {filename}...")
            
            # Execute child test file headlessly
            proc = subprocess.run(
                [sys.executable, script_path],
                creationflags=creation_flags,
                cwd=TESTS_DIR
            )
            
            if proc.returncode != 0:
                log(f"❌ CRITICAL FAILURE: '{filename}' failed with exit code: {proc.returncode}.", "ERROR")
                log("Halted entire E2E suite to preserve debug states on disk.", "ERROR")
                sys.exit(1)
                
            log(f"✓ '{filename}' passed.")

        elapsed = time.time() - start_time
        log("\n" + "="*70)
        log(f"🎉 SUCCESS! All {len(TEST_PIPELINE_FILES)} diagnostic scenarios resolved successfully.")
        log(f"Total Suite Duration: {round(elapsed, 2)} seconds")
        log("="*70)
        sys.exit(0)

    except KeyboardInterrupt:
        log("\n⚠️ Suite cancelled by user. Halting processes...", "WARNING")
        sys.exit(1)
    except Exception as e:
        log(f"❌ Orchestration crashed: {str(e)}", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main()
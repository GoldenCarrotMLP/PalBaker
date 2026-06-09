# Technical Debt: Cross-Platform Discrepancies

## 1. Windows Dependency
### Description
The mod manager currently relies on Windows-specific utilities and naming conventions:
* `taskkill /F /T` for process termination.
* Executables are hardcoded with `.exe` extensions (e.g., `UnrealEditor-Cmd.exe`, `UnrealPak.exe`, `blender.exe` fallback).
### Debt / Risk
* **Linux/SteamDeck Modding:** Linux and SteamDeck modders cannot run this suite natively without modifying the platform-checking code and replacing Windows execution trees with POSIX shell kills.
* **Path Handledness:** Backslash-to-slash replacements (`replace("\\", "/")`) are used throughout the scripts to bridge Windows local paths with Unreal Engine virtual paths. This assumes Windows-style input paths and may behave unexpectedly if run natively under POSIX environments.
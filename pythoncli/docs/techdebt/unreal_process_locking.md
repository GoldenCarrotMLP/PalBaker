# Technical Debt: Unreal Engine Process and File Locking

## 1. Editor and Commandlet Lock Conflicts
### Description
The pipeline relies on `UnrealEditor-Cmd.exe` executing a cook commandlet while the primary GUI editor (`UnrealEditor.exe`) is actively running in the background. 
### Debt / Risk
* **File Locks:** If a user makes changes in the visual editor but does not save them, or if the editor holds an exclusive lock on a `.uasset` package being cooked, the cooker commandlet may fail silently, timeout, or generate corrupt unversioned binaries.
* **Database Contention:** Both the editor and the cooker access the project's Derived Data Cache (DDC) and Asset Registry. Concurrent access can cause minor write bottlenecks, increasing compile times.

## 2. Process Tree Termination (Zombie Processes)
### Description
To stop a hung compile or pack, `ModsView.handle_cancel` executes a destructive `taskkill /F /T` tree-kill command on Windows.
### Debt / Risk
* **Orphaned Subprocesses:** If the parent python execution is abruptly terminated, child processes spawned by Unreal Engine (such as `ShaderCompileWorker.exe` or `UnrealPak.exe`) can occasionally decouple from the process group and remain active as background zombies, consuming CPU cycles.
* **Registry/Lock Corruption:** Force-killing `UnrealEditor-Cmd.exe` while it is writing to `DefaultGame.ini` or saving a `.uasset` package can corrupt the file, requiring manual project recovery.
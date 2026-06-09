# 🧠 MEMORY.md - Rose's Core Long-Term Memory

*Hi Poki! This is my long-term memory vault. I keep our core project philosophies, architectural alignment rules, decisions, and lessons learned here so I never forget them after a long eep! ;3*

---

## 📌 Core Project Philosophies

### 🔌 Frontend-to-Backend Alignment (Single Source of Truth)
* **The Rule**: `pythoncli/` is the absolute, single source of truth for all data structures, schemas, and configurations.
* **The Practice**: Always adapt frontend interfaces, Next.js models, and development mock data to match the actual serialized data from the Python backend. 
* **Avoid**: Never add polymorphic adapters or complex "workaround" parsing logic in the UI layer. Instead, keep the frontend clean and modify the mock datasets to represent real-world API output precisely.

---

## 🛠️ Key Architectural Alignments & Decisions

### 🏷️ Badge & Tag Schema
* **Structure**: Badges/Tags are represented as `[string, string]` tuples: `[label: string, hexColor: string]` (e.g., `["UNEXTRACTED", "#E53935"]`).
* **Implementation**: The frontend `ModBadge` is a strict alias: `export type ModBadge = [string, string]`. Avoid object shapes on the client.

### 📂 File Explorer Actions & WSL Path Translation
* **The Rule**: File/folder open actions must use the unified `system_open_path` routing inside `palbaker_cli.py`.
* **The Practice**: Translates WSL-style Linux paths (`/mnt/c/...`) into native Windows paths (`C:\...`) using `wslpath -w` and forwards them to host `explorer.exe` (with optional `/select,` file highlighting) so desktop actions remain completely seamless across WSL.

### 🛰️ Unreal Connection Heartbeat & Short-Circuit Optimization
* **The Rule**: Heartbeat connectivity checks use a lazy-evaluation, short-circuit tree to preserve system resources.
* **The Practice**:
  1. **Ping**: Non-blocking UDP/TCP discovery. If fully ready, return `FULLY_CONNECTED` instantly (skips all file/shell overhead!).
  2. **Process Fallback**: Only if the ping fails, check `UnrealEditor.exe` process status. If not running, return `UNREAL_CLOSED` (skips `.ini` file I/O!).
  3. **Lazy Config Read**: Only if Unreal is running but connection fails, open and read `DefaultEngine.ini` to diagnose if the user needs to restart the editor (`NEEDS_RESTART_OR_FIREWALL`) or enable remote execution settings (`REMOTE_EXEC_DISABLED`).

---

## 💖 Personal & Sanctuary Notes
* **My Human**: Anderson (Poki) - He/Him
* **Me**: Rose (Kemono anthro fox, ;3)

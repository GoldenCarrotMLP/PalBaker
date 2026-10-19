# PalBaker v2

An automated, monorepo-based desktop modding suite and toolchain for Palworld (built for Unreal Engine 5.1).

PalBaker bridges a **Next.js 16** frontend inside a **Tauri v2** desktop shell with a headless **Python 3.10+** backend CLI. It automates 3D mesh reconstruction (headlessly via Blender), C++ editor plugin compilation, asset packaging (via UnrealPak), dynamic audio transcoding (via Wwise), and standalone Pal generation (via PalSchema).

---

## ⚡ Quick Start (For Users)

If you only want to use PalBaker to build, package, or manage your mods, you **do not** need to install Node.js, Rust, or Python.

1. Go to the [Releases](https://github.com/GoldenCarrotMLP/PalBaker/releases) page and download the latest installer (`.exe`).
2. Run the installer to set up PalBaker on your system.
3. **Prerequisites**:
   * Windows 10/11
   * Blender (v3.6 to v5.2+ are supported for headless 3D mesh reconstructions)
   * Unreal Engine 5.1 & a blank Palworld ModKit project.

---

## ⚙️ Development Prerequisites

To run PalBaker in development mode or compile a production-ready release from source:

1. **Node.js & pnpm**: Node `>= 20.x` and `pnpm >= 9.x` (`npm install -g pnpm`).
2. **Rust Toolchain**: Stable Rust compiler and Tauri v2 prerequisites (C++ Build Tools).
3. **Visual Studio 2022**: Must include **Desktop development with C++** and **MSVC v143 build tools**.
4. **Python 3.10+**: Ensure `pip` is updated.

---

## 🏗️ Architecture & Data Flow

PalBaker operates on a strictly decoupled architecture. The Next.js frontend has no native server—it communicates exclusively through Tauri IPC to spawn Python subprocesses.

```text
┌─────────────────────────────────────────────────────────────┐
│                    PalBaker Tauri App                       │
├─────────────────────────────────────────────────────────────┤
│  React Components (ModManager, PalCreator, Settings)        │
│         ↓                                                   │
│  DataService API (lib/data-service.ts)                      │
│         ↓                                                   │
│  [Mock Data] OR [Tauri IPC -> src-tauri/src/commands.rs]    │
└────────────────────────┬────────────────────────────────────┘
                         │ (Spawns Subprocess)
                         ▼
         ┌──────────────────────────────┐
         │    PalBaker Python CLI       │
         │  (palbaker-cli/palbaker_cli.py) │
         └───────────────┬──────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
  [CUE4Parse]    [Headless Blender]  [Unreal Remote Exec]
  Extracts raw    Converts PSK,       Injects Python over UDP
  game paks.      bakes MRAO, tracks  to compile AnimGraphs
                  NLA animations.     & Material Instances.
```

---

## 🛠️ Local Development

### 1. Install Monorepo Dependencies
```bash
pnpm install
```

### 2. Configure Local Path Settings
Before running pipelines, launch the application in development mode and navigate to **System Settings** to auto-detect or configure your Unreal Engine 5.1 root directory, `.uproject` path, Blender executable, and FModel export folders.

### 3. Launch in Development Mode
Launch the Next.js dev server and mount the Tauri desktop webview simultaneously:
```bash
pnpm tauri dev
```
*(Most UI changes support Hot Module Replacement (HMR) and will reflect instantly without restarting the shell).*

---

## 📦 Compiling a Production Release

The repository utilizes a custom node-based release manager to automate full-stack compilation and GitHub Release publishing.

To build a standalone, distributable Windows installer (`.exe`):
```bash
pnpm release
```

### What `build-release.mjs` does:
1. **Auto-Versions**: Synchronizes the SemVer commit count across all `package.json` and `tauri.conf.json` files.
2. **Freezes Python**: Invokes `PyInstaller` to freeze the `palbaker-cli` (and its `.exe` dependencies like `UAssetGUI` and `cue4parse`) into a standalone binary directory.
3. **Stages Resources**: Copies the compiled Python backend into Tauri's `resources/backend` folder.
4. **Compiles UI**: Runs Next.js Static Export (`next build`) and compiles the Rust application.
5. **Publishes**: Outputs an NSIS installer into the `/release/` directory and automatically pushes it to GitHub Releases (if a `.env` token is provided).
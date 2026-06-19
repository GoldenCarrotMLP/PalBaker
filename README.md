# PalBaker

An automated, monorepo-based desktop modding suite and toolchain for Palworld (built for Unreal Engine 5.1).

PalBaker bridges a **Next.js 16** frontend inside a **Tauri v2** desktop shell with a headless **Python 3.10+** backend CLI. It automates 3D mesh reconstruction (headlessly via Blender), C++ editor plugin compilation, asset packaging (via UnrealPak), dynamic audio transcoding (via Wwise and vgmstream), and standalone Pal generation (via PalSchema JSON injection).

---

## ⚡ Quick Start (For Users & Modders)

If you only want to use PalBaker to build, package, or manage your mods, you **do not** need to install Node.js, Rust, or Python.

1. Go to the [Releases](https://github.com/GoldenCarrotMLP/PalBaker/releases) page and download the latest installer (`.exe`).
2. Run the installer to set up PalBaker on your system.
3. **Prerequisites**:
   * Windows 10/11
   * Blender (v3.6 to v4.3+ are supported for headless 3D mesh reconstructions)
   * Unreal Engine 5.1 & any blank or existing unreal engine project

---

## ⚙️ Development Prerequisites (For Developers)

To run PalBaker in development mode or compile a production-ready release from source, your system must meet the following environments and compiler toolchains.

### 1. Windows Operating System
* The suite relies on Windows-specific binary dependencies (`UAssetGUI.exe`, `WwiseConsole.exe`, `vgmstream-cli.exe`) and shell command boundaries. 

### 2. Node.js & pnpm
* **Node.js**: Version `>= 20.x` is required.
* **pnpm**: Version `>= 9.x` is required. Enable globally via:
  ```bash
  npm install -g pnpm
  ```

### 3. Rust Toolchain (Tauri v2)
* Install **Rustup** and the stable Rust compiler.
* Complete the Tauri v2 Windows prerequisites (C++ Build Tools and Windows SDK).
* Run this command to verify or update your toolchain:
  ```bash
  rustup update stable
  ```

### 4. C++ Compiler & Build Tools (Visual Studio 2022)
* Install **Visual Studio 2022** (Community, Professional, or Enterprise).
* During installation, you **must** select the following workloads/components:
  * **Desktop development with C++**
  * **MSVC v143 - VS 2022 C++ x64/x86 build tools (v14.3x)** (Mandatory for compiling both Tauri Rust bindings and Unreal Engine 5.1 C++ modules).

### 5. Python 3.10+
* Ensure Python is added to your Windows environment variables (`PATH`).
* Install Python dependencies and ensure `pip` is updated:
  ```bash
  python -m pip install --upgrade pip
  ```

### 6. Complementary Game Utilities
* **Unreal Engine 5.1 & Palworld ModKit**: Required for micro-cooking and AnimBP compilation.
* **Blender**: Versions `3.6` to `4.3+` are supported.
* **Wwise 2022.1+ Authoring**: (Optional, but required if transcoding custom MP3/OGG Pal cries on the fly).

---

## 📂 Project Structure

```text
palbaker/
├── palbaker-cli/        # Python CLI backend (standalone orchestrator)
│   ├── deps/         # Third-party compiler & extraction binaries (UAssetGUI, cue4parse, etc.)
│   ├── plugins/      # Custom Unreal Engine C++ helper plugins
│   ├── utils/        # Pathing, workspace managers, and CLI command sub-handlers
│   └── unreal_scripts/# Scripts injected into Unreal Editor via Remote Execution
│
└── palbaker-ui/      # Next.js 16 frontend + Tauri v2 Rust desktop shell
    ├── app/          # State-based UI layouts
    ├── components/   # High-fidelity React components & setup wizards
    ├── lib/          # Frontend data-service API client
    └── src-tauri/    # Rust/Tauri native execution layer & IPC commands
```

---

## 🛠️ Local Development (For Developers)

Follow these steps to set up your monorepo workspace locally.

### 1. Clone the Repository
```bash
git clone https://github.com/YourUsername/PalBaker.git
cd PalBaker
```

### 2. Install Monorepo Dependencies
Run this command from the root directory to bootstrap the `pnpm` monorepo workspace:
```bash
pnpm install
```

### 3. Configure Local Path Settings
Before running pipelines, launch the application in development mode and navigate to **System Settings** to auto-detect or configure:
* Your Unreal Engine 5.1 root directory
* Active ModKit `.uproject` path
* Your Blender executable
* FModel export folders

### 4. Launch in Development Mode
To launch the Next.js dev server and mount the Tauri desktop webview simultaneously:
```bash
pnpm tauri dev
```
*Most UI changes support Hot Module Replacement (HMR) and will reflect instantly without restarting the shell.*

---

## 📦 Compiling a Production Release

The repository contains a custom node-based release manager (`build-release.mjs`) to automate full-stack compilation.

To build a standalone, distributable Windows installer (`.exe`):
```bash
pnpm release
```

### What this script does under the hood:
1. **Installs Python Dependencies:** Installs `pyinstaller` inside the Python environment.
2. **Compiles the Backend:** Invokes PyInstaller to freeze `palbaker_cli.py` using `palbaker_cli.spec`. This bundles Python 3.12, necessary libraries, and external binary dependencies (`UAssetGUI`, `cue4parse`, Wwise authoring schemas) into an optimized, self-contained subfolder (`_internal/`).
3. **Stages Tauri Resources:** Copies the compiled Python backend into the Tauri resource directory (`palbaker-ui/src-tauri/resources/backend`).
4. **Compiles Tauri & Next.js:** Runs `pnpm tauri build` to perform a Next.js static export (`out/`), compile the Rust IPC wrapper, and pack the bundle.
5. **Gathers Artifacts:** Outputs a production-ready NSIS installer (`PalBaker_x.x.x_x64_en-US.exe`) directly into the root `/release/` directory.

---

## 📡 Unreal Live Link Handshake (UDP Multicast)
PalBaker communicates with Unreal Editor in real-time using an unbuffered socket connection. If your pipeline fails to connect:
1. Open Unreal Editor and verify that **Project Settings -> Plugins -> Python -> Enable Remote Execution** is checked.
2. If you use virtual network adapters (WSL, Hyper-V, VMware, or VR Headsets), they can hijack local UDP multicast traffic. Temporarily disable non-essential adapters under **Control Panel -> Network Connections** to resolve loopback binding issues.
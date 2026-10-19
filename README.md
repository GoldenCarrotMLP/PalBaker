# PalBaker v2

An automated, monorepo-based desktop modding suite and toolchain for Palworld (built for Unreal Engine 5.1).

PalBaker bridges a **Next.js 16** frontend inside a **Tauri v2** desktop shell with a headless **Python 3.10+** backend CLI. It automates 3D mesh reconstruction (headlessly via Blender), C++ editor plugin compilation, asset packaging (via UnrealPak), dynamic audio transcoding (via Wwise), and standalone Pal generation (via PalSchema).

---

## 🦊 What PalBaker Does

Making a Palworld mod by hand means juggling FModel, Blender, an Unreal Engine 5.1 ModKit project, UnrealPak and several game-side mod loaders. PalBaker drives all of those tools for you from one app.

| Feature | What you get |
|---|---|
| **Mod Manager** | Reskin or remodel any Pal. PalBaker extracts the Pal from the game, rebuilds it as an editable `.blend`, imports your edited model into Unreal (materials, physics, sockets, AnimBP), then cooks and packs a ready-to-install `_P.pak`. |
| **Custom animations** | Dump a Pal's animations into Blender, edit them as NLA tracks, push them back and wire their notifies into montages. |
| **Dynamic Pals** | Instead of replacing every Chillet, add *variants* (different meshes, materials or shape-key sliders) that roll at spawn time by level, gender, trait, Lucky status and more. Output is a Format V2 `ModelJSON` for the Dynamic Pals mod. |
| **Pal Creator** | Create a brand-new species cloned from a vanilla Pal: stats, elements, work suitabilities, learnset, Paldeck entry, drops, breeding, wild spawns, boss/predator variants, and pinned spawns on an interactive map. Exported as a PalSchema mod plus a patched actor Blueprint. |
| **Audio** | Replace a Pal's cries (Normal, Joy, Anger, Sorrow, Pain, Death) with your own MP3/OGG/WAV, transcoded to Wwise `.wem`. |
| **Environment setup** | Auto-detects UE 5.1, Blender and Palworld, enables Unreal remote execution, compiles PalBaker's C++ editor plugin, and installs UE4SS and PalSchema. |
| **Decompile** | Turn an existing cooked mod back into a `.blend` workspace. |

## 🔁 How It Works

A typical reskin goes through these steps; each one is a button in the app and a command in the CLI:

1. **Extract** – CUE4Parse pulls the Pal's mesh (`.psk`), textures and material data out of the game's `.pak` files.
2. **Create Blend** – Blender runs headlessly to rebuild the model, materials and skeleton as a `.blend`, plus a `_blend.json` sidecar describing materials, shape keys and bones.
3. **Edit** – You change the model in Blender as usual.
4. **Push** – PalBaker exports FBX and sends Python to your running Unreal Editor (remote execution) to import the mesh, build material instances, copy sockets/virtual bones and generate the AnimBP.
5. **Cook & Pack** – Unreal cooks only your mod's assets, then UnrealPak bundles them into `<Mod>_P.pak` for `Pal/Content/Paks/~mods`.

Pal Creator and Dynamic Pals skip the pak step for their data: they write JSON straight into the PalSchema and Dynamic Pals mod folders in your game install.

## ⌨️ CLI at a Glance

Everything the app does goes through `palbaker-cli/palbaker_cli.py`, so you can also script it. Commands print logs to stdout and finish with a single-line JSON result (`{"status": "success", ...}`); long tasks stream JSONL progress.

| Group | Common commands | Purpose |
|---|---|---|
| `mod` | `extract`, `create-blend`, `push`, `cook`, `pack`, `full`, `decompile`, `dump-anims`, `push-anims` | Model/animation pipeline for one Pal, e.g. `mod push AmaterasuWolf Normal` |
| `dynamic_pals` | `toggle`, `list`, `add`, `save`, `delete` | Manage runtime variants |
| `creator` | `list`, `add <id> --template <Pal>`, `update`, `delete`, `refresh-bp`, `validate` | Standalone custom Pals |
| `audio` | `set`, `clear`, `play` | Custom cries |
| `env` | `verify`, `autodetect`, `install-plugin`, `ue4ss-install`, `palschema-install`, `launch-unreal`, `enable-remote-exec` | Environment setup and health |
| `manager` / `config` | `list`, `build-db`, `get-caches` / `get`, `set` | Mod discovery, reference caches, settings |

Full arguments and output formats are in [`commands.md`](commands.md); end-user guides live in [`palbaker-ui/public/docs`](palbaker-ui/public/docs/index.md) (also shown in the app).

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
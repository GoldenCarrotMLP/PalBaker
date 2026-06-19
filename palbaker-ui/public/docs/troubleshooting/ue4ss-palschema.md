# UE4SS & PalSchema Integration

To support advanced runtime modding features—like dynamic Altermatic variants or standalone custom Pals—your Palworld game directory must have UE4SS and the PalSchema mod correctly installed.

## 1. Unreal Engine 4/5 Scripting System (UE4SS)
UE4SS is a C++ scripting system and dll-injector that allows the game to load custom configurations, override blueprints, and hook memory functions.

**Installation**:
- Navigate to **System Settings** in PalBaker.
- Under Essential Binaries, click **Install Palworld-Experimental** (or *Latest-Experimental*).
- PalBaker will automatically download, extract, and register the core loader binaries (`dwmapi.dll`, `ue4ss.dll`) inside your game's `Win64/` binary directory.

---

## 2. PalSchema Mod
PalSchema is a master data mapping structure compiled by the modding community. It tells UE4SS exactly how the game's internal data structures and binary arrays are aligned so custom configurations can be safely serialized into memory.

**Installation**:
- Under Essential Binaries, click **Install PalSchema**.
- PalBaker will automatically fetch and extract the latest schema structures directly into your active UE4SS Mods folder, and safely enable mandatory core loaders inside `mods.txt`.
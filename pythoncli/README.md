# PalBaker (Palworld Mod Manager)

A dedicated, automated modding environment for Palworld that handles the pipeline from raw FModel extracts to a fully cooked and packed `_P.pak` file. It orchestrates Blender, Unreal Engine 5.1, and UnrealPak using a Flet-based UI.

## Features
* **State Tracking:** Detects whether a mod is in a raw state, has active source files (.blend), contains compiled Unreal Engine assets, or has been manually modified inside the Unreal Editor. Warns users before overwriting manual changes with exact file names.
* **Context-Aware Pipeline:** Offers specific actions based on the mod's current state (Push to Unreal, Cook & Pack, or Full Pipeline).
* **Headless Blender Integration:** Automatically converts `.blend` files to `.fbx` with forced bone scaling, rotation, and hierarchy parameters compatible with Palworld's physics limits.
* **Automated Advanced Rigging (Jiggle, Hair, & Offset Bones):** Extracts structural offsets and physics configurations directly from Blender's pose mode. Natively translates Blender's right-handed local space into Unreal's left-handed parent bone space to seamlessly preserve animations while altering character proportions or adding ragdoll spring physics.
* **Dynamic C++ Plugin Generation:** Automatically injects and headlessly compiles a custom Unreal Editor C++ module (`PalBakerEditorUtils`) using your MSVC toolchain, allowing the script to programmatically build and wire complex `AnimGraph` node trees.
* **Intelligent Animation Blueprint Binding:** Generates an Animation Blueprint from scratch if one doesn't exist, wires the custom physics/offset nodes, compiles it, and automatically binds the generated `_C` class to the Skeletal Mesh's Post-Process slot.
* **Compiler Diagnostics & Auto-Fix:** Includes a built-in diagnostic utility to scan your system for compliant MSVC v143 (14.3x) compiler toolsets and automatically repairs corrupted or misconfigured `BuildConfiguration.xml` files required for UE 5.1 building.
* **Unreal Engine Remote Execution:** Injects asset serialization commands directly into a running Unreal Editor instance, avoiding engine cold-boot times.
* **Targeted Micro-Cooking:** Temporarily overrides `DefaultGame.ini` to restrict the Unreal Cooker to the specific mod folder and skeleton directory, reducing cook times from minutes to seconds.
* **Safe Packaging:** Automatically filters out generated skeletons and physics assets during the packaging phase to prevent in-game ragdoll glitches.
* **Real-Time Progress Tracking & Memory UI Caching:** Parses Python subprocess stdout streams asynchronously to provide real-time UI updates. Employs an in-memory control caching system to handle queries and filtering instantly, preventing WebSocket channel clogging.
* **Native Multi-Format Audio Customization:** Supports custom audio overrides in WAV, MP3, and OGG formats. Implements an instant, on-the-fly compilation pipeline using Wwise Console and `vgmstream-cli` to provide immediate conversion feedback upon file upload, completely decoupled from Flet client rendering.
* **De-cluttered Modular Architecture:** Resolves complex packaging, file-system directories, and path computations into distinct, dedicated sub-modules (Workspaces, INI context managers, and staged audio resolvers), reducing the core builder script to a lightweight orchestrator.

## Prerequisites
1. Python 3.10+
2. Unreal Engine 5.1
3. Visual Studio 2022 (with MSVC v143 - C++ Desktop Development Workload)
4. An Unreal Engine 5.1 Project (it can be completely blank—PalBaker automatically injects its own required C++ plugin, master materials, and framework assets)
5. Blender

## Setup
1. Clone this repository.
2. Install Python dependencies: `pip install flet`
3. Run the manager: `python manager.py`
4. **MANDATORY FIRST STEP:** Upon launching, navigate directly to the **Settings** tab. You **MUST** configure all executable and directory paths (Unreal Engine root, `.uproject` path, Blender executable, etc.) before performing any mod actions. 
5. Once configured, click **Save and Reload Mod List**. PalBaker will automatically verify your compiler, inject and compile its required C++ helper plugin, and copy master materials inside your Unreal project.

## Usage
* Enable **Remote Execution** in your Unreal Engine Project Settings -> Python.
* Keep the Unreal Editor open.
* To create a custom skeleton, jiggle bones, or hair physics, simply rename bones in Blender to end with `_jiggle`, `_phy`, or `_hair` and adjust their pose.
* Use the UI to select a mod and execute the relevant build pipeline phase.
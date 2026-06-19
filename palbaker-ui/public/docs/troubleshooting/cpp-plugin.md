# Installing the C++ Helper Plugin

PalBaker requires a custom C++ Editor Utility Plugin (`PalBakerEditorUtils`) compiled directly inside your Unreal project to handle complex AnimGraph node generation and programmatically bind jiggle bones.

## Installation & Compilation Requirements

To compile this C++ plugin, your system must possess a compliant compiler toolset:
- **Visual Studio 2022** (Community, Professional, or Enterprise).
- Under the Visual Studio Installer workloads, you must have checked **Desktop development with C++**.
- Under Individual Components, you must have checked **MSVC v143 - VS 2022 C++ x64/x86 build tools (v14.3x)**.

---

## Automated Verification & Healing

If your compiler toolset is missing, misconfigured, or has broken paths:
1. Open PalBaker and click the **Verify Environment Prerequisites** button under Pipeline Health.
2. PalBaker will scan your drive letters for Visual Studio 2022, check for compliant MSVC toolsets, and automatically repair or generate your local `BuildConfiguration.xml` file.
3. Once repaired, click **Save & Verify Project Requirements** to headlessly build, link, and inject the compiled C++ binaries directly into your active Unreal ModKit Plugins folder!
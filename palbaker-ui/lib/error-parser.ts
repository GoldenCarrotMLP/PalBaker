/**
 * Smart Error Parser for Palworld pythoncli stdout and stderr diagnostics.
 */

export interface DiagnosticReport {
  category: "CONFIG" | "UNREAL_CONNECTIVITY" | "EXTRACTOR" | "BLENDER" | "COMPILER" | "CREATOR" | "AUDIO" | "COOK_PACK" | "GENERAL_ERROR"
  title: string
  friendlyMsg: string
  remediations: {
    label: string
    actionKey: "launch_unreal" | "go_to_settings" | "enable_remote_exec" | "close_game" | "autodetect_paths" | "rebuild_db" | "open_vs_installer" | "close_modal"
    style: "primary" | "secondary" | "warning" | "danger"
  }[]
}

export function parseBackendError(rawError: string): DiagnosticReport {
  const err = String(rawError).trim();

  // 1. CONFIGURATION & PATH ERRORS
  if (
    err.includes("Missing required setting") ||
    err.includes("does not exist on disk") ||
    err.includes("path is invalid") ||
    err.includes("not configured")
  ) {
    return {
      category: "CONFIG",
      title: "Configuration & Path Conflict",
      friendlyMsg: "Oh noes! It looks like one of our workspace directories is either missing or pointing to the wrong place qwq. Let's make sure our environment paths are set up correctly!",
      remediations: [
        { label: "⚙️ Go to Settings", actionKey: "go_to_settings", style: "primary" },
        { label: "🔍 Run Autodetect", actionKey: "autodetect_paths", style: "secondary" }
      ]
    };
  }

  // 2. UNREAL EDITOR CONNECTIVITY
  if (
    err.includes("Unreal Editor is not running") ||
    err.includes("Remote Execution is currently disabled") ||
    err.includes("connection timed out") ||
    err.includes("No response received from Unreal") ||
    err.includes("UDP handshake with Unreal") ||
    err.includes("UNREAL_CLOSED") ||
    err.includes("UNREAL_DISABLED")
  ) {
    return {
      category: "UNREAL_CONNECTIVITY",
      title: "Unreal Editor Offline",
      friendlyMsg: "Hmm, I can't reach Unreal Editor right now! ;3 Make sure it's fully opened with your active project, and that Python remote execution scripting is enabled.",
      remediations: [
        { label: "🚀 Launch Unreal Editor", actionKey: "launch_unreal", style: "primary" },
        { label: "🔌 Enable Remote Execution", actionKey: "enable_remote_exec", style: "secondary" },
        { label: "⚙️ Go to Settings", actionKey: "go_to_settings", style: "secondary" }
      ]
    };
  }

  // 3. ARCHIVE EXTRACTION & LOCALIZATION
  if (
    err.includes("cue4parse") ||
    err.includes("usmap") ||
    err.includes("DataTable Rows") ||
    err.includes("text localization") ||
    err.includes("DT_PalNameText")
  ) {
    return {
      category: "EXTRACTOR",
      title: "FModel / Cue4Parse Failure",
      friendlyMsg: "Poki, I couldn't extract the raw Pal assets or translate their name entries! We might be missing standard Mappings or our cue4parse dependencies in 'deps/'. Let's check them!",
      remediations: [
        { label: "⚙️ Go to Settings", actionKey: "go_to_settings", style: "primary" },
        { label: "📦 Rebuild Database Map", actionKey: "rebuild_db", style: "secondary" }
      ]
    };
  }

  // 4. BLENDER HEADLESS PIPELINE
  if (
    err.includes("Failed to pre-install PSK addon") ||
    err.includes("no .psk skeletal mesh found") ||
    err.includes("Blender executed but failed to save") ||
    err.includes("Skeletal blend file not found") ||
    err.includes("Failed to launch Blender")
  ) {
    return {
      category: "BLENDER",
      title: "Blender Headless Error",
      friendlyMsg: "Aww, headless Blender failed to reconstruct or save our .blend workspace file qwq! Make sure your configured Blender path is correct, and that the PSK skeletal mesh import addon isn't blocked.",
      remediations: [
        { label: "⚙️ Go to Settings", actionKey: "go_to_settings", style: "primary" }
      ]
    };
  }

  // 5. MSVC C++ COMPILER & TOOLSETS
  if (
    err.includes("No Visual Studio 2022") ||
    err.includes("No compliant v143") ||
    err.includes("RunUAT compilation failed") ||
    err.includes("UnrealBuildTool.exe") ||
    err.includes("compiler toolset")
  ) {
    return {
      category: "COMPILER",
      title: "C++ Compiler Missing",
      friendlyMsg: "Our C++ compilation tools are missing or outdated! Unreal Engine 5.1 requires the MSVC v143 compiler toolset (from Visual Studio 2022) to compile development plugins.",
      remediations: [
        { label: "📥 Install VS 2022 Build Tools", actionKey: "open_vs_installer", style: "primary" },
        { label: "⚙️ Go to Settings", actionKey: "go_to_settings", style: "secondary" }
      ]
    };
  }

  // 6. STANDALONE PAL CREATION
  if (
    err.includes("UAssetGUI") ||
    err.includes("already exists") ||
    err.includes("reserved vanilla Pal") ||
    err.includes("blueprint patching routine crashed")
  ) {
    return {
      category: "CREATOR",
      title: "Pal Creator Collision",
      friendlyMsg: "Oh! There was a naming collision or a serialization glitch during blueprint patching! Make sure your new Pal ID doesn't conflict with a vanilla Pal, and that UAssetGUI.exe exists in your dependencies.",
      remediations: [
        { label: "✏️ Try Another Name", actionKey: "close_modal", style: "primary" },
        { label: "⚙️ Go to Settings", actionKey: "go_to_settings", style: "secondary" }
      ]
    };
  }

  // 7. WWISE AUDIO pipeline
  if (
    err.includes("vgmstream-cli") ||
    err.includes("Wwise environment not found") ||
    err.includes("Failed to generate .wem") ||
    err.includes("transcode")
  ) {
    return {
      category: "AUDIO",
      title: "Wwise Transcoding Failure",
      friendlyMsg: "I couldn't transcode or compile the custom audio override qwq! Make sure vgmstream-cli.exe and Wwise are installed in your 'deps/' folders, and the source audio file isn't corrupted.",
      remediations: [
        { label: "⚙️ Go to Settings", actionKey: "go_to_settings", style: "primary" }
      ]
    };
  }

  // 8. COOK & PACK SYSTEM
  if (
    err.includes("Cannot overwrite") ||
    err.includes("Close the game") ||
    err.includes("COOK FAILED") ||
    err.includes("Low Physical Memory")
  ) {
    return {
      category: "COOK_PACK",
      title: "Cooking File Lock",
      friendlyMsg: "Eeeek! It looks like our pak files are locked by the game or Unreal Editor, or your system is running low on RAM! Please make sure Palworld is completely closed, and try again!",
      remediations: [
        { label: "🛑 Force Close Palworld", actionKey: "close_game", style: "danger" },
        { label: "⚙️ Go to Settings", actionKey: "go_to_settings", style: "secondary" }
      ]
    };
  }

  // GENERAL DEFAULT FALLBACK
  return {
    category: "GENERAL_ERROR",
    title: "Backend Execution Error",
    friendlyMsg: "Oopsies! The pythoncli returned an unexpected error qwq. Review the full technical logs below to see what happened!",
    remediations: [
      { label: "Dismiss", actionKey: "close_modal", style: "secondary" }
    ]
  };
}

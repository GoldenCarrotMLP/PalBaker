/**
 * Smart Error Parser for Palworld palbaker-cli stdout and stderr diagnostics.
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
  let err = String(rawError).trim();

  // 0. NO FILES FOUND TO PACK
  if (
    err.includes("No files found to pack") ||
    err.includes("Cook process might have failed")
  ) {
    return {
      category: "COOK_PACK",
      title: "Packaging Failed",
      friendlyMsg: "ERROR: No files found to pack. Cook process might have failed.\n\nUnreal Engine finished cooking, but no .uasset files were found in the cooked directory for this character or variant to pack into the .pak archive.",
      remediations: [
        { label: "Dismiss", actionKey: "close_modal", style: "primary" }
      ]
    };
  }

  // 1. PHYSICAL MEMORY (RAM) LIMIT EXHAUSTIONS
  // Detects the signature of the low memory block immediately
  if (
    err.includes("Low Physical Memory") || 
    err.includes("free RAM is available") || 
    err.includes("Win32 memory limits")
  ) {
    let extractedMsg = "";
    
    // Attempt to extract the exact text from the JSON line outputted by the background thread
    const match = err.match(/"message":\s*"([^"]*(?:Low Physical Memory|free RAM is available)[^"]*)"/i);
    if (match && match[1]) {
      extractedMsg = match[1];
    } else {
      // Fallback: extract the physical raw line containing the memory limits
      const lines = err.split(/[\r\n]+/);
      const matchedLine = lines.find(l => l.includes("Low Physical Memory") || l.includes("free RAM is available"));
      extractedMsg = matchedLine ? matchedLine.trim() : err;
    }

    // Clean up escaped sequences left by JSON serialization
    extractedMsg = extractedMsg.replace(/\\"/g, '"').replace(/\\n/g, '\n');

    return {
      category: "COOK_PACK",
      title: "Low System Memory Warning",
      friendlyMsg: extractedMsg, // Forward raw backend message directly
      remediations: [
        { label: "Dismiss", actionKey: "close_modal", style: "primary" }
      ]
    };
  }

  // Unpack raw JSON error envelopes to extract the core descriptive message for downstream checks
  try {
    const parsed = JSON.parse(err);
    if (parsed && typeof parsed === "object") {
      const parsedObj = parsed as Record<string, unknown>;
      if (typeof parsedObj.message === "string") {
        err = parsedObj.message;
      } else if (typeof parsedObj.error === "string") {
        err = parsedObj.error;
      }
    }
  } catch {
    // Not a JSON string, keep it as is
  }

  // 2. CONFIGURATION & PATH ERRORS
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

  // 3. UNREAL EDITOR CONNECTIVITY
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

  // 4. ARCHIVE EXTRACTION & LOCALIZATION
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
      friendlyMsg: "I couldn't extract the raw Pal assets or translate their name entries! We might be missing standard Mappings or our cue4parse dependencies in 'deps/'. Let's check them!",
      remediations: [
        { label: "⚙️ Go to Settings", actionKey: "go_to_settings", style: "primary" },
        { label: "📦 Rebuild Database Map", actionKey: "rebuild_db", style: "secondary" }
      ]
    };
  }

  // 5. BLENDER HEADLESS PIPELINE
  if (
    err.includes("Failed to pre-install PSK addon") ||
    err.includes("no .psk skeletal mesh found") ||
    err.includes("Blender executed but failed to save") ||
    err.includes("Skeletal mesh blend file not found") ||
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

  // 5b. RIGGING & ARMATURE ERRORS
  if (err.includes("StaticMesh instead of a SkeletalMesh")) {
    return {
      category: "BLENDER",
      title: "Armature/Rigging Error",
      friendlyMsg: "Oh noes! Unreal Engine imported your model as a StaticMesh instead of a SkeletalMesh! This usually happens if your mesh isn't parented to the 'Armature' in Blender, or it has no vertex weights assigned. Please open your .blend file, fix the parenting, and try again! ;3",
      remediations: [
        { label: "Dismiss", actionKey: "close_modal", style: "secondary" }
      ]
    };
  }

  // 6. MSVC C++ COMPILER & TOOLSETS
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

  // 7. STANDALONE PAL CREATION
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

  // 8. WWISE AUDIO pipeline
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

  // 8a. PACKAGING - NO COOKED FILES FOUND
  if (
    err.includes("No files found to pack") ||
    err.includes("Cook process might have failed")
  ) {
    return {
      category: "COOK_PACK",
      title: "No Cooked Files Found",
      friendlyMsg: "ERROR: No files found to pack. Cook process might have failed.\n\nUnreal Engine finished cooking, but no compiled .uasset files were found in the cooked output directory to bundle into the .pak archive.",
      remediations: [
        { label: "Dismiss", actionKey: "close_modal", style: "primary" }
      ]
    };
  }

  // 8b. SPECIFIC UNREAL COMPILATION & ASSET FAILURES
  if (
    err.includes("[AssetLog]") ||
    err.includes("LogBlueprint: Error") ||
    (err.includes(".uasset") && err.includes("[Compiler]")) ||
    err.includes("unknown Anim Sequence Base")
  ) {
    // Locate the line specifically mentioning the asset
    const lines = err.split(/[\r\n]+/);
    const errorLine = lines.find(l => 
      (l.includes("[AssetLog]") || l.includes("LogBlueprint: Error") || l.includes("[Compiler]")) &&
      (l.includes(".uasset") || l.includes(".umap"))
    ) || lines.find(l => l.includes("[AssetLog]")) || err;

    // Extract file path (Windows: F:\... or virtual: /Game/...)
    const fileMatch = errorLine.match(/([a-zA-Z]:\\[^\s:]+\.(?:uasset|umap))/i) ||
                      errorLine.match(/(\/Game\/[^\s:]+\.(?:uasset|umap))/i);
    
    const fullPath = fileMatch ? fileMatch[1].trim() : "";
    const fileName = fullPath ? fullPath.split(/[\\/]/).pop() || "Asset" : "Broken Asset";

    // Extract the compiler or error message after the file path
    let reason = "";
    if (fullPath && errorLine.includes(fullPath)) {
      const afterFile = errorLine.split(fullPath)[1];
      if (afterFile) {
        reason = afterFile.replace(/^[:\s]+/, "").trim();
      }
    }
    if (!reason) {
      const compilerMatch = errorLine.match(/(\[Compiler\].*)/i);
      if (compilerMatch) {
        reason = compilerMatch[1].trim();
      } else {
        reason = errorLine.replace(/.*(?:Error:|\[AssetLog\])/i, "").trim();
      }
    }

    let friendlyMsg = `Cook failed on: ${fileName}\n\n`;
    if (reason) {
      friendlyMsg += `Reason: ${reason}\n\n`;
    }
    if (fullPath) {
      friendlyMsg += `File: ${fullPath}`;
    }

    return {
      category: "COMPILER",
      title: `Failed Asset: ${fileName}`,
      friendlyMsg: friendlyMsg.trim(),
      remediations: [
        { label: "Dismiss", actionKey: "close_modal", style: "primary" }
      ]
    };
  }
  
  // 9. COOK & PACK SYSTEM
  if (
    err.includes("Cannot overwrite") ||
    err.includes("Close the game")
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
  
  if (err.includes("COOK FAILED") || err.includes("Pipeline action cook failed") || err.includes("Pipeline action pack failed")) {
     return {
      category: "COOK_PACK",
      title: "Cook Process Failed",
      friendlyMsg: "The Unreal Cooker failed to process your assets! Review the red error lines in the terminal below to see exactly which file caused the crash.",
      remediations: [
        { label: "Dismiss", actionKey: "close_modal", style: "primary" }
      ]
     }
  }

  // GENERAL DEFAULT FALLBACK
  return {
    category: "GENERAL_ERROR",
    title: "Backend Execution Error",
    friendlyMsg: "Oopsies! The palbaker-cli returned an unexpected error qwq. Review the full technical logs below to see what happened!",
    remediations: [
      { label: "Dismiss", actionKey: "close_modal", style: "secondary" }
    ]
  };
}
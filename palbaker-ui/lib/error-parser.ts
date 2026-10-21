/**
 * Smart Error Parser for Palworld palbaker-cli stdout and stderr diagnostics.
 *
 * Every rule here mirrors an error the Python CLI can emit (search the quoted text in palbaker-cli/).
 * Rules are matched against the backend's final error message only, never the whole build log, so
 * an unrelated log line (e.g. "asset already exists") can't trigger the wrong explanation.
 */

export interface DiagnosticReport {
  category: "CONFIG" | "UNREAL_CONNECTIVITY" | "PROJECT" | "EXTRACTOR" | "BLENDER" | "COMPILER" | "CREATOR" | "AUDIO" | "COOK_PACK" | "MATERIALS" | "ANIMATION" | "MOD" | "GENERAL_ERROR"
  title: string
  friendlyMsg: string
  // What the backend actually reported, shown verbatim under the explanation
  detail?: string
  // Folder the user has to put files into to fix the error (shown with a copy button)
  folder?: string
  remediations: {
    label: string
    actionKey: "launch_unreal" | "go_to_settings" | "enable_remote_exec" | "close_game" | "autodetect_paths" | "rebuild_db" | "open_vs_installer" | "close_modal"
    style: "primary" | "secondary" | "warning" | "danger"
  }[]
}

type Remediation = DiagnosticReport["remediations"][number]

const DISMISS: Remediation[] = [{ label: "Dismiss", actionKey: "close_modal", style: "primary" }]
const SETTINGS: Remediation[] = [{ label: "⚙️ Go to Settings", actionKey: "go_to_settings", style: "primary" }]

interface Rule {
  match: (string | RegExp)[]
  category: DiagnosticReport["category"]
  title: string
  // Receives the backend message so the explanation can quote names and paths from it
  friendlyMsg: string | ((err: string) => string)
  remediations?: Remediation[]
}

const GENERIC_PIPELINE_LINE = /^Pipeline action \S+ failed with exit code: -?\d+$/

/**
 * Returns the message of the last {"status": "error"} envelope when given raw JSONL stdout,
 * the unwrapped message for a single JSON envelope, or the text itself.
 */
function extractCoreMessage(raw: string): string {
  const lines = raw.split(/\r?\n/)
  for (let i = lines.length - 1; i >= 0; i--) {
    const line = lines[i]
    const start = line.indexOf("{")
    const end = line.lastIndexOf("}")
    if (start < 0 || end <= start) continue
    try {
      const parsed = JSON.parse(line.slice(start, end + 1)) as Record<string, unknown>
      if (parsed && typeof parsed === "object" && parsed.status === "error") {
        if (typeof parsed.message === "string") return parsed.message
        if (typeof parsed.error === "string") return parsed.error
      }
    } catch {
      // Not a JSON line
    }
  }
  return raw
}

export interface LogDiagnosis {
  title: string
  solution: string
  assets: string[]
}

const DIAGNOSIS_MARKER = /\[PalBaker Diagnosis\]\s*(\[.*\])/

/**
 * Signatures utils/builder/log_analyzer.py found anywhere in the build log, appended by
 * mod_handlers.py as "[PalBaker Diagnosis] [...]" (and as "diagnostics" on successful results).
 */
export function parseLogDiagnosis(err: string): LogDiagnosis[] {
  const match = err.match(DIAGNOSIS_MARKER)
  if (!match) return []
  try {
    const parsed = JSON.parse(match[1])
    return Array.isArray(parsed) ? parsed.filter(d => d && typeof d.title === "string") : []
  } catch {
    return []
  }
}

function formatDiagnosis(diagnosis: LogDiagnosis[]): string {
  return diagnosis.map(d => {
    const assets = d.assets?.length ? `\nAffected: ${d.assets.join(", ")}` : ""
    return `• ${d.title}\n${d.solution}${assets}`
  }).join("\n\n")
}

/** The backend message minus the generic "Pipeline action X failed" line, trimmed for display. */
function toDetail(err: string): string | undefined {
  const lines = err.split(/\r?\n/).map(l => l.trim()).filter(l => l && !GENERIC_PIPELINE_LINE.test(l) && !DIAGNOSIS_MARKER.test(l))
  const text = lines.join("\n")
  if (!text) return undefined
  return text.length > 1200 ? text.slice(0, 1200) + "…" : text
}

function matchesAny(err: string, patterns: (string | RegExp)[]): boolean {
  return patterns.some(p => (typeof p === "string" ? err.includes(p) : p.test(err)))
}

function capture(err: string, re: RegExp, fallback = ""): string {
  const m = err.match(re)
  return m && m[1] ? m[1] : fallback
}

const RULES: Rule[] = [
  // ---------------- CONFIGURATION & PATHS ----------------
  {
    match: ["Missing required setting"],
    category: "CONFIG",
    title: "Setting Not Configured",
    friendlyMsg: err => `PalBaker needs the '${capture(err, /Missing required setting: '([^']+)'/, "required")}' setting before it can run this.\n\nOpen Settings and fill it in, or use Autodetect to find it for you.`,
    remediations: [...SETTINGS, { label: "🔍 Run Autodetect", actionKey: "autodetect_paths", style: "secondary" }]
  },
  {
    match: ["does not exist on disk"],
    category: "CONFIG",
    title: "Configured Path Not Found",
    friendlyMsg: err => `The path saved for '${capture(err, /path for '([^']+)'/, "a setting")}' doesn't exist anymore:\n${capture(err, /on disk: '([^']+)'/, "(unknown path)")}\n\nIt may have been moved or renamed, or it's on a drive that isn't connected. Update it in Settings.`,
    remediations: [...SETTINGS, { label: "🔍 Run Autodetect", actionKey: "autodetect_paths", style: "secondary" }]
  },
  {
    match: ["Paks directory not found or Palworld.exe path is invalid"],
    category: "CONFIG",
    title: "Palworld Game Files Not Found",
    friendlyMsg: "PalBaker reads vanilla assets straight from Palworld's .pak files, but couldn't find the Paks folder from your Palworld.exe setting.\n\nSet 'Palworld.exe Path' in Settings to the Palworld.exe in your game's install folder (the one that has the 'Pal' folder next to it).",
    remediations: [...SETTINGS, { label: "🔍 Run Autodetect", actionKey: "autodetect_paths", style: "secondary" }]
  },
  {
    match: ["FModel output folder is not configured", "No FModel path found"],
    category: "CONFIG",
    title: "Workspace Folder Not Set",
    friendlyMsg: "PalBaker doesn't know where your workspace (FModel Output) folder is. Set 'Workspace Folder' in Settings to FModel's Output folder.",
    remediations: SETTINGS
  },
  {
    match: ["Could not find RunUAT.bat", "Could not find UnrealBuildTool.exe", "Could not find UnrealEditor.exe", "Could not find remote_execution.py", "Could not locate remote_execution.py"],
    category: "CONFIG",
    title: "Unreal Engine Path Invalid",
    friendlyMsg: "PalBaker couldn't find Unreal Engine's tools in the configured 'Unreal Engine Root'.\n\nIt has to point at the UE 5.1 install folder itself, the one that contains 'Engine' (for example C:\\Program Files\\Epic Games\\UE_5.1).",
    remediations: SETTINGS
  },
  {
    match: ["Environment path verification failed"],
    category: "CONFIG",
    title: "Environment Check Failed",
    friendlyMsg: "One or more of your configured paths failed verification. The red ❌ lines in the Build Console say exactly which ones. Fix them in Settings and verify again.",
    remediations: SETTINGS
  },
  {
    match: [/^Path does not exist: /m, "Empty path"],
    category: "CONFIG",
    title: "Folder Doesn't Exist Yet",
    friendlyMsg: "This folder hasn't been created yet. It appears once the matching step has run (Extract for the source folder, Push for the Unreal folder, Cook & Pack for the .pak).",
    remediations: DISMISS
  },

  // ---------------- UNREAL EDITOR & PROJECT ----------------
  {
    match: ["Unreal Editor is not running", "Remote Execution is currently disabled", "connection timed out", "No response received from Unreal", "UDP handshake with Unreal", "Unreal remote connection check failed", "Remote party failed to send a valid response", "UNREAL_CLOSED", "UNREAL_DISABLED"],
    category: "UNREAL_CONNECTIVITY",
    title: "Unreal Editor Offline",
    friendlyMsg: "Hmm, I can't reach Unreal Editor right now! ;3 Make sure it's fully opened with your active project, and that Python remote execution scripting is enabled.\n\nIf it's open and enabled, restart the editor; a firewall blocking local UDP traffic can also cause this.",
    remediations: [
      { label: "🚀 Launch Unreal Editor", actionKey: "launch_unreal", style: "primary" },
      { label: "🔌 Enable Remote Execution", actionKey: "enable_remote_exec", style: "secondary" },
      ...SETTINGS
    ]
  },
  {
    match: ["Failed to focus Unreal"],
    category: "UNREAL_CONNECTIVITY",
    title: "Couldn't Open Content Browser",
    friendlyMsg: "Unreal Editor didn't respond when PalBaker tried to show this folder. Make sure the editor is open and not busy (compiling shaders, a modal dialog open) and try again.",
    remediations: DISMISS
  },
  {
    match: ["Failed to enable Python Remote Execution"],
    category: "UNREAL_CONNECTIVITY",
    title: "Couldn't Enable Remote Execution",
    friendlyMsg: "The Remote Execution setting didn't stick because Unreal Editor rewrote DefaultEngine.ini while it was open.\n\nClose Unreal Editor completely, click 'Enable Remote Execution' again, then relaunch the editor.",
    remediations: DISMISS
  },
  {
    match: ["Failed to launch Unreal Editor"],
    category: "CONFIG",
    title: "Unreal Editor Failed to Start",
    friendlyMsg: "PalBaker couldn't start Unreal Editor. Check that 'Unreal Engine Root' and 'Palworld ModKit .uproject Path' in Settings are correct, or open the project manually.",
    remediations: SETTINGS
  },
  {
    match: ["C++ Editor Helper Plugin is missing or outdated", "missing or outdated in your Unreal project"],
    category: "PROJECT",
    title: "Helper Plugin Missing",
    friendlyMsg: "Your ModKit project is missing PalBaker's C++ helper plugin (PalBakerEditorUtils), or it's outdated. PalBaker needs it to wire up Animation Blueprints, sockets and retargeting.\n\nInstall it below, then restart Unreal Editor.",
    remediations: DISMISS
  },
  {
    match: ["missing crucial master materials"],
    category: "PROJECT",
    title: "Master Materials Missing",
    friendlyMsg: "Your ModKit project doesn't have the master materials PalBaker builds its material instances from. Inject them below and run the action again.",
    remediations: DISMISS
  },
  {
    match: ["Project Validation Failed"],
    category: "PROJECT",
    title: "Project Validation Failed",
    friendlyMsg: "Your Unreal project didn't pass PalBaker's requirements check. The details below say what's wrong. Open Settings to verify the project requirements again once it's fixed.",
    remediations: SETTINGS
  },
  {
    match: ["Cannot create Animation Blueprint because skeleton"],
    category: "BLENDER",
    title: "Skeleton Not Found",
    friendlyMsg: "The mesh was imported but Unreal couldn't resolve its skeleton, so no Animation Blueprint could be made.\n\nIn Blender, make sure every mesh is parented to the armature named 'Armature' and has vertex weights, then push again.",
    remediations: DISMISS
  },
  {
    match: ["Failed to instantiate Animation Blueprint"],
    category: "PROJECT",
    title: "Animation Blueprint Creation Failed",
    friendlyMsg: "Unreal refused to create the Animation Blueprint. This is usually a stale or broken ABP left at the same path.\n\nDelete the old ABP_* asset for this mod in Unreal's Content Browser and push again.",
    remediations: DISMISS
  },
  {
    match: ["StaticMesh instead of a SkeletalMesh"],
    category: "BLENDER",
    title: "Armature/Rigging Error",
    friendlyMsg: "Oh noes! Unreal Engine imported your model as a StaticMesh instead of a SkeletalMesh! This usually happens if your mesh isn't parented to the 'Armature' in Blender, or it has no vertex weights assigned. Please open your .blend file, fix the parenting, and try again! ;3",
    remediations: DISMISS
  },
  {
    match: ["Invalid USkeleton supplied", "The skeleton asset for this animation Blueprint is missing"],
    category: "PROJECT",
    title: "Broken Skeleton Reference",
    friendlyMsg: "Unreal has references to a skeleton that was deleted or renamed. Delete the old SK_* assets and stale AnimBlueprints for this mod in the Content Browser, then push again.",
    remediations: DISMISS
  },
  {
    match: ["VerifyImport: Failed to load package", "Failed to load '/Game/"],
    category: "PROJECT",
    title: "Missing Asset Reference",
    friendlyMsg: "Your project references assets that no longer exist. In Unreal, right-click your Content folder and choose 'Fix Up Redirectors in Folder', then try again.",
    remediations: DISMISS
  },

  // ---------------- MOD PIPELINE ----------------
  {
    match: ["Collision Lock:"],
    category: "MOD",
    title: "Vanilla Mode Conflict",
    friendlyMsg: err => `Mod '${capture(err, /Mod '([^']+)'/, "another mod")}' already replaces ${capture(err, /base '([^']+)'/, "this Pal")} in Vanilla mode and is pushed to Unreal. Two Vanilla mode mods on the same Pal overwrite each other's assets in the editor.\n\nSwitch one of them to Dynamic Pals mode, then run the action again.`,
    remediations: DISMISS
  },
  {
    match: ["No .psk skeletal mesh found", "no .psk skeletal mesh found"],
    category: "MOD",
    title: "Pal Not Extracted",
    friendlyMsg: "There's no extracted .psk model in this mod's workspace folder yet. Run 'Extract' for this mod first so PalBaker can pull the base Pal's mesh from the game files.",
    remediations: DISMISS
  },
  {
    match: ["No raw model sources found in workspaces to push", "No .blend files found in workspace"],
    category: "MOD",
    title: "No .blend File Found",
    friendlyMsg: "This mod's workspace folder has no .blend file to work from. Run 'Create Blend' first, or put your .blend file into the mod's folder (Open Source Folder shows where).",
    remediations: DISMISS
  },
  {
    match: ["Sidecar layout generation failed", "Blender failed to save .blend", "Blender executed but failed to save", "Headless Blender failed to export FBX"],
    category: "BLENDER",
    title: "Blender Processing Failed",
    friendlyMsg: "Headless Blender crashed while working on your .blend file. The details below show the Python error it hit.\n\nCommon causes: the file was saved with a newer Blender than the one in Settings, a required addon is missing, or a mesh has broken modifiers. Open the file in the configured Blender version and check that it loads cleanly.",
    remediations: SETTINGS
  },
  {
    match: ["Failed to pre-install PSK addon", "Skeletal mesh blend file not found", "Failed to launch Blender", "Failed to execute Blender process", "No PSK importer addon", "io_scene_psk_psa"],
    category: "BLENDER",
    title: "Blender Headless Error",
    friendlyMsg: "Aww, headless Blender failed to reconstruct or save our .blend workspace file qwq! Make sure your configured Blender path is correct, and that the PSK skeletal mesh import addon isn't blocked.",
    remediations: SETTINGS
  },
  {
    match: ["[PalBaker Animation Guard]", "Please click 'Push Animations'"],
    category: "ANIMATION",
    title: "Animations Not Pushed",
    friendlyMsg: "Custom animations are turned on for this mod, but Unreal doesn't have all the animation assets they need yet.\n\nClick 'Push Animations' for this mod, then cook again. The details below list what's missing.",
    remediations: DISMISS
  },
  {
    match: ["past montage length"],
    category: "ANIMATION",
    title: "Notify Past End of Animation",
    friendlyMsg: "An anim notify is placed after the end of its montage, and Unreal would crash on it. Open the animation in the Animations editor and move the listed notify(s) inside the animation's length.",
    remediations: DISMISS
  },
  {
    match: ["Failed to read Dynamic Pals manifest", "Failed to write deployment JSON"],
    category: "MOD",
    title: "Dynamic Pals Config Error",
    friendlyMsg: "PalBaker couldn't read or write this mod's Dynamic Pals configuration. The *_dynamic_pals.json file may be corrupted or locked by another program, or the game's Mods folder isn't writable. Close Palworld and try again.",
    remediations: DISMISS
  },
  {
    match: ["Pipeline execution crashed"],
    category: "GENERAL_ERROR",
    title: "PalBaker Crashed",
    friendlyMsg: "PalBaker's build worker crashed before it could finish. This is a bug, not something you did. Please report it with the details below and the Build Console log.",
    remediations: DISMISS
  },

  // ---------------- EXTRACTION ----------------
  {
    match: ["Missing cue4parse.exe dependency", "Missing Mappings.usmap dependency"],
    category: "EXTRACTOR",
    title: "Extraction Tools Missing",
    friendlyMsg: "PalBaker's bundled extraction files (cue4parse.exe / Mappings.usmap in the 'deps' folder) are missing. Antivirus software sometimes quarantines them. Restore them or reinstall PalBaker.",
    remediations: DISMISS
  },
  {
    match: ["cue4parse exited with code", "Failed to execute cue4parse.exe"],
    category: "EXTRACTOR",
    title: "Game Asset Extraction Failed",
    friendlyMsg: "cue4parse couldn't read Palworld's .pak files. After a game update this usually means the bundled Mappings.usmap is out of date, so check for a PalBaker update. Also make sure your Palworld.exe path points at the current install.",
    remediations: [...SETTINGS, { label: "📦 Rebuild Database Map", actionKey: "rebuild_db", style: "secondary" }]
  },
  {
    match: ["Failed to locate or extract any assets for", "Extracted assets missing for", "Failed to extract raw assets"],
    category: "EXTRACTOR",
    title: "Pal Assets Not Found",
    friendlyMsg: "PalBaker couldn't find this Pal's model files in the game archives. The Pal may have been renamed or moved by a game update, or the base Pal name doesn't match a real game folder.",
    remediations: [{ label: "📦 Rebuild Database Map", actionKey: "rebuild_db", style: "primary" }]
  },
  {
    match: ["usmap", "DataTable Rows", "text localization", "DT_PalNameText", "Extracted file not found", "Exception during icon extraction"],
    category: "EXTRACTOR",
    title: "FModel / Cue4Parse Failure",
    friendlyMsg: "I couldn't extract the raw Pal assets or translate their name entries! We might be missing standard Mappings or our cue4parse dependencies in 'deps/'. Let's check them!",
    remediations: [...SETTINGS, { label: "📦 Rebuild Database Map", actionKey: "rebuild_db", style: "secondary" }]
  },
  {
    match: ["No FBX assets were exported by Unreal", "Export failed inside Unreal"],
    category: "PROJECT",
    title: "Unreal Export Failed",
    friendlyMsg: "Unreal didn't export any meshes for this decompile. Make sure the mod has been pushed to Unreal and its SkeletalMesh exists in the Content Browser.",
    remediations: DISMISS
  },

  // ---------------- MSVC C++ COMPILER ----------------
  {
    match: ["No Visual Studio 2022", "No compliant v143", "RunUAT compilation failed", "UnrealBuildTool.exe", "compiler toolset", /^Compilation failed/m],
    category: "COMPILER",
    title: "C++ Compiler Missing",
    friendlyMsg: "Our C++ compilation tools are missing or outdated! Unreal Engine 5.1 requires the MSVC v143 compiler toolset (from Visual Studio 2022) to compile development plugins.",
    remediations: [
      { label: "📥 Install VS 2022 Build Tools", actionKey: "open_vs_installer", style: "primary" },
      ...SETTINGS
    ]
  },

  // ---------------- PAL CREATOR ----------------
  {
    match: ["UAssetGUI tojson failed", "UAssetGUI"],
    category: "CREATOR",
    title: "Asset Decompile Failed",
    friendlyMsg: "UAssetGUI couldn't convert one of the game assets this Pal is built from. Make sure deps/UAssetGUI.exe exists (antivirus can remove it) and that the donor Pal's assets were extracted.",
    remediations: DISMISS
  },
  {
    match: ["already exists", "reserved vanilla Pal", "blueprint patching routine crashed"],
    category: "CREATOR",
    title: "Pal Creator Collision",
    friendlyMsg: "Oh! There was a naming collision or a serialization glitch during blueprint patching! Make sure your new Pal ID doesn't conflict with a vanilla Pal.",
    remediations: [{ label: "✏️ Try Another Name", actionKey: "close_modal", style: "primary" }]
  },
  {
    match: ["Unknown evasion style", "No valid character class resolved for funnel", "Invalid leaning mode", "Unknown utility skill", "Unknown weapon mode", "lacks a SimpleConstructionScript_0"],
    category: "CREATOR",
    title: "Invalid Pal Feature Setting",
    friendlyMsg: "One of the features configured for this Pal has a value PalBaker doesn't support (the details below list the valid options). Pick a different option for that feature and try again.",
    remediations: DISMISS
  },
  {
    match: ["Deployment failed", "PalSchema action failed"],
    category: "CREATOR",
    title: "PalSchema Deploy Failed",
    friendlyMsg: "PalBaker couldn't install or write to PalSchema in your game folder. Close Palworld (it locks the Mods folder), make sure the Palworld.exe path is correct, and try again.",
    remediations: [{ label: "🛑 Force Close Palworld", actionKey: "close_game", style: "danger" }, ...SETTINGS]
  },
  {
    match: [/^Action failed: /m],
    category: "CONFIG",
    title: "UE4SS Install Failed",
    friendlyMsg: "The UE4SS install/uninstall didn't finish. Close Palworld, check your internet connection and the Palworld.exe path, then try again. The Build Console has the step that failed.",
    remediations: [{ label: "🛑 Force Close Palworld", actionKey: "close_game", style: "danger" }, ...SETTINGS]
  },

  // ---------------- WWISE AUDIO ----------------
  {
    match: ["No media_id found for"],
    category: "AUDIO",
    title: "Unknown Pal Cry",
    friendlyMsg: "This cry slot has no matching sound in the game's audio data, so there's nothing to replace. Pick a different cry for this Pal.",
    remediations: DISMISS
  },
  {
    match: ["vgmstream-cli", "Wwise environment not found", "Failed to generate .wem", "Failed to decode", "transcode", "Exception during audio processing"],
    category: "AUDIO",
    title: "Wwise Transcoding Failure",
    friendlyMsg: "I couldn't transcode or compile the custom audio override qwq! Make sure vgmstream-cli.exe and Wwise are installed in your 'deps/' folders, and the source audio file isn't corrupted.",
    remediations: SETTINGS
  },

  // ---------------- COOK & PACK ----------------
  {
    match: ["No files found to pack", "Cook process might have failed"],
    category: "COOK_PACK",
    title: "Packaging Failed",
    friendlyMsg: "Unreal Engine finished cooking, but no .uasset files were found in the cooked directory for this character or variant to pack into the .pak archive.\n\nScroll up in the Build Console for the cook errors. The most common cause is that the mod was never pushed to Unreal.",
    remediations: DISMISS
  },
  {
    match: ["Cannot overwrite", "Cannot remove redundant variant pak", "File lock detected", "Close the game"],
    category: "COOK_PACK",
    title: "Pak File Locked",
    friendlyMsg: "Eeeek! The .pak file is locked, almost always because Palworld is still running. Please make sure Palworld is completely closed, and try again!",
    remediations: [{ label: "🛑 Force Close Palworld", actionKey: "close_game", style: "danger" }, ...SETTINGS]
  },
  {
    match: ["COOK FAILED", "Pipeline action cook failed", "Pipeline action cook-only failed", "Pipeline action pack failed", "Pipeline action pack-only failed"],
    category: "COOK_PACK",
    title: "Cook Process Failed",
    friendlyMsg: "The Unreal Cooker failed to process your assets! Review the red error lines in the Build Console to see exactly which file caused the crash.",
    remediations: DISMISS
  },
]

interface MissingTexture {
  material: string
  parameter: string
  texture: string
  game_path: string
}

/**
 * Builds placement instructions from the "[PalBaker Missing Textures] {...}" report printed by
 * unreal_scripts/materials.py (build_mod.py adds the mod folder the PNGs belong in).
 */
function parseMissingTextures(err: string): DiagnosticReport | null {
  const match = err.match(/\[PalBaker Missing Textures\]\s*(\{.*\})/)
  if (!match) return null

  let report: { textures?: MissingTexture[]; folder?: string }
  try {
    report = JSON.parse(match[1])
  } catch {
    return null
  }
  const textures = report.textures ?? []
  if (textures.length === 0) return null

  const folder = report.folder
  const vanilla = textures.filter(t => t.game_path.startsWith("/Game/"))
  const custom = textures.filter(t => !t.game_path.startsWith("/Game/"))

  let msg = "Unreal couldn't build your materials because these textures are missing from your mod folder and from the Unreal project:\n"
  for (const t of textures) {
    msg += `\n• ${t.texture}.png  (parameter '${t.parameter}' on ${t.material})`
  }

  msg += "\n\nHow to fix it:\n"
  let step = 1
  if (vanilla.length > 0) {
    msg += `\n${step++}. These come from the base game. In FModel, open each path below and export it as PNG (right-click → Save Texture):`
    for (const t of vanilla) {
      msg += `\n     Pal/Content/${t.game_path.slice("/Game/".length)}`
    }
    msg += "\n   FModel saves it next to the base Pal's files, not inside your mod folder, so you'll need to move it."
  }
  if (custom.length > 0) {
    msg += `\n${step++}. ${custom.map(t => t.texture).join(", ")} ${custom.length === 1 ? "isn't" : "aren't"} a base game texture. Your .blend material references ${custom.length === 1 ? "it" : "them"}, so you have to supply the PNG yourself (or remove the texture from that material in Blender).`
  }
  msg += `\n${step++}. Put the PNG files in your mod folder${folder ? " (shown below)" : ", next to your .blend file"}. Keep the exact file names, e.g. ${textures[0].texture}.png.`
  msg += `\n${step}. Run the action again.`

  return {
    category: "MATERIALS",
    title: textures.length === 1 ? "Missing Texture" : `Missing Textures (${textures.length})`,
    friendlyMsg: msg,
    folder,
    remediations: DISMISS
  }
}

/** Cooker errors that name a specific broken asset ([AssetLog] / LogBlueprint / [Compiler]). */
function parseAssetCompileError(err: string): DiagnosticReport | null {
  if (!(
    err.includes("[AssetLog]") ||
    err.includes("LogBlueprint: Error") ||
    (err.includes(".uasset") && err.includes("[Compiler]")) ||
    err.includes("unknown Anim Sequence Base")
  )) {
    return null
  }

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
    remediations: DISMISS
  };
}

export function parseBackendError(rawError: string): DiagnosticReport {
  const err = extractCoreMessage(String(rawError).trim());
  const detail = toDetail(err);

  // 1. MATERIAL TEXTURE DEPENDENCIES
  const textureReport = parseMissingTextures(err)
  if (textureReport) {
    return textureReport
  }

  // 2. PHYSICAL MEMORY (RAM) LIMIT EXHAUSTION: forward the backend's exact numbers
  if (err.includes("Low Physical Memory") || err.includes("free RAM is available") || err.includes("Win32 memory limits")) {
    const memLine = err.split(/[\r\n]+/).find(l => l.includes("Low Physical Memory") || l.includes("free RAM is available"))
    return {
      category: "COOK_PACK",
      title: "Low System Memory Warning",
      friendlyMsg: (memLine ? memLine.replace(/^ERROR:\s*/, "").trim() : err) + "\n\nCooking needs that much free RAM. Close other heavy programs (a second Unreal Editor, Blender, the game, browsers) and try again.",
      remediations: DISMISS
    };
  }

  // 3. SPECIFIC UNREAL COMPILATION & ASSET FAILURES
  const assetReport = parseAssetCompileError(err)
  if (assetReport) {
    return assetReport
  }

  const diagnosis = parseLogDiagnosis(err)

  // 4. KNOWN BACKEND ERRORS
  for (const rule of RULES) {
    if (matchesAny(err, rule.match)) {
      let friendlyMsg = typeof rule.friendlyMsg === "function" ? rule.friendlyMsg(err) : rule.friendlyMsg
      // The cook failure rule can't say which asset broke; the log scan often can
      if (rule.title === "Cook Process Failed" && diagnosis.length > 0) {
        friendlyMsg += `\n\nPalBaker spotted this in the build log:\n\n${formatDiagnosis(diagnosis)}`
      }
      return {
        category: rule.category,
        title: rule.title,
        friendlyMsg,
        detail,
        remediations: rule.remediations ?? DISMISS
      }
    }
  }

  // 5. SIGNATURES FOUND IN THE FULL BUILD LOG
  if (diagnosis.length > 0) {
    return {
      category: "GENERAL_ERROR",
      title: diagnosis.length === 1 ? diagnosis[0].title : "Build Failed",
      friendlyMsg: diagnosis.length === 1
        ? `${diagnosis[0].solution}${diagnosis[0].assets?.length ? `\n\nAffected: ${diagnosis[0].assets.join(", ")}` : ""}`
        : `PalBaker found ${diagnosis.length} known problems in the build log:\n\n${formatDiagnosis(diagnosis)}`,
      detail,
      remediations: DISMISS
    }
  }

  // GENERAL DEFAULT FALLBACK: say what the backend said instead of a generic shrug
  return {
    category: "GENERAL_ERROR",
    title: "Backend Execution Error",
    friendlyMsg: detail
      ? "PalBaker stopped with an error it doesn't have a specific explanation for yet. This is what the backend reported. The Build Console has the full log."
      : "Oopsies! The palbaker-cli returned an unexpected error qwq. Review the full technical logs in the Build Console to see what happened!",
    detail,
    remediations: DISMISS
  };
}

// Mock data derived from pythoncli/cli_queries_dump.json
// These will later be replaced by real Python CLI calls via the IPC bridge.

export const mockConfig = {
  fmodel_output: "H:\\SteamLibrary\\steamapps\\common\\Palworld\\Output",
  palworld_exe: "H:\\SteamLibrary\\steamapps\\common\\Palworld\\Palworld.exe",
  workspace:
    "H:\\SteamLibrary\\steamapps\\common\\Palworld\\Output\\Exports\\Pal\\Content\\Pal\\Model\\Character\\Pending Monster\\BlueberryFairy",
  uproject_path: "C:\\GameDev\\PalProject\\PalWorld.uproject",
  blender_exe: "C:\\Program Files\\Blender Foundation\\Blender 3.6\\blender.exe",
  ue_root: "C:\\Program Files\\Epic Games\\UE_5.1",
}

export type ModStatus = "OUT_OF_SYNC" | "IDLE" | "READY" | "SUCCESS" | "ERROR"

export interface SoundEntry {
  media_id: number
  wav_name: string
  wem_relative_path: string
  override?: string
}

export interface ModItem {
  id: string
  name: string
  localized_name: string
  status: ModStatus
  modified: string
  source_ext: string
  sound_metadata: Partial<Record<string, SoundEntry>>
  has_icon: boolean
}

export const mockModList: ModItem[] = [
  {
    id: "anubis_model_v4",
    name: "Anubis_Model_v4",
    localized_name: "Anubis Model v4",
    status: "OUT_OF_SYNC",
    modified: "2m ago",
    source_ext: ".fbx",
    sound_metadata: {
      Normal: { media_id: 0, wav_name: "VO_Anubis_01_Normal.wav", wem_relative_path: "Pal/Content/WwiseAudio/Media/0.wem" },
      Joy: { media_id: 111, wav_name: "VO_Anubis_02_Joy.wav", wem_relative_path: "Pal/Content/WwiseAudio/Media/111.wem", override: "Custom Override" },
      Anger: { media_id: 222, wav_name: "VO_Anubis_03_Anger.wav", wem_relative_path: "Pal/Content/WwiseAudio/Media/222.wem" },
      Sorrow: { media_id: 333, wav_name: "VO_Anubis_04_Sorrow.wav", wem_relative_path: "Pal/Content/WwiseAudio/Media/333.wem" },
      Pain: { media_id: 444, wav_name: "VO_Anubis_05_Pain.wav", wem_relative_path: "Pal/Content/WwiseAudio/Media/444.wem" },
      Death: { media_id: 555, wav_name: "VO_Anubis_06_Death.wav", wem_relative_path: "Pal/Content/WwiseAudio/Media/555.wem" },
    },
    has_icon: true,
  },
  {
    id: "depresso_depressed_v2",
    name: "Depresso_Depressed_V2",
    localized_name: "Depresso Depressed V2",
    status: "IDLE",
    modified: "10m ago",
    source_ext: ".fbx",
    sound_metadata: {},
    has_icon: false,
  },
  {
    id: "lamball_armor_set",
    name: "Lamball_Armor_Set",
    localized_name: "Lamball Armor Set",
    status: "READY",
    modified: "1h ago",
    source_ext: ".blend",
    sound_metadata: {},
    has_icon: false,
  },
  {
    id: "jetragon_supersonic_v1",
    name: "Jetragon_Supersonic_V1",
    localized_name: "Jetragon Supersonic V1",
    status: "SUCCESS",
    modified: "3h ago",
    source_ext: ".uasset",
    sound_metadata: {},
    has_icon: false,
  },
  {
    id: "chillet_ice_reskin",
    name: "Chillet_Ice_Reskin",
    localized_name: "Chillet Ice Reskin",
    status: "OUT_OF_SYNC",
    modified: "5h ago",
    source_ext: ".blend",
    sound_metadata: {},
    has_icon: false,
  },
]

export interface LearnsetEntry {
  Level: number
  WazaID: string
}

export interface ActiveSkill {
  id: string
  element: string
  category: string
}

export const mockActiveSkills: Record<string, ActiveSkill> = {
  TidalWave: { id: "TidalWave", element: "Water", category: "Shot" },
  Unique_MoonQueen_MoonBlade: { id: "Unique_MoonQueen_MoonBlade", element: "Normal", category: "Shot" },
  AirCanon: { id: "AirCanon", element: "Normal", category: "Shot" },
  StoneShotgun: { id: "StoneShotgun", element: "Ground", category: "Shot" },
  RockLance: { id: "RockLance", element: "Ground", category: "Shot" },
  MudShot: { id: "MudShot", element: "Ground", category: "Shot" },
  DragonMeteor: { id: "DragonMeteor", element: "Dragon", category: "Shot" },
  PowerShot: { id: "PowerShot", element: "Normal", category: "Shot" },
  HyperBeam: { id: "HyperBeam", element: "Normal", category: "Beam" },
  RadiantBarrage: { id: "RadiantBarrage", element: "Normal", category: "Shot" },
  SandBlast: { id: "SandBlast", element: "Ground", category: "Shot" },
  StoneBlast: { id: "StoneBlast", element: "Ground", category: "Shot" },
  SandTornado: { id: "SandTornado", element: "Ground", category: "Charge" },
}

export const mockLearnsets: Record<string, LearnsetEntry[]> = {
  Anubis: [
    { Level: 1, WazaID: "StoneShotgun" },
    { Level: 22, WazaID: "Unique_Anubis_LowRoundKick" },
    { Level: 50, WazaID: "RockLance" },
  ],
  Chillet: [
    { Level: 1, WazaID: "AirCanon" },
    { Level: 15, WazaID: "TidalWave" },
    { Level: 40, WazaID: "DragonMeteor" },
  ],
  Furret: [
    { Level: 1, WazaID: "AirCanon" },
    { Level: 22, WazaID: "Unique_PinkCat_CatPunch" },
    { Level: 50, WazaID: "DragonMeteor" },
  ],
}

export const mockPalTemplates = ["Anubis", "Chillet", "Furret", "IceDeer", "Yeti", "Lamball", "Foxparks", "Cattiva"]

export interface WorkSuitability {
  Kindling: boolean
  Planting: boolean
  Handiwork: boolean
  Watering: boolean
  Gathering: boolean
  Lumbering: boolean
  Mining: boolean
  Medicine: boolean
}

export interface CreatorPal {
  CharacterID: string
  palId: string
  speciesName: string
  elementTypes: string[]
  hp: number
  attack: number
  defense: number
  workSpeed: number
  workSuitabilities: WorkSuitability
  Learnset: LearnsetEntry[]
  spawnX: number
  spawnY: number
  levelMin: number
  levelMax: number
  groupSize: number
  parentTemplate: string
}

export const mockCreatorPals: CreatorPal[] = [
  {
    CharacterID: "Furret",
    palId: "001-B",
    speciesName: "Anubis Prime",
    elementTypes: ["Ground"],
    hp: 120,
    attack: 85,
    defense: 70,
    workSpeed: 150,
    workSuitabilities: {
      Kindling: true,
      Planting: false,
      Handiwork: true,
      Watering: false,
      Gathering: false,
      Lumbering: true,
      Mining: true,
      Medicine: false,
    },
    Learnset: [
      { Level: 1, WazaID: "SandBlast" },
      { Level: 7, WazaID: "PowerShot" },
      { Level: 15, WazaID: "StoneBlast" },
      { Level: 30, WazaID: "SandTornado" },
    ],
    spawnX: 240,
    spawnY: -120,
    levelMin: 15,
    levelMax: 25,
    groupSize: 3,
    parentTemplate: "Anubis",
  },
]

export const mockEnvStatus = {
  palschema: { status: "Installed" as const },
  remote_exec_enabled: true,
  ue4ss: { version: "v2.5.2", status: "INSTALLED_ACTIVE" as const },
  palschema_plugin: { version: "v0.2.1.0", status: "UPDATE_AVAILABLE" as const },
  pipeline: {
    blender_rpc: "CONNECTED" as const,
    ue_live_link: "STANDBY" as const,
    asset_watcher: "RUNNING" as const,
    build_queue: "IDLE" as const,
  },
}

export const ELEMENT_COLORS: Record<string, string> = {
  Ground:  "bg-amber-700 text-amber-100",
  Water:   "bg-blue-600 text-blue-100",
  Fire:    "bg-orange-600 text-orange-100",
  Grass:   "bg-green-700 text-green-100",
  Ice:     "bg-cyan-600 text-cyan-100",
  Electric:"bg-yellow-500 text-yellow-950",
  Dark:    "bg-purple-700 text-purple-100",
  Dragon:  "bg-violet-700 text-violet-100",
  Normal:  "bg-zinc-600 text-zinc-100",
}

export const CONSOLE_LOGS = [
  { time: "14:32:01", level: "SUCCESS" as const, msg: 'Validation complete. Species "Anubis Prime" contains 4 active moves.' },
  { time: "14:31:55", level: "INFO" as const, msg: "Learnset matrix resolved. 4 entries mapped." },
  { time: "14:22:04", level: "SUCCESS" as const, msg: "System Environment Validated." },
  { time: "14:22:05", level: "INFO" as const, msg: "12 mods indexed from workspace." },
  { time: "09:41:22", level: "SUCCESS" as const, msg: "Package 'Anubis_Model_v4' linked to Unreal Engine 5.3 project." },
]

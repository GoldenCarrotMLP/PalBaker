// Mock data derived from pythoncli/cli_queries_dump.json and pythoncli/components/mods/mod_card.py
// Replace these with real CLI bridge calls once the Python server is wired up.

// ── Config ─────────────────────────────────────────────────────────────────────
export const mockConfig = {
  workspace:      "H:\\SteamLibrary\\steamapps\\common\\Palworld\\Output\\Exports\\Pal\\Content\\Pal\\Model\\Character\\Pending Monster",
  ue_root:        "C:\\Program Files\\Epic Games\\UE_5.1",
  uproject_path:  "C:\\GameDev\\PalProject\\PalWorld.uproject",
  blender_exe:    "C:\\Program Files\\Blender Foundation\\Blender 3.6\\blender.exe",
  palworld_exe:   "H:\\SteamLibrary\\steamapps\\common\\Palworld\\Palworld.exe",
  fmodel_output:  "H:\\SteamLibrary\\steamapps\\common\\Palworld\\Output",
}

// ── Spawner cache (from pythoncli/deps/monster_spawners_cache.json) ────────────
export const mockSpawnerCache: Record<string, string> = {
  "11_1_testarea_1 (Cattiva, Chikipi, Foxparks, Hoocrates)": "11_1_testarea_1",
  "1_10_plain_F_Boss_Anubis (Boss_Anubis)": "1_10_plain_F_Boss_Anubis",
  "1_10_plain_F_Boss_BlueDragon (BOSS_BlueDragon)": "1_10_plain_F_Boss_BlueDragon",
  "2_2_forestsnow_1 (Chillet, Foxcicle, Kitsun, Mimog)": "2_2_forestsnow_1",
  "3_1_volcano_1 (Blazehowl Noct, Flambelle, Kelpsea Ignis, Mimog)": "3_1_volcano_1",
  "4_1_dessert_1 (Cawgnito, Dazzi, Dinossom Lux, Leezpunk)": "4_1_dessert_1",
}

// ── Pak status mirrors mod_card.py ModItem badge logic ─────────────────────────
export type PakStatus =
  | "Unextracted"    // has_fmodel=false — red EXTRACT PAL
  | "Unpacked"       // has_fmodel=true, has_blend=false — grey CREATE .BLEND FILE
  | "Outdated"       // has_blend=true, has_ue=false — cyan PUSH TO UNREAL
  | "Packed"         // has_ue=true, source_modified=false — green COOK & PACK
  | "SrcChanged"     // has_ue=true, source_modified=true  — orange FULL PIPELINE

export interface SoundEntry {
  media_id: number
  wav_name: string
  wem_relative_path: string
}

export interface AltermaticVariant {
  label: string
  is_base: boolean
  SkeletonSource?: string
  Gender: string        // "None" | "Male" | "Female"
  IsRarePal: boolean
  SkinName?: string
  ReqTrait: string[]
  PrefTrait: string[]
  MatReplace: any[]
  MorphTarget: any[]
}

export interface ModBadge {
  text: string
  color: string   // Tailwind bg class
  tooltip: string
}

export interface ModItem {
  id: string
  name: string
  localized_name: string
  pak_status: PakStatus
  modified: string
  source_ext: string
  // flags that drive button logic (mirrors mod_card.py)
  has_fmodel: boolean
  has_blend: boolean
  has_ue: boolean
  source_modified: boolean
  ue_modified?: boolean
  has_icon: boolean
  icon_path: string
  badges: ModBadge[]
  sound_metadata: Partial<Record<string, SoundEntry>>
  audio_overrides: Partial<Record<string, string>>   // cryName → file path
  is_altermatic_active: boolean
  altermatic_variants: AltermaticVariant[]
}

export const mockModList: ModItem[] = [
  {
    id: "anubis_model_v4",
    name: "Anubis_Model_v4",
    localized_name: "Anubis Model v4",
    pak_status: "SrcChanged",
    modified: "2m ago",
    source_ext: ".fbx",
    has_fmodel: true,
    has_blend: true,
    has_ue: true,
    source_modified: true,
    has_icon: true,
    icon_path: "",
    badges: [
      { text: ".blend Changed", color: "bg-status-warning/20 text-status-warning border-status-warning/50", tooltip: "Source files have been edited since your last Push. Run 'Push & Cook & Pack'." },
      { text: "ALTERMATIC", color: "bg-primary/15 text-primary border-primary/40", tooltip: "Altermatic dynamic variants are active for this Pal." },
    ],
    sound_metadata: {
      Normal: { media_id: 100000001, wav_name: "VO_Anubis_01_Normal.wav", wem_relative_path: "Pal/Content/WwiseAudio/Media/100000001.wem" },
      Joy:    { media_id: 100000002, wav_name: "VO_Anubis_02_Joy.wav",    wem_relative_path: "Pal/Content/WwiseAudio/Media/100000002.wem" },
      Anger:  { media_id: 100000003, wav_name: "VO_Anubis_03_Anger.wav",  wem_relative_path: "Pal/Content/WwiseAudio/Media/100000003.wem" },
      Sorrow: { media_id: 100000004, wav_name: "VO_Anubis_04_Sorrow.wav", wem_relative_path: "Pal/Content/WwiseAudio/Media/100000004.wem" },
      Pain:   { media_id: 100000005, wav_name: "VO_Anubis_05_Pain.wav",   wem_relative_path: "Pal/Content/WwiseAudio/Media/100000005.wem" },
      Death:  { media_id: 100000006, wav_name: "VO_Anubis_06_Death.wav",  wem_relative_path: "Pal/Content/WwiseAudio/Media/100000006.wem" },
    },
    audio_overrides: { Joy: "custom_joy_override.wav" },
    is_altermatic_active: true,
    altermatic_variants: [
      { label: "Anubis_base",   is_base: true,  Gender: "None",   IsRarePal: false, ReqTrait: ["HP_ACC_up1", "OctaviaArmorVampire", "ElementAddDrop_Aqua_2_PAL"], PrefTrait: [], MatReplace: ["MI_Body_v1"], MorphTarget: [] },
      { label: "Anubis_Bikini", is_base: false, Gender: "Female", IsRarePal: true,  ReqTrait: [], PrefTrait: [], MatReplace: [], MorphTarget: ["Bikini_Morph", "SizeUp_Morph", "HipTilt_Morph", "Slim_Morph"] },
      { label: "Anubis_NSFW",   is_base: false, Gender: "Female", IsRarePal: false, ReqTrait: ["HP_ACC_up1"], PrefTrait: [], MatReplace: [], MorphTarget: [] },
    ],
  },
  {
    id: "depresso_depressed_v2",
    name: "Depresso_Depressed_V2",
    localized_name: "Depresso Depressed V2",
    pak_status: "Unpacked",
    modified: "10m ago",
    source_ext: ".fbx",
    has_fmodel: true,
    has_blend: false,
    has_ue: false,
    source_modified: false,
    has_icon: false,
    icon_path: "",
    badges: [
      { text: "RAW", color: "bg-muted text-muted-foreground border-border", tooltip: "FModel files extracted, but no Blender (.blend) file has been created yet." },
    ],
    sound_metadata: {},
    audio_overrides: {},
    is_altermatic_active: false,
    altermatic_variants: [],
  },
  {
    id: "lamball_armor_set",
    name: "Lamball_Armor_Set",
    localized_name: "Lamball Armor Set",
    pak_status: "Outdated",
    modified: "1h ago",
    source_ext: ".blend",
    has_fmodel: true,
    has_blend: true,
    has_ue: false,
    source_modified: false,
    has_icon: false,
    icon_path: "",
    badges: [
      { text: ".blend", color: "bg-primary/10 text-primary border-primary/30", tooltip: "Blender (.blend) source file detected. Mod is actively being worked on." },
    ],
    sound_metadata: {},
    audio_overrides: {},
    is_altermatic_active: false,
    altermatic_variants: [],
  },
  {
    id: "jetragon_supersonic_v1",
    name: "Jetragon_Supersonic_V1",
    localized_name: "Jetragon Supersonic V1",
    pak_status: "Packed",
    modified: "3h ago",
    source_ext: ".uasset",
    has_fmodel: true,
    has_blend: true,
    has_ue: true,
    source_modified: false,
    has_icon: false,
    icon_path: "",
    badges: [
      { text: "UE ASSETS", color: "bg-status-success/10 text-status-success border-status-success/30", tooltip: "Files are compiled in Unreal Engine." },
    ],
    sound_metadata: {
      Normal: { media_id: 200000001, wav_name: "VO_Jetragon_01_Normal.wav", wem_relative_path: "Pal/Content/WwiseAudio/Media/200000001.wem" },
      Pain:   { media_id: 200000002, wav_name: "VO_Jetragon_05_Pain.wav",   wem_relative_path: "Pal/Content/WwiseAudio/Media/200000002.wem" },
      Death:  { media_id: 200000003, wav_name: "VO_Jetragon_06_Death.wav",  wem_relative_path: "Pal/Content/WwiseAudio/Media/200000003.wem" },
    },
    audio_overrides: {},
    is_altermatic_active: false,
    altermatic_variants: [],
  },
  {
    id: "chillet_ice_reskin",
    name: "Chillet_Ice_Reskin",
    localized_name: "Chillet Ice Reskin",
    pak_status: "SrcChanged",
    modified: "5h ago",
    source_ext: ".blend",
    has_fmodel: true,
    has_blend: true,
    has_ue: true,
    source_modified: true,
    has_icon: false,
    icon_path: "",
    badges: [
      { text: ".blend Changed", color: "bg-status-warning/20 text-status-warning border-status-warning/50", tooltip: "Source files have been edited since your last Push. Run 'Push & Cook & Pack'." },
      { text: "MODIFIED", color: "bg-status-warning/15 text-status-warning border-status-warning/40", tooltip: "Files have been manually modified inside Unreal Engine since your last Push." },
    ],
    sound_metadata: {},
    audio_overrides: {},
    is_altermatic_active: false,
    altermatic_variants: [],
  },
]

// ── Active Skills (enriched from manager_get_caches) ──────────────────────────
export interface ActiveSkill {
  id: string
  element: string
  category: string
  power: number
}

export const mockActiveSkills: Record<string, ActiveSkill> = {
  TidalWave:                              { id: "TidalWave",                              element: "Water",   category: "Shot",   power: 120 },
  Unique_MoonQueen_MoonBlade:             { id: "Unique_MoonQueen_MoonBlade",             element: "Normal",  category: "Shot",   power: 90  },
  Unique_LegendDeer_RadiantPurge_Otomo:   { id: "Unique_LegendDeer_RadiantPurge_Otomo",   element: "Normal",  category: "Shot",   power: 150 },
  AirCanon:                               { id: "AirCanon",                               element: "Normal",  category: "Shot",   power: 25  },
  StoneShotgun:                           { id: "StoneShotgun",                           element: "Ground",  category: "Shot",   power: 55  },
  Unique_Anubis_LowRoundKick:             { id: "Unique_Anubis_LowRoundKick",             element: "Ground",  category: "Melee",  power: 130 },
  RockLance:                              { id: "RockLance",                              element: "Ground",  category: "Shot",   power: 150 },
  MudShot:                                { id: "MudShot",                                element: "Ground",  category: "Shot",   power: 30  },
  Unique_KingAlpaca_BodyPress:            { id: "Unique_KingAlpaca_BodyPress",            element: "Normal",  category: "Melee",  power: 120 },
  HyperBeam:                              { id: "HyperBeam",                              element: "Normal",  category: "Beam",   power: 150 },
  PowerShot:                              { id: "PowerShot",                              element: "Normal",  category: "Shot",   power: 35  },
  RadiantBarrage:                         { id: "RadiantBarrage",                         element: "Normal",  category: "Shot",   power: 80  },
  Unique_PinkCat_CatPunch:                { id: "Unique_PinkCat_CatPunch",                element: "Normal",  category: "Melee",  power: 70  },
  DragonMeteor:                           { id: "DragonMeteor",                           element: "Dragon",  category: "Shot",   power: 150 },
  SandBlast:                              { id: "SandBlast",                              element: "Ground",  category: "Shot",   power: 40  },
  StoneBlast:                             { id: "StoneBlast",                             element: "Ground",  category: "Shot",   power: 55  },
  SandTornado:                            { id: "SandTornado",                            element: "Ground",  category: "Charge", power: 80  },
  IceMissile:                             { id: "IceMissile",                             element: "Ice",     category: "Shot",   power: 30  },
  BlizzardSpike:                          { id: "BlizzardSpike",                          element: "Ice",     category: "Shot",   power: 130 },
  FireBall:                               { id: "FireBall",                               element: "Fire",    category: "Shot",   power: 45  },
  FlameHowl:                              { id: "FlameHowl",                              element: "Fire",    category: "Shot",   power: 110 },
  ThunderBolt:                            { id: "ThunderBolt",                            element: "Electric",category: "Shot",   power: 40  },
  LightningStrike:                        { id: "LightningStrike",                        element: "Electric",category: "Shot",   power: 120 },
  WaterGun:                               { id: "WaterGun",                               element: "Water",   category: "Shot",   power: 30  },
  BubbleBlast:                            { id: "BubbleBlast",                            element: "Water",   category: "Shot",   power: 65  },
  LeafTornado:                            { id: "LeafTornado",                            element: "Grass",   category: "Shot",   power: 65  },
  SeedMachine:                            { id: "SeedMachine",                            element: "Grass",   category: "Shot",   power: 50  },
}

export interface LearnsetEntry {
  Level: number
  WazaID: string
}

export const mockLearnsets: Record<string, LearnsetEntry[]> = {
  Anubis: [
    { Level: 1,  WazaID: "StoneShotgun" },
    { Level: 22, WazaID: "Unique_Anubis_LowRoundKick" },
    { Level: 50, WazaID: "RockLance" },
  ],
  BOSS_KingAlpaca: [
    { Level: 1,  WazaID: "MudShot" },
    { Level: 22, WazaID: "Unique_KingAlpaca_BodyPress" },
    { Level: 50, WazaID: "HyperBeam" },
  ],
  Chillet: [
    { Level: 1,  WazaID: "AirCanon" },
    { Level: 15, WazaID: "TidalWave" },
    { Level: 40, WazaID: "DragonMeteor" },
  ],
  Furret: [
    { Level: 1,  WazaID: "AirCanon" },
    { Level: 22, WazaID: "Unique_PinkCat_CatPunch" },
    { Level: 50, WazaID: "DragonMeteor" },
  ],
}

export const mockPalTemplates = [
  "Anubis", "Chillet", "Furret", "IceDeer", "Yeti", "Lamball",
  "Foxparks", "Cattiva", "WeaselDragon", "BOSS_KingAlpaca", "BOSS_LegendDeer",
]

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
  TemplateID: string
  Name: string
  Description: string
  ElementType1: string
  ElementType2: string
  BaseHP: number
  BaseAtk: number
  BaseDef: number
  BaseWorkSpeed: number
  WorkSuitabilities: Record<string, number>
  Learnset: LearnsetEntry[]
  SpawnLocationID?: string
  SpawnMinLevel?: number
  SpawnMaxLevel?: number
  SpawnMinGroup?: number
  SpawnMaxGroup?: number
  ZukanIndex?: number
  ZukanIndexSuffix?: string
  resolved_icon_path?: string
  // Legacy fields for mock fallback compatibility
  palId?: string
  speciesName?: string
  parentTemplate?: string
}

// Alias for data-service.ts
export type CreatorItem = CreatorPal
export type EnvStatusType = typeof mockEnvStatus

export const mockCreatorPals: CreatorPal[] = [
  {
    CharacterID: "Furret",
    TemplateID: "WeaselDragon",
    Name: "Furret",
    Description: "A custom standalone Pal cloned from WeaselDragon.",
    ElementType1: "EPalElementType::Normal",
    ElementType2: "EPalElementType::None",
    BaseHP: 100,
    BaseAtk: 100,
    BaseDef: 80,
    BaseWorkSpeed: 70,
    WorkSuitabilities: {
      WorkSuitability_EmitFlame: 0,
      WorkSuitability_Watering: 0,
      WorkSuitability_Seeding: 0,
      WorkSuitability_GenerateElectricity: 0,
      WorkSuitability_Handcraft: 0,
      WorkSuitability_Collection: 1,
      WorkSuitability_Deforest: 0,
      WorkSuitability_Mining: 0,
      WorkSuitability_OilExtraction: 0,
      WorkSuitability_ProductMedicine: 0,
      WorkSuitability_Cool: 1,
      WorkSuitability_Transport: 0,
      WorkSuitability_MonsterFarm: 0,
    },
    Learnset: [
      { Level: 1,  WazaID: "AirCanon" },
      { Level: 7,  WazaID: "AirCanon" },
      { Level: 15, WazaID: "DragonWave" },
    ],
    SpawnLocationID: "1_1_plain_begginer",
    SpawnMinLevel: 2,
    SpawnMaxLevel: 5,
    SpawnMinGroup: 1,
    SpawnMaxGroup: 3,
    ZukanIndex: 55,
    ZukanIndexSuffix: "C",
  },
]

// ── Passive traits (from manager_get_caches.traits_db) ──────────────────────────
export const mockTraitsDb: Record<string, string> = {
  "Health Up Lv. 1":           "HP_ACC_up1",
  "Blood Is Fuel":              "OctaviaArmorVampire",
  "Aqua Element Drop+2":        "ElementAddDrop_Aqua_2_PAL",
  "Attack Up Lv. 1":            "ATK_ACC_up1",
  "Defense Up Lv. 1":           "DEF_ACC_up1",
  "Swift":                      "MoveSpeed_up_PAL",
  "Conceited":                  "Bossy_PAL",
}

// ── Env status ─────────────────────────────────────────────────────────────────
export const mockEnvStatus = {
  palschema:         { status: "Installed" as const },
  remote_exec_enabled: true,
  ue4ss:             { version: "v2.5.2", status: "INSTALLED_ACTIVE" as const },
  palschema_plugin:  { version: "v0.2.1.0", status: "UPDATE_AVAILABLE" as const },
  pipeline: {
    blender_rpc:  "CONNECTED"  as const,
    ue_live_link: "STANDBY"    as const,
    asset_watcher:"RUNNING"    as const,
    build_queue:  "IDLE"       as const,
  },
}

// ── Element color palette ───────────────────────────────────────────────────────
export const ELEMENT_COLORS: Record<string, string> = {
  Ground:   "bg-amber-700  text-amber-100",
  Water:    "bg-blue-600   text-blue-100",
  Fire:     "bg-orange-600 text-orange-100",
  Grass:    "bg-green-700  text-green-100",
  Ice:      "bg-cyan-600   text-cyan-100",
  Electric: "bg-yellow-500 text-yellow-950",
  Dark:     "bg-purple-700 text-purple-100",
  Dragon:   "bg-violet-700 text-violet-100",
  Normal:   "bg-zinc-600   text-zinc-100",
}

// ── Build console logs ──────────────────────────────────────────────────────────
export type LogLevel = "SUCCESS" | "INFO" | "ERROR" | "WARNING"

export interface LogEntry {
  time: string
  level: LogLevel
  msg: string
}

export const CONSOLE_LOGS: LogEntry[] = [
  { time: "14:32:01", level: "SUCCESS", msg: 'Validation complete. Species "Anubis Prime" contains 4 active moves.' },
  { time: "14:31:55", level: "INFO",    msg: "Learnset matrix resolved. 4 entries mapped." },
  { time: "14:22:05", level: "INFO",    msg: "12 mods indexed from workspace." },
  { time: "14:22:04", level: "SUCCESS", msg: "System Environment Validated." },
  { time: "09:41:22", level: "SUCCESS", msg: "Package 'Anubis_Model_v4' linked to Unreal Engine 5.3 project." },
]

// ── Creator list (mock) ──────────────────────────────────────────────────────────
export const mockCreatorList: CreatorItem[] = [
  {
    CharacterID: "Anubis_Prime",
    TemplateID: "Anubis",
    Name: "Anubis Prime",
    Description: "An upgraded, standalone form of Anubis specialized in fire and combat maneuvers.",
    ElementType1: "EPalElementType::Earth",
    ElementType2: "EPalElementType::Fire",
    BaseHP: 100,
    BaseAtk: 85,
    BaseDef: 75,
    BaseWorkSpeed: 150,
    WorkSuitabilities: {
      WorkSuitability_EmitFlame: 1,
      WorkSuitability_Watering: 0,
      WorkSuitability_Seeding: 0,
      WorkSuitability_GenerateElectricity: 0,
      WorkSuitability_Handcraft: 1,
      WorkSuitability_Collection: 0,
      WorkSuitability_Deforest: 1,
      WorkSuitability_Mining: 1,
      WorkSuitability_OilExtraction: 0,
      WorkSuitability_ProductMedicine: 0,
      WorkSuitability_Cool: 0,
      WorkSuitability_Transport: 0,
      WorkSuitability_MonsterFarm: 0,
    },
    Learnset: [
      { Level: 1, WazaID: "StoneShotgun" },
      { Level: 22, WazaID: "Unique_Anubis_LowRoundKick" },
      { Level: 50, WazaID: "RockLance" },
    ],
    SpawnLocationID: "1_1_plain_begginer",
    SpawnMinLevel: 15,
    SpawnMaxLevel: 25,
    SpawnMinGroup: 1,
    SpawnMaxGroup: 4,
    ZukanIndex: 1,
    ZukanIndexSuffix: "B",
  },
]


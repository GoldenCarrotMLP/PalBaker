// Mock data derived from palbaker-cli/cli_queries_dump.json and palbaker-cli/components/mods/mod_card.py

export const mockConfig = {
  workspace:      "",
  ue_root:        "",
  uproject_path:  "",
  blender_exe:    "",
  palworld_exe:   "",
  fmodel_output:  "",
}

export const mockSpawnerCache: Record<string, string> = {
  "11_1_testarea_1 (Cattiva, Chikipi, Foxparks, Hoocrates)": "11_1_testarea_1",
  "1_10_plain_F_Boss_Anubis (Boss_Anubis)": "1_10_plain_F_Boss_Anubis",
  "1_10_plain_F_Boss_BlueDragon (BOSS_BlueDragon)": "1_10_plain_F_Boss_BlueDragon",
  "2_2_forestsnow_1 (Chillet, Foxcicle, Kitsun, Mimog)": "2_2_forestsnow_1",
  "3_1_volcano_1 (Blazehowl Noct, Flambelle, Kelpsea Ignis, Mimog)": "3_1_volcano_1",
  "4_1_dessert_1 (Cawgnito, Dazzi, Dinossom Lux, Leezpunk)": "4_1_dessert_1",
}

export type PakStatus =
  | "Unextracted"    
  | "Unpacked"       
  | "Outdated"       
  | "Packed"         
  | "SrcChanged"     

export interface SoundEntry {
  media_id: number
  wav_name: string
  wem_relative_path: string
}

export interface AltermaticVariant {
  label: string
  is_base: boolean
  SkeletonSource?: string
  Gender: string        
  IsRarePal: boolean
  SkinName?: string
  ReqTrait: string[]
  PrefTrait: string[]
  MatReplace: any[]
  MorphTarget: any[]
}

export type ModBadge = [string, string]

export interface ModItem {
  id: string
  name: string
  localized_name: string
  pak_status: PakStatus
  modified: string
  source_ext: string
  has_fmodel: boolean
  has_blend: boolean
  has_ue: boolean
  source_modified: boolean
  ue_modified?: boolean
  has_icon: boolean
  icon_path: string
  badges: ModBadge[]
  sound_metadata: Partial<Record<string, SoundEntry>>
  audio_overrides: Partial<Record<string, string>>   
  is_altermatic_active: boolean
  altermatic_variants: AltermaticVariant[]
  preserve_materials: boolean 
}

export const mockModList: ModItem[] = []

export interface ActiveSkill {
  id: string
  element: string
  category: string
  power: number
}

export const mockActiveSkills: Record<string, ActiveSkill> = {
  AirCanon: { id: "AirCanon", element: "Normal", category: "Shot", power: 25 },
}

export interface LearnsetEntry {
  Level: number
  WazaID: string
}

export const mockLearnsets: Record<string, LearnsetEntry[]> = {}

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

// Strictly modeled 1:1 against DT_PalMonsterParameter to map directly into PalSchema
export interface CreatorPal {
  CharacterID: string
  TemplateID: string
  Name: string
  Description: string
  
  // Exact Palworld Keys
  ElementType1: string
  ElementType2: string
  Hp?: number
  MeleeAttack?: number
  ShotAttack?: number
  Defense?: number
  Support?: number
  CraftSpeed?: number
  Size?: string
  Rarity?: number
  Price?: number
  WalkSpeed?: number
  RunSpeed?: number
  RideSprintSpeed?: number
  TransportSpeed?: number
  FoodAmount?: number
  Stamina?: number
  MaleProbability?: number
  CombiRank?: number
  CaptureRateCorrect?: number

  // Core Collision Capsule Heights & Relative Mesh Translation Slices
  MeshCapsuleHalfHeight?: number
  MeshCapsuleRadius?: number
  MeshRelativeLocation?: {
    X: number
    Y: number
    Z: number
  }
  
  // Flat Native Palworld Suitabilities
  WorkSuitability_EmitFlame?: number
  WorkSuitability_Watering?: number
  WorkSuitability_Seeding?: number
  WorkSuitability_GenerateElectricity?: number
  WorkSuitability_Handcraft?: number
  WorkSuitability_Collection?: number
  WorkSuitability_Deforest?: number
  WorkSuitability_Mining?: number
  WorkSuitability_OilExtraction?: number
  WorkSuitability_ProductMedicine?: number
  WorkSuitability_Cool?: number
  WorkSuitability_Transport?: number
  WorkSuitability_MonsterFarm?: number
  
  BaseSkills?: string[]
  PassiveSkills?: string[]
  PartnerSkill?: string
  Learnset: LearnsetEntry[]
  SpawnLocationID?: string
  SpawnWeight?: number // <-- ADDED
  SpawnMinLevel?: number
  SpawnMaxLevel?: number
  SpawnMinGroup?: number
  SpawnMaxGroup?: number
  EnablePaldeck?: boolean
  ZukanIndex?: number
  ZukanIndexSuffix?: string
  PaldexType?: string
  LongDescription?: string

  resolved_icon_path?: string
  
  // Legacy Fallbacks
  BaseHP?: number
  BaseMelee?: number
  BaseAtk?: number
  BaseShot?: number
  BaseDef?: number
  BaseWorkSpeed?: number
  WorkSuitabilities?: Record<string, number>
}

export type CreatorItem = CreatorPal

export interface EnvStatusType {
  ue4ss?: {
    status: "Installed" | "Not Installed" | "Exe not found" | "INSTALLED_ACTIVE" | "STATUS UNKNOWN"
    branch?: string
    corrupted?: boolean
    version?: string
  }
  palschema?: {
    status: "Installed" | "Not Installed" | "STATUS UNKNOWN"
  }
  palschema_plugin?: {
    status: "Installed" | "Not Installed" | "UPDATE_AVAILABLE" | "STATUS UNKNOWN"
    version?: string
  }
  remote_exec_enabled?: boolean
  unreal_running?: boolean
  pipeline?: {
    blender_rpc: "CONNECTED" | "STANDBY" | "RUNNING" | "IDLE"
    ue_live_link: "CONNECTED" | "STANDBY" | "RUNNING" | "IDLE"
    asset_watcher: "CONNECTED" | "STANDBY" | "RUNNING" | "IDLE"
    build_queue: "CONNECTED" | "STANDBY" | "RUNNING" | "IDLE"
  }
}

export const mockCreatorPals: CreatorPal[] = []

export const mockTraitsDb: Record<string, string> = {}

export const mockEnvStatus: EnvStatusType = {
  palschema: { status: "Not Installed" },
  remote_exec_enabled: false,
}

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

export type LogLevel = "SUCCESS" | "INFO" | "ERROR" | "WARNING"

export interface LogEntry {
  time: string
  level: LogLevel
  msg: string
}

export const CONSOLE_LOGS: LogEntry[] = []

export const mockCreatorList: CreatorItem[] = []
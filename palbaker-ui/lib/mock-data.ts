// palbaker-ui/lib/mock-data.ts

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

export interface SpecialMaterialEntry {
  Index: string
  MaterialAsset: string
  RandomHue?: boolean
  SlotName?: string
}

export interface ShapeKeyEntry {
  Name: string
  Mode?: "Free" | "Restrictive" | string
  Min?: number
  Max?: number
  Set?: number
}

export interface DynamicPalVariant {
  label: string
  is_base: boolean
  SkeletonSource?: string
  Gender?: string
  SkinName?: string
  SetNickname?: string
  AnimTarget?: string

  // Range toggle activation flags
  enableLevelRange?: boolean
  enableTrustRange?: boolean
  enableRankRange?: boolean
  enableSizeRange?: boolean
  enableSpawnWeight?: boolean

  // Range values
  MinLevel?: number
  MaxLevel?: number
  MinTrust?: number
  MaxTrust?: number
  MinRank?: number
  MaxRank?: number
  MinSizeMultiplier?: number
  MaxSizeMultiplier?: number

  // Variant flags & attributes
  SpawnWeight?: number
  LuckyStarReq?: boolean
  IsWildPal?: boolean
  ReqSwap?: string[]
  PassiveSkills?: string[]
  PrefTrait?: string[]
  SkipTrait?: string[]
  SpecialMaterial?: SpecialMaterialEntry[]
  ShapeKeys?: ShapeKeyEntry[]
  Extra?: string
}

export type ModBadge = [string, string]

export interface ModItem {
  id: string
  name: string
  base_pal: string
  category: string
  is_variant: boolean
  localized_name: string
  pak_status: PakStatus
  modified: string
  source_ext: string
  has_fmodel: boolean
  has_blend: boolean
  has_psk?: boolean
  has_ue: boolean
  source_modified: boolean
  ue_modified?: boolean
  has_icon: boolean
  icon_path: string
  badges: ModBadge[]
  sound_metadata: Partial<Record<string, SoundEntry>>
  audio_overrides: Partial<Record<string, string>>   
  is_dynamic_pals_active: boolean
  dynamic_pal_variants: DynamicPalVariant[]
  preserve_materials: boolean 
  push_materials?: boolean
  push_textures?: boolean
  push_animbp?: boolean
  physical_variants?: string[]
  active_vanilla_replacer?: string
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
export interface MapSpawnRule {
  isBoss?: boolean
  level: number
  levelMax?: number
  x: number
  y: number
  z: number
  amountMin?: number
  amountMax?: number
  adds?: any[]
}
export interface WildSpawnerConfig {
  SpawnLocationID: string
  SpawnWeight: number 
  SpawnMinLevel: number
  SpawnMaxLevel: number
  SpawnMinGroup: number
  SpawnMaxGroup: number
}

export interface CreatorPal {
  CharacterID: string
  TemplateID: string
  Name: string
  Description: string
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
  MeshCapsuleHalfHeight?: number
  MeshCapsuleRadius?: number
  MeshRelativeLocation?: {
    X: number
    Y: number
    Z: number
  }
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
  PartnerSkillName?: string
  Learnset: LearnsetEntry[]
  PartnerWeaponElement?: string
  PartnerWeaponEffectType?: string
  PartnerWeaponNiagara?: string
  SaddleItem?: string
  SpawnLocationID?: string
  SpawnWeight?: number 
  SpawnMinLevel?: number
  SpawnMaxLevel?: number
  SpawnMinGroup?: number
  SpawnMaxGroup?: number
  EnableSpawns?: boolean
  WildSpawners?: WildSpawnerConfig[]
  BreedingCombos?: { parentA: string; parentB: string }[]
  CageSpawns?: string[]
  ItemDrops?: { itemId: string; rate: number; min: number; max: number }[]
  PartnerPlayerBuff?: "None" | "Attack" | "Defense" | "WorkSpeed"
  PartnerCampBuff?: "None" | string
  PartnerDropItems?: string[]
  GenerateBoss?: boolean
  GeneratePredator?: boolean
  BossPrefix?: string
  PredatorPrefix?: string
  BossHPMultiplier?: number
  PredatorHPMultiplier?: number
  PredatorAtkMultiplier?: number
  PredatorSpeedMultiplier?: number
  FieldBossSpawns?: MapSpawnRule[]
  GenerateBountyToken?: boolean
  HasFunnel?: boolean
  FunnelWazaID?: string
  EnablePaldeck?: boolean
  ZukanIndex?: number
  ZukanIndexSuffix?: string
  PaldexType?: string
  LongDescription?: string
  resolved_icon_path?: string
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
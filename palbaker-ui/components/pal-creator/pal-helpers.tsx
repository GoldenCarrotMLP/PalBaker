"use client"

import { Slider } from "@/components/ui/slider"
import { cn } from "@/lib/utils"

export const WORK_SUITS = [
  "Kindling", "Watering", "Planting", "Electricity", "Handiwork",
  "Gathering", "Lumbering", "Mining", "Oil Extraction", "Medicine",
  "Cooling", "Transport", "Farming",
] as const


export interface PartnerWeaponConfig {
  id: string
  name: string
  /** Aliases and substrings to match against the selected PartnerSkill string */
  aliases: string[]
  defaultElement: string
  defaultEffect: string
  defaultNiagara: string
  weaponSuffix: string
}

export const PARTNER_WEAPON_CONFIGS: PartnerWeaponConfig[] = [
  {
    id: "FlameThrower",
    name: "Flamethrower",
    aliases: [
      "flamethrower", 
      "kitsunebi", 
      "unique_kitsunebi_flamethrower", 
      "special_kitsunebi_flamethrower"
    ],
    defaultElement: "EPalElementType::Fire",
    defaultEffect: "EPalAdditionalEffectType::Burn",
    defaultNiagara: "Pal/Content/Pal/Effect/Skill/FlameThrower/NS_CommonSkill_Flamethrower",
    weaponSuffix: "Flamethrower"
  },
  {
    id: "Launcher",
    name: "Rocket / Pal Launcher",
    aliases: [
      "launcher", 
      "penguinlauncher", 
      "rocketlauncher", 
      "unique_penguin_launcher", 
      "special_penguin_launcher",
      "penguin"
    ],
    defaultElement: "EPalElementType::Water",
    defaultEffect: "EPalAdditionalEffectType::None",
    defaultNiagara: "Pal/Content/Pal/Effect/Skill/BlastCanon/NS_CommonSkill_BlastCannon_Impact",
    weaponSuffix: "Launcher"
  },
  {
    id: "Rifle",
    name: "Assault Rifle",
    aliases: [
      "rifle", 
      "monkeyrifle", 
      "assaultrifle", 
      "unique_monkey_rifle", 
      "special_monkey_rifle",
      "monkey"
    ],
    defaultElement: "EPalElementType::Leaf",
    defaultEffect: "EPalAdditionalEffectType::None",
    defaultNiagara: "Pal/Content/Pal/Effect/Skill/SeedMachinegun/NS_CommonSkill_SeedMachinegun",
    weaponSuffix: "Rifle"
  },
  {
    id: "Submachinegun",
    name: "Submachine Gun",
    aliases: [
      "submachinegun", 
      "carbunclo_submachinegun", 
      "carbunclosubmachinegun", 
      "unique_carbunclo_submachinegun",
      "carbunclo"
    ],
    defaultElement: "EPalElementType::Leaf",
    defaultEffect: "EPalAdditionalEffectType::None",
    defaultNiagara: "Pal/Content/Pal/Effect/Skill/PowerShot/NS_CommonSkill_PowerShot",
    weaponSuffix: "Submachinegun"
  },
  {
    id: "Minigun",
    name: "Heavy Minigun / Gatling",
    aliases: [
      "minigun", 
      "gatlinggun", 
      "grizzbolt_minigun", 
      "unique_grizzbolt_minigun",
      "grizzbolt"
    ],
    defaultElement: "EPalElementType::Electricity",
    defaultEffect: "EPalAdditionalEffectType::Electrical",
    defaultNiagara: "Pal/Content/Pal/Effect/Skill/Thunderbolt/NS_CommonSkill_Thunderbolt",
    weaponSuffix: "Minigun"
  }
]

export const PARTNER_WEAPON_CONFIG_MAP: Record<string, PartnerWeaponConfig> = Object.fromEntries(
  PARTNER_WEAPON_CONFIGS.map((c) => [c.id, c])
)

/**
 * Checks if a given PartnerSkill identifier represents a tunable partner weapon.
 */
export function getPartnerWeaponConfig(skillId?: string): PartnerWeaponConfig | null {
  if (!skillId || skillId === "None") return null
  const lower = skillId.toLowerCase().trim()

  for (const config of PARTNER_WEAPON_CONFIGS) {
    if (config.id.toLowerCase() === lower) return config
    if (config.aliases.some((alias) => alias.toLowerCase() === lower)) return config
    if (lower.includes(config.id.toLowerCase())) return config
    if (config.aliases.some((alias) => lower.includes(alias.toLowerCase()))) return config
  }
  return null
}


// Add to palbaker-ui/components/pal-creator/pal-helpers.tsx

export const CUSTOMIZABLE_WEAPON_SKILLS = [
  "PartnerSkill_Kitsunebi", "Flamethrower",
  "PartnerSkill_Penguin", "Launcher",
  "PartnerSkill_Monkey", "AssaultRifle", "Rifle",
  "PartnerSkill_Carbunclo", "SubmachineGun", "Submachinegun",
  "PartnerSkill_Grizzbolt", "HeavyWeapon", "Minigun"
]

export const WEAPON_EFFECT_OPTIONS: [string, string][] = [
  ["EPalAdditionalEffectType::None", "None"],
  ["EPalAdditionalEffectType::Burn", "Burn"],
  ["EPalAdditionalEffectType::Freeze", "Freeze"],
  ["EPalAdditionalEffectType::Electrical", "Electrical / Shock"],
  ["EPalAdditionalEffectType::Poison", "Poison"],
  ["EPalAdditionalEffectType::Wetness", "Wetness"],
  ["EPalAdditionalEffectType::Stun", "Stun"],
  ["EPalAdditionalEffectType::Sleep", "Sleep"],
  ["EPalAdditionalEffectType::Muddy", "Muddy"],
  ["EPalAdditionalEffectType::IvyCling", "Ivy Cling"],
  ["EPalAdditionalEffectType::Darkness", "Darkness"],
  ["EPalAdditionalEffectType::AttackUp", "Attack Up"],
  ["EPalAdditionalEffectType::DefenseUp", "Defense Up"],
  ["EPalAdditionalEffectType::Recovery", "Recovery"],
  ["EPalAdditionalEffectType::Trap_LegHold", "Trap Leg Hold"],
]

export const NIAGARA_EFFECT_LIST: string[] = [
  "Pal/Content/Pal/Effect/Skill/FlameThrower/NS_CommonSkill_Flamethrower",
  "Pal/Content/Pal/Effect/Skill/FrostBreath/NS_CommonSkill_FrostBreath",
  "Pal/Content/Pal/Effect/Skill/DragonBreath/NS_CommonSkill_DragonBreath",
  "Pal/Content/Pal/Effect/Skill/AcidRain/NS_CommonSkill_AcidRain",
  "Pal/Content/Pal/Effect/Skill/AcidRain/NS_CommonSkill_AcidRain_Bullet",
  "Pal/Content/Pal/Effect/Skill/AcidRain/NS_CommonSkill_AcidRain_Cloud",
  "Pal/Content/Pal/Effect/Skill/AirBlade/NS_CommonSkill_AirBlade",
  "Pal/Content/Pal/Effect/Skill/AirBlade/NS_CommonSkill_AirBlade_Charge",
  "Pal/Content/Pal/Effect/Skill/AirCanon/NS_CommonSkill_AirCanon",
  "Pal/Content/Pal/Effect/Skill/Apocalypse/NS_CommonSkill_Apocalypse_Tornado",
  "Pal/Content/Pal/Effect/Skill/Apocalypse/NS_CommonSkill_Apocalypse_Tornado_End",
  "Pal/Content/Pal/Effect/Skill/Apocalypse/NS_CommonSkill_Apocalypse_Tornado_Ready",
  "Pal/Content/Pal/Effect/Skill/AquaJet/NS_CommonSkill_AquaJet",
  "Pal/Content/Pal/Effect/Skill/AquaJet/NS_CommonSkill_AquaJetMuzzle",
  "Pal/Content/Pal/Effect/Skill/BeamSlicer/NS_CommonSkill_BeamSlicer",
  "Pal/Content/Pal/Effect/Skill/BeamSlicer/NS_CommonSkill_BeamSlicer_Charge",
  "Pal/Content/Pal/Effect/Skill/BeamSlicer/NS_CommonSkill_BeamSlicer_Impact",
  "Pal/Content/Pal/Effect/Skill/BeamSlicer/NS_CommonSkill_BeamSlicer_Mark",
  "Pal/Content/Pal/Effect/Skill/BlastCanon/NS_CommonSkill_BlastCannon_Impact",
  "Pal/Content/Pal/Effect/Skill/BlastCanon/NS_CommonSkill_BlastCannon_Ready",
  "Pal/Content/Pal/Effect/Skill/BlastCanon/NS_CommonSkill_BlastCannon_Start",
  "Pal/Content/Pal/Effect/Skill/BlizzardLance/NS_CommonSkill_BlizzardLance",
  "Pal/Content/Pal/Effect/Skill/BlizzardLance/NS_CommonSkill_BlizzardLance_ready",
  "Pal/Content/Pal/Effect/Skill/BubbleShot/NS_CommonSkill_BubbleShot",
  "Pal/Content/Pal/Effect/Skill/BubbleShot/NS_CommonSkill_BubbleShot_Splash",
  "Pal/Content/Pal/Effect/Skill/ChargeCanon/NS_CommonSkill_ChargeCanon_Bullet",
  "Pal/Content/Pal/Effect/Skill/ChargeCanon/NS_CommonSkill_ChargeCanon_Charge",
  "Pal/Content/Pal/Effect/Skill/ChargeCanon/NS_CommonSkill_ChargeCanon_Impact",
  "Pal/Content/Pal/Effect/Skill/ChargeCanon/NS_CommonSkill_ChargeCanon_Muzzle",
  "Pal/Content/Pal/Effect/Skill/Commet/NS_CommonSkill_Commet_Bullet",
  "Pal/Content/Pal/Effect/Skill/Commet/NS_CommonSkill_Commet_Ready",
  "Pal/Content/Pal/Effect/Skill/Commet/NS_CommonSkill_Commet_Ring",
  "Pal/Content/Pal/Effect/Skill/CrossWind/NS_CommonSkill_CrossWind_Slash",
  "Pal/Content/Pal/Effect/Skill/DarkArrow/NS_CommonSkill_DarkArrow",
  "Pal/Content/Pal/Effect/Skill/DarkArrow/NS_CommonSkill_DarkArrow_Bullet",
  "Pal/Content/Pal/Effect/Skill/DarkArrow/NS_CommonSkill_DarkArrow_Hit",
  "Pal/Content/Pal/Effect/Skill/DarkBall/NS_CommonSkill_DarkBall",
  "Pal/Content/Pal/Effect/Skill/DarkBall/NS_CommonSkill_DarkBall_Hit",
  "Pal/Content/Pal/Effect/Skill/DarkCanon/NS_CommonSkill_DarkCanon_Bullet",
  "Pal/Content/Pal/Effect/Skill/DarkCanon/NS_CommonSkill_DarkCanon_Impact",
  "Pal/Content/Pal/Effect/Skill/DarkCanon/NS_CommonSkill_DarkCanon_Muzzle",
  "Pal/Content/Pal/Effect/Skill/DarkLaser/NS_CommonSkill_DarkLaser",
  "Pal/Content/Pal/Effect/Skill/DarkLaser/NS_CommonSkill_DarkLaser_Charge",
  "Pal/Content/Pal/Effect/Skill/DarkPulse/NS_CommonSkill_DarkPulse_Bullet",
  "Pal/Content/Pal/Effect/Skill/DarkPulse/NS_CommonSkill_DarkPulse_Muzzle",
  "Pal/Content/Pal/Effect/Skill/DarkWave/NS_CommonSkill_DarkWave",
  "Pal/Content/Pal/Effect/Skill/DiamondFall/NS_CommonSkill_DiamondFall_Bullet",
  "Pal/Content/Pal/Effect/Skill/DiamondFall/NS_CommonSkill_DiamondFall_Impact",
  "Pal/Content/Pal/Effect/Skill/DiamondFall/NS_CommonSkill_DiamondFall_Ready",
  "Pal/Content/Pal/Effect/Skill/DiversionLaser/NS_CommonSkill_DiversionLaser_Charge",
  "Pal/Content/Pal/Effect/Skill/DragonCanon/NS_CommonSkill_DragonCanon_Bullet",
  "Pal/Content/Pal/Effect/Skill/DragonCanon/NS_CommonSkill_DragonCanon_Charge",
  "Pal/Content/Pal/Effect/Skill/DragonCanon/NS_CommonSkill_DragonCanon_Impact",
  "Pal/Content/Pal/Effect/Skill/DragonCanon/NS_CommonSkill_DragonCanon_Muzzle",
  "Pal/Content/Pal/Effect/Skill/DragonMeteor/NS_CommonSkill_DragonMeteor_Bullet",
  "Pal/Content/Pal/Effect/Skill/DragonMeteor/NS_CommonSkill_DragonMeteor_Explosion",
  "Pal/Content/Pal/Effect/Skill/DragonMeteor/NS_CommonSkill_DragonMeteor_Spawn",
  "Pal/Content/Pal/Effect/Skill/DragonWave/NS_CommonSkill_DragonWave",
  "Pal/Content/Pal/Effect/Skill/ElecWave/NS_CommonSkill_ElecWave",
  "Pal/Content/Pal/Effect/Skill/Eruption/NS_CommonSkill_Eruption_Bullet",
  "Pal/Content/Pal/Effect/Skill/Eruption/NS_CommonSkill_Eruption_Explosion",
  "Pal/Content/Pal/Effect/Skill/Eruption/NS_CommonSkill_Eruption_Ready",
  "Pal/Content/Pal/Effect/Skill/Eruption/NS_CommonSkill_Eruption_Start",
  "Pal/Content/Pal/Effect/Skill/FairyTornado/NS_CommonSkill_FairyTornado",
  "Pal/Content/Pal/Effect/Skill/FairyTornado/NS_CommonSkill_FairyTornado_End",
  "Pal/Content/Pal/Effect/Skill/FairyTornado/NS_CommonSkill_FairyTornado_Hit",
  "Pal/Content/Pal/Effect/Skill/FairyTornado/NS_CommonSkill_FairyTornado_Wind",
  "Pal/Content/Pal/Effect/Skill/FireBall/NS_CommonSkill_FireBall",
  "Pal/Content/Pal/Effect/Skill/FireBall/NS_CommonSkill_FireBall_Impact",
  "Pal/Content/Pal/Effect/Skill/FireBall/NS_CommonSkill_FireBall_ready",
  "Pal/Content/Pal/Effect/Skill/FireSeed/NS_CommonSkill_FireSeed",
  "Pal/Content/Pal/Effect/Skill/FireSeed/NS_CommonSkill_FireSeed_Bullet",
  "Pal/Content/Pal/Effect/Skill/FireSeed/NS_CommonSkill_FireSeed_Hit",
  "Pal/Content/Pal/Effect/Skill/FireSeed/NS_CommonSkill_FireSeed_Spark",
  "Pal/Content/Pal/Effect/Skill/FlameFunnel/NS_CommonSkill_FlameFunnel_Bullet",
  "Pal/Content/Pal/Effect/Skill/FlameFunnel/NS_CommonSkill_FlameFunnel_Mai",
  "Pal/Content/Pal/Effect/Skill/FlameWall/NS_CommonSkill_FlameWall",
  "Pal/Content/Pal/Effect/Skill/FlameWall/NS_CommonSkill_FlameWall_Explosion",
  "Pal/Content/Pal/Effect/Skill/FlameWall/NS_CommonSkill_FlameWall_Ready",
  "Pal/Content/Pal/Effect/Skill/FlareTornado/NS_CommonSkill_FlareTornado",
  "Pal/Content/Pal/Effect/Skill/FlareTornado/NS_CommonSkill_FlareTornado_aura",
  "Pal/Content/Pal/Effect/Skill/FlareTornado/NS_CommonSkill_FlareTornado_aura_loop",
  "Pal/Content/Pal/Effect/Skill/FlareTornado/NS_CommonSkill_FlareTornado_End",
  "Pal/Content/Pal/Effect/Skill/GhostFlame/NS_CommonSkill_GhostFlame",
  "Pal/Content/Pal/Effect/Skill/GhostFlame/NS_CommonSkill_GhostFlame_Bullet",
  "Pal/Content/Pal/Effect/Skill/GrassTornado/NS_CommonSkill_GrassTornado",
  "Pal/Content/Pal/Effect/Skill/GrassTornado/NS_CommonSkill_GrassTornado_End",
  "Pal/Content/Pal/Effect/Skill/GravityShot/NS_CommonSkill_GravityShot",
  "Pal/Content/Pal/Effect/Skill/GravityShot/NS_CommonSkill_GravityShot_Bullet",
  "Pal/Content/Pal/Effect/Skill/HolyBlast/NS_CommonSkill_HolyBlast_Explosion",
  "Pal/Content/Pal/Effect/Skill/HolyBlast/NS_CommonSkill_HolyBlast_Explosion_2",
  "Pal/Content/Pal/Effect/Skill/HolyBlast/NS_CommonSkill_HolyBlast_Explosion_3",
  "Pal/Content/Pal/Effect/Skill/HydroPump/NS_CommonSkill_HydroPump",
  "Pal/Content/Pal/Effect/Skill/HydroPump/NS_CommonSkill_HydroPump_charge",
  "Pal/Content/Pal/Effect/Skill/HydroPump/NS_CommonSkill_HydroPump_Explosion",
  "Pal/Content/Pal/Effect/Skill/HydroSlicer/NS_CommonSkill_HydroSlicer_Beam",
  "Pal/Content/Pal/Effect/Skill/HydroSlicer/NS_CommonSkill_HydroSlicer_Charge",
  "Pal/Content/Pal/Effect/Skill/HydroSlicer/NS_CommonSkill_HydroSlicer_Splash",
  "Pal/Content/Pal/Effect/Skill/HyperBeam/NS_CommonSkill_HyperBeam",
  "Pal/Content/Pal/Effect/Skill/HyperBeam/NS_CommonSkill_HyperBeam_charge",
  "Pal/Content/Pal/Effect/Skill/IceAge/NS_CommonSkill_IceAge",
  "Pal/Content/Pal/Effect/Skill/IceAge/NS_CommonSkill_IceAge_Ready",
  "Pal/Content/Pal/Effect/Skill/IceBlade/NS_CommonSkill_IceBlade",
  "Pal/Content/Pal/Effect/Skill/IceWall/NS_CommonSkill_IceWall",
  "Pal/Content/Pal/Effect/Skill/IceWall/NS_CommonSkill_IceWall_Break",
  "Pal/Content/Pal/Effect/Skill/IceWall/NS_CommonSkill_IceWall_Ready",
  "Pal/Content/Pal/Effect/Skill/IcicleLine/NS_CommonSkill_IcicleLine",
  "Pal/Content/Pal/Effect/Skill/IcicleThrow/NS_CommonSkill_DoubleIcicleThrow_Bullet",
  "Pal/Content/Pal/Effect/Skill/IcicleThrow/NS_CommonSkill_IcicleThrow_Bullet",
  "Pal/Content/Pal/Effect/Skill/IcicleThrow/NS_CommonSkill_IcicleThrow_Charge",
  "Pal/Content/Pal/Effect/Skill/IcicleThrow/NS_CommonSkill_IcicleThrow_Impact",
  "Pal/Content/Pal/Effect/Skill/Inferno/NS_CommonSkill_Inferno_Explosion",
  "Pal/Content/Pal/Effect/Skill/Inferno/NS_CommonSkill_Inferno_Omen",
  "Pal/Content/Pal/Effect/Skill/KingWhale/CreepingBubble/NS_CommonSkill_CreepingBubble",
  "Pal/Content/Pal/Effect/Skill/KingWhale/CreepingBubble/NS_CommonSkill_CreepingBubble_Explosion",
  "Pal/Content/Pal/Effect/Skill/LineGeyser/NS_CommonSkill_LineGeyser",
  "Pal/Content/Pal/Effect/Skill/LockonLaser/NS_CommonSkill_LockonLaser_Bullet",
  "Pal/Content/Pal/Effect/Skill/LockonLaser/NS_CommonSkill_LockonLaser_Charge",
  "Pal/Content/Pal/Effect/Skill/LockonLaser/NS_CommonSkill_LockonLaser_Impact",
  "Pal/Content/Pal/Effect/Skill/LockonLaser/NS_CommonSkill_LockonLaser_LaserSight",
  "Pal/Content/Pal/Effect/Skill/LockonLaser/NS_CommonSkill_ShokeiLaser_Charge",
  "Pal/Content/Pal/Effect/Skill/LockonLaser/NS_CommonSkill_ShokeiLaser_Impact",
  "Pal/Content/Pal/Effect/Skill/LockonLaser/NS_CommonSkill_ShokeiLaser_LaserSight",
  "Pal/Content/Pal/Effect/Skill/MudShot/NS_CommonSkill_MudShot",
  "Pal/Content/Pal/Effect/Skill/MudShot/NS_CommonSkill_MudShot_Dust",
  "Pal/Content/Pal/Effect/Skill/PerfectStorm/NS_CommonSkill_PerfectStorm",
  "Pal/Content/Pal/Effect/Skill/PerfectStorm/NS_CommonSkill_PerfectStorm_aura",
  "Pal/Content/Pal/Effect/Skill/PerfectStorm/NS_CommonSkill_PerfectStorm_aura_loop",
  "Pal/Content/Pal/Effect/Skill/PerfectStorm/NS_CommonSkill_PerfectStorm_Main",
  "Pal/Content/Pal/Effect/Skill/PoisonShot/NS_CommonSkill_PoisonShot",
  "Pal/Content/Pal/Effect/Skill/PoisonShot/NS_CommonSkill_PoisonShot_GroundHit",
  "Pal/Content/Pal/Effect/Skill/PoisonShower/NS_CommonSkill_PoisonShower_Bullet",
  "Pal/Content/Pal/Effect/Skill/PoisonShower/NS_CommonSkill_PoisonShower_Explosion",
  "Pal/Content/Pal/Effect/Skill/PoisonShower/NS_CommonSkill_PoisonShower_Ready",
  "Pal/Content/Pal/Effect/Skill/PoisonShower/NS_CommonSkill_PoisonShower_Sign",
  "Pal/Content/Pal/Effect/Skill/PowerBall/NS_CommonSkill_PowerBall",
  "Pal/Content/Pal/Effect/Skill/PowerBall/NS_CommonSkill_PowerBall_charge",
  "Pal/Content/Pal/Effect/Skill/PowerBall/NS_CommonSkill_PowerBall_explosion",
  "Pal/Content/Pal/Effect/Skill/PowerShot/NS_CommonSkill_PowerShot",
  "Pal/Content/Pal/Effect/Skill/PowerShot/NS_CommonSkill_PowerShot_Charge",
  "Pal/Content/Pal/Effect/Skill/PredatorBeam/NS_CommonSkill_PredatorBeam",
  "Pal/Content/Pal/Effect/Skill/PredatorBeam/NS_CommonSkill_PredatorBeam_charge",
  "Pal/Content/Pal/Effect/Skill/PredatorLockon/NS_CommonSkill_PredatorLockon_Bullet",
  "Pal/Content/Pal/Effect/Skill/PredatorLockon/NS_CommonSkill_PredatorLockon_Charge",
  "Pal/Content/Pal/Effect/Skill/PredatorLockon/NS_CommonSkill_PredatorLockon_Hit",
  "Pal/Content/Pal/Effect/Skill/PredatorWave/NS_CommonSkill_PredatorWave_Charge",
  "Pal/Content/Pal/Effect/Skill/PredatorWave/NS_CommonSkill_PredatorWave_Wave",
  "Pal/Content/Pal/Effect/Skill/Psychokinesis/NS_CommonSkill_Psychokinesis_Ready",
  "Pal/Content/Pal/Effect/Skill/ReflectiveShuriken/NS_CommonSkill_ReflectiveShuriken",
  "Pal/Content/Pal/Effect/Skill/ReflectiveShuriken/NS_CommonSkill_ReflectiveShuriken_Charge",
  "Pal/Content/Pal/Effect/Skill/RipTide/NS_CommonSkill_RipTide",
  "Pal/Content/Pal/Effect/Skill/RipTide/NS_CommonSkill_RipTide_Blast",
  "Pal/Content/Pal/Effect/Skill/RockBeat/NS_CommonSkill_RockBeat_Impact",
  "Pal/Content/Pal/Effect/Skill/RockBeat/NS_CommonSkill_RockBeat_Omen",
  "Pal/Content/Pal/Effect/Skill/RockBeat/NS_CommonSkill_RockBeat_Rock",
  "Pal/Content/Pal/Effect/Skill/RockLance/NS_CommonSkill_RockLance",
  "Pal/Content/Pal/Effect/Skill/RockLance/NS_CommonSkill_RockLance_ready",
  "Pal/Content/Pal/Effect/Skill/RootAttack/NS_CommonSkill_RootAttack",
  "Pal/Content/Pal/Effect/Skill/RootAttack/NS_CommonSkill_RootAttack_Vines",
  "Pal/Content/Pal/Effect/Skill/RootLance/NS_CommonSkill_RootLance_Attack",
  "Pal/Content/Pal/Effect/Skill/RootLance/NS_CommonSkill_RootLance_Vine",
  "Pal/Content/Pal/Effect/Skill/SandTornado/NS_CommonSkill_SandTornado",
  "Pal/Content/Pal/Effect/Skill/SandTornado/NS_CommonSkill_SandTornado_End",
  "Pal/Content/Pal/Effect/Skill/SandTwist/NS_CommonSkill_SandTwist",
  "Pal/Content/Pal/Effect/Skill/SandTwist/NS_CommonSkill_SandTwist_End",
  "Pal/Content/Pal/Effect/Skill/SandTwist/NS_CommonSkill_SandTwist_Ready",
  "Pal/Content/Pal/Effect/Skill/SeaGush/NS_CommonSkill_SeaGush",
  "Pal/Content/Pal/Effect/Skill/SeaGush/NS_CommonSkill_SeaGush_Bullet",
  "Pal/Content/Pal/Effect/Skill/SeedMachinegun/NS_CommonSkill_SeedMachinegun",
  "Pal/Content/Pal/Effect/Skill/SeedMine/NS_CommonSkill_SeedMine",
  "Pal/Content/Pal/Effect/Skill/SeedMine/NS_CommonSkill_SeedMine_Explosion",
  "Pal/Content/Pal/Effect/Skill/SeedMine/NS_CommonSkill_SeedMine_Main",
  "Pal/Content/Pal/Effect/Skill/SelfExplosion/NS_CommonSkill_SelfExplosion",
  "Pal/Content/Pal/Effect/Skill/ShadowBall/NS_CommonSkill_ShadowBall",
  "Pal/Content/Pal/Effect/Skill/ShadowBall/NS_CommonSkill_ShadowBall_charge_2",
  "Pal/Content/Pal/Effect/Skill/SolarBeam/NS_CommonSkill_SolarBeam",
  "Pal/Content/Pal/Effect/Skill/SolarBeam/NS_CommonSkill_SolarBeam_charge",
  "Pal/Content/Pal/Effect/Skill/SpreadPulse/NS_CommonSkill_SpreadPulse_Bullet",
  "Pal/Content/Pal/Effect/Skill/SpreadPulse/NS_CommonSkill_SpreadPulse_Muzzle",
  "Pal/Content/Pal/Effect/Skill/StarMine/NS_CommonSkill_StarMine_Cloud",
  "Pal/Content/Pal/Effect/Skill/StarMine/NS_CommonSkill_StarMine_Impact",
  "Pal/Content/Pal/Effect/Skill/StarMine/NS_CommonSkill_StarMine_Seed",
  "Pal/Content/Pal/Effect/Skill/StoneShotgun/NS_CommonSkill_StoneShotgun",
  "Pal/Content/Pal/Effect/Skill/ThrowRock/NS_CommonSkill_ThrowRock",
  "Pal/Content/Pal/Effect/Skill/ThrowRock/NS_CommonSkill_ThrowRock_Trail",
  "Pal/Content/Pal/Effect/Skill/Thunderbolt/NS_CommonSkill_Railbolt",
  "Pal/Content/Pal/Effect/Skill/Thunderbolt/NS_CommonSkill_Railbolt_Ready",
  "Pal/Content/Pal/Effect/Skill/Thunderbolt/NS_CommonSkill_Thunderbolt",
  "Pal/Content/Pal/Effect/Skill/Thunderbolt/NS_CommonSkill_Thunderbolt_ready",
  "Pal/Content/Pal/Effect/Skill/Thunderbolt/NS_CommonSkill_Thunderbolt_ready_Loop",
  "Pal/Content/Pal/Effect/Skill/ThunderFunnel/NS_CommonSkill_ThunderFunnel_Bullet",
  "Pal/Content/Pal/Effect/Skill/ThunderFunnel/NS_CommonSkill_ThunderFunnel_Main",
  "Pal/Content/Pal/Effect/Skill/ThunderSpear/NS_CommonSkill_ThunderSpear",
  "Pal/Content/Pal/Effect/Skill/ThunderSpear/NS_CommonSkill_ThunderSpear_Bullet",
  "Pal/Content/Pal/Effect/Skill/ThunderStorm/NS_CommonSkill_ThunderStorm",
  "Pal/Content/Pal/Effect/Skill/ThunderStorm/NS_CommonSkill_ThunderStorm_Ready",
  "Pal/Content/Pal/Effect/Skill/Tremor/NS_CommonSkill_Tremor",
  "Pal/Content/Pal/Effect/Skill/Tremor/NS_CommonSkill_Tremor_Blast",
  "Pal/Content/Pal/Effect/Skill/Tremor/NS_CommonSkill_Tremor_impact",
  "Pal/Content/Pal/Effect/Skill/Tremor/NS_CommonSkill_Tremor_Ready",
  "Pal/Content/Pal/Effect/Skill/WallSplash/NS_CommonSkill_WallSplash",
  "Pal/Content/Pal/Effect/Skill/WallSplash/NS_CommonSkill_WallSplash_Omen_temp",
  "Pal/Content/Pal/Effect/Skill/WaterBall/NS_CommonSkill_WaterBall",
  "Pal/Content/Pal/Effect/Skill/WaterBall/NS_CommonSkill_WaterBall_Impact",
  "Pal/Content/Pal/Effect/Skill/WindBurst/NS_CommonSkill_WindBurst_Burst",
  "Pal/Content/Pal/Effect/Skill/WindBurst/NS_CommonSkill_WindBurst_Charge",
]

export type WorkKey = typeof WORK_SUITS[number]

export const WORK_SUITABILITY_MAP: Record<WorkKey, string> = {
  "Kindling":  "WorkSuitability_EmitFlame",
  "Watering":  "WorkSuitability_Watering",
  "Planting":  "WorkSuitability_Seeding",
  "Electricity": "WorkSuitability_GenerateElectricity",
  "Handiwork": "WorkSuitability_Handcraft",
  "Gathering": "WorkSuitability_Collection",
  "Lumbering": "WorkSuitability_Deforest",
  "Mining":    "WorkSuitability_Mining",
  "Oil Extraction": "WorkSuitability_OilExtraction",
  "Medicine":  "WorkSuitability_ProductMedicine",
  "Cooling": "WorkSuitability_Cool",
  "Transport": "WorkSuitability_Transport",
  "Farming": "WorkSuitability_MonsterFarm",
}

export const ELEMENT_OPTIONS: [string, string][] = [
  ["EPalElementType::None",        "None"],
  ["EPalElementType::Normal",      "Neutral"],
  ["EPalElementType::Fire",        "Fire"],
  ["EPalElementType::Water",       "Water"],
  ["EPalElementType::Leaf",        "Grass"],
  ["EPalElementType::Electricity", "Electric"],
  ["EPalElementType::Ice",         "Ice"],
  ["EPalElementType::Earth",       "Ground"],
  ["EPalElementType::Dark",        "Dark"],
  ["EPalElementType::Dragon",      "Dragon"],
]

export function cleanElement(raw: string): string {
  if (!raw) return "Normal"
  const part = raw.split("::")[1] || "Normal"
  if (part === "Leaf")        return "Grass"
  if (part === "Electricity") return "Electric"
  if (part === "Earth")       return "Ground"
  if (part === "None")        return ""
  return part
}

export function FieldGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">{label}</label>
      {children}
    </div>
  )
}

export function SectionLabel({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <h2 className={cn("text-muted-foreground text-xs font-bold uppercase tracking-widest", className)}>
      {children}
    </h2>
  )
}

export function StatSlider({
  label,
  value,
  onChange,
  min = 1,
  max = 500,
}: {
  label: string
  value: number
  onChange: (v: number) => void
  min?: number
  max?: number
}) {
  return (
    <div className="grid grid-cols-[120px_1fr_56px] items-center gap-3">
      <span className="text-muted-foreground text-[10px] font-semibold uppercase tracking-wider">{label}</span>
      <Slider
        value={[value]}
        min={min}
        max={max}
        step={1}
        onValueChange={(vals) => onChange(Array.isArray(vals) ? (vals as number[])[0] : Number(vals))}
        className="[&_[role=slider]]:bg-primary [&_[role=slider]]:border-primary"
      />
      <div className="bg-muted/60 border border-border rounded px-2 py-1 text-primary text-[10px] font-mono text-center">
        {value}
      </div>
    </div>
  )
}
"use client"

import { useState, useEffect, useMemo } from "react"
import { type CreatorPal, type CreatorPalFeatures, type ActiveSkill } from "@/lib/mock-data"
import { FieldGroup, SectionLabel, NIAGARA_EFFECT_LIST, ELEMENT_OPTIONS, WEAPON_EFFECT_OPTIONS } from "./pal-helpers"
import { Switch } from "@/components/ui/switch"
import { SearchableSelect } from "@/components/ui/searchable-select"
import { Plus, Trash2, Shield, Crosshair, Map, CloudLightning, Move, Star, Sparkles } from "lucide-react"
import { ModManagerAPI } from "@/lib/data-service"
import { cn } from "@/lib/utils"

interface Props {
  pal: CreatorPal
  onUpdate: (patch: Partial<CreatorPal>) => void
  activeSkills: Record<string, ActiveSkill>
}

export function FeatureEditor({ pal, onUpdate, activeSkills }: Props) {
  const features = pal.Features || {}
  const customFeaturesEnabled = !!features.CustomFeaturesEnabled

  const toggleMasterSwitch = (val: boolean) => {
    onUpdate({
      Features: {
        ...features,
        CustomFeaturesEnabled: val,
      },
    })
  }

  const updateFeature = (key: keyof CreatorPalFeatures, data: any) => {
    onUpdate({ Features: { ...features, [key]: data } })
  }

  // --- BONES FOR SOCKET DROPDOWN ---
  const [localBones, setLocalBones] = useState<string[]>(pal.all_bones || [])

  useEffect(() => {
    if (pal.all_bones && pal.all_bones.length > 0) {
      setLocalBones(pal.all_bones)
    } else {
      const fetchBones = async () => {
        try {
          const target = pal.CharacterID || pal.TemplateID
          const res = await ModManagerAPI.dynamicPalsSidecar("Monster", target, `${target}.blend`)
          if (res?.status === "success" && Array.isArray(res.data?.all_bones) && res.data.all_bones.length > 0) {
            setLocalBones(res.data.all_bones)
          } else if (pal.TemplateID) {
            const resTmpl = await ModManagerAPI.dynamicPalsSidecar("Monster", pal.TemplateID, `${pal.TemplateID}.blend`)
            if (resTmpl?.status === "success" && Array.isArray(resTmpl.data?.all_bones) && resTmpl.data.all_bones.length > 0) {
              setLocalBones(resTmpl.data.all_bones)
            }
          }
        } catch {
          // Silent fallback
        }
      }
      fetchBones()
    }
  }, [pal.CharacterID, pal.TemplateID, pal.all_bones])

  // --- SUB-FEATURES ---
  const riding = features.Riding || { Enabled: false }
  const coopWeapon = features.CoopWeapon || { Enabled: false }
  const funnel = features.Funnel || { Enabled: false }
  const shield = features.Shield || { Enabled: false }
  const evasion = features.CombatEvasion || {}
  const utility = features.CoopUtility || {}
  const vfx = features.VFX || []
  const light = features.TimerPointLight || { Enabled: false }

  const boneOptions = useMemo(() => {
    const bones = new Set(localBones)
    if (riding.AttachSocket) {
      bones.add(riding.AttachSocket)
    }
    if (bones.size === 0) {
      ["PlayerRideMarker", "spine_01", "pelvis", "spine_02", "root"].forEach((b) => bones.add(b))
    }
    return Array.from(bones).map((b) => ({
      value: b,
      label: b,
    }))
  }, [localBones, riding.AttachSocket])

  const niagaraOptions = NIAGARA_EFFECT_LIST.map((path) => {
    const parts = path.split("/")
    const name = parts[parts.length - 1].replace("NS_CommonSkill_", "")
    return { value: path, label: `${name} (${parts[parts.length - 2]})` }
  })

  const missingDeps = pal.missing_dependencies || []

  return (
    <div className="grid grid-cols-2 gap-x-6 gap-y-5">
      {/* --- MASTER FEATURE CUSTOMIZATION SWITCH --- */}
      <div className="col-span-2 p-4 rounded-xl border border-border bg-card/80 shadow-md flex items-center justify-between gap-4">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <Sparkles className="size-4 text-primary" />
            <span className="font-bold text-sm text-foreground uppercase tracking-wider">
              Customize Abilities & Feature Components
            </span>
            <span
              className={cn(
                "text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border",
                customFeaturesEnabled
                  ? "bg-primary/20 text-primary border-primary/40"
                  : "bg-muted text-muted-foreground border-border"
              )}
            >
              {customFeaturesEnabled ? "ACTIVE (CUSTOM OVERRIDES)" : "OFF (PRESERVE TEMPLATE 1:1)"}
            </span>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed max-w-2xl">
            When <strong>disabled</strong> (default), PalBaker preserves the parent template&apos;s original riding markers, weapons, and companion components untouched (only applying vital mesh and class renames). Turn this <strong>ON</strong> to override or inject custom mounts, weapons, funnels, shields, or mobility.
          </p>
        </div>

        <Switch
          checked={customFeaturesEnabled}
          onCheckedChange={toggleMasterSwitch}
        />
      </div>

      {/* --- FEATURE VERIFICATION BANNER --- */}
      {missingDeps.length > 0 && customFeaturesEnabled && (
        <div className="col-span-2 p-3.5 rounded-lg border border-amber-500/40 bg-amber-500/10 flex flex-col gap-2 text-xs text-amber-200 animate-in fade-in-50 duration-200">
          <div className="font-bold flex items-center gap-2 text-amber-400">
            <span className="text-base">⚠️</span>
            <span>Feature Verification Notices ({missingDeps.length} item{missingDeps.length > 1 ? "s" : ""})</span>
          </div>
          <ul className="list-disc pl-5 flex flex-col gap-1 text-[11px] text-amber-200/90 leading-relaxed font-mono">
            {missingDeps.map((d: any, idx: number) => (
              <li key={idx}>
                <strong className="text-amber-300 font-sans">[{d.feature}]</strong>: {d.message}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* CONTAINER FOR ALL SUB-FEATURES (DIMMED WHEN MASTER IS OFF) */}
      <div
        className={cn(
          "col-span-2 grid grid-cols-2 gap-x-6 gap-y-5 transition-opacity duration-200",
          !customFeaturesEnabled && "opacity-40 pointer-events-none select-none"
        )}
      >
        {/* --- MOUNTS & SADDLES --- */}
        <div className="border border-border/50 p-4 rounded bg-background/30 shadow-inner flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <SectionLabel className="flex items-center gap-2">
              <Map className="size-4 text-primary" /> Mounts & Saddles
            </SectionLabel>
            <Switch
              checked={riding.Enabled}
              onCheckedChange={(c) => updateFeature("Riding", { ...riding, Enabled: c })}
            />
          </div>
          {riding.Enabled && (
            <div className="flex flex-col gap-3 border-t border-border/40 pt-3">
              <div className="grid grid-cols-2 gap-3">
                <FieldGroup label="Saddle Type">
                  <select
                    value={riding.MarkerType || "Saddle"}
                    onChange={(e) => updateFeature("Riding", { ...riding, MarkerType: e.target.value })}
                    className="input-field"
                  >
                    <option value="Saddle">Saddle (Standard)</option>
                    <option value="BiggerHorse">BiggerHorse (Large)</option>
                    <option value="Sit">Sit (Upright)</option>
                  </select>
                </FieldGroup>
                <FieldGroup label="Ride Posture">
                  <select
                    value={riding.RidePosition || "HorseRide"}
                    onChange={(e) => updateFeature("Riding", { ...riding, RidePosition: e.target.value })}
                    className="input-field"
                  >
                    <option value="HorseRide">Straddle</option>
                    <option value="BiggerHorseRide">Wide Straddle</option>
                    <option value="Sit">Seated Forward</option>
                  </select>
                </FieldGroup>
              </div>

              <FieldGroup label="Socket Bone (Attach Socket)">
                <SearchableSelect
                  value={riding.AttachSocket || (boneOptions[0]?.value ?? "PlayerRideMarker")}
                  onChange={(val) => updateFeature("Riding", { ...riding, AttachSocket: val })}
                  options={boneOptions}
                  placeholder="Search bone from mesh (e.g. spine_01, pelvis)..."
                  emptyText="No bones found in mesh."
                />
                <span className="text-[10px] text-muted-foreground leading-tight">
                  Bone to parent the player saddle. Native mount templates possess &apos;PlayerRideMarker&apos;; non-mount templates should select &apos;spine_01&apos; or &apos;pelvis&apos;.
                </span>
              </FieldGroup>

              <div className="grid grid-cols-2 gap-3 pt-1">
                <label className="flex items-center justify-between p-2 rounded border border-border/40 bg-muted/20 cursor-pointer">
                  <span className="text-xs text-foreground font-medium">Trample Damage</span>
                  <Switch
                    size="sm"
                    checked={!!riding.WithSpeedCollision}
                    onCheckedChange={(c) => updateFeature("Riding", { ...riding, WithSpeedCollision: c })}
                  />
                </label>
                <label className="flex items-center justify-between p-2 rounded border border-border/40 bg-muted/20 cursor-pointer">
                  <span className="text-xs text-foreground font-medium">Mounted Shooting</span>
                  <Switch
                    size="sm"
                    checked={!!riding.WithMountedShooter}
                    onCheckedChange={(c) => updateFeature("Riding", { ...riding, WithMountedShooter: c })}
                  />
                </label>
              </div>
            </div>
          )}
        </div>

        {/* --- PARTNER WEAPONS --- */}
        <div className="border border-border/50 p-4 rounded bg-background/30 shadow-inner flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <SectionLabel className="flex items-center gap-2">
              <Crosshair className="size-4 text-primary" /> Partner Weapons
            </SectionLabel>
            <Switch
              checked={coopWeapon.Enabled}
              onCheckedChange={(c) => updateFeature("CoopWeapon", { ...coopWeapon, Enabled: c })}
            />
          </div>
          {coopWeapon.Enabled && (
            <div className="flex flex-col gap-3 border-t border-border/40 pt-3">
              <FieldGroup label="Weapon Mode">
                <select
                  value={coopWeapon.Mode || "AssaultRifle"}
                  onChange={(e) => updateFeature("CoopWeapon", { ...coopWeapon, Mode: e.target.value })}
                  className="input-field"
                >
                  <option value="AssaultRifle">Assault Rifle</option>
                  <option value="Shotgun">Shotgun</option>
                  <option value="Flamethrower">Flamethrower</option>
                  <option value="Launcher">Rocket Launcher</option>
                  <option value="OnHeadSubmachineGun">Submachine Gun (Head)</option>
                  <option value="Minigun">Minigun</option>
                </select>
              </FieldGroup>
              {coopWeapon.Mode === "Flamethrower" && (
                <div className="grid grid-cols-2 gap-3">
                  <FieldGroup label="Element">
                    <select
                      value={coopWeapon.Element || "EPalElementType::Fire"}
                      onChange={(e) => updateFeature("CoopWeapon", { ...coopWeapon, Element: e.target.value })}
                      className="input-field"
                    >
                      {ELEMENT_OPTIONS.map(([val, label]) => (
                        <option key={val} value={val}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </FieldGroup>
                  <FieldGroup label="Status Effect">
                    <select
                      value={coopWeapon.Effect || "EPalAdditionalEffectType::Burn"}
                      onChange={(e) => updateFeature("CoopWeapon", { ...coopWeapon, Effect: e.target.value })}
                      className="input-field"
                    >
                      {WEAPON_EFFECT_OPTIONS.map(([val, label]) => (
                        <option key={val} value={val}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </FieldGroup>
                </div>
              )}
            </div>
          )}
        </div>

        {/* --- SATELLITE FUNNEL --- */}
        <div className="border border-border/50 p-4 rounded bg-background/30 shadow-inner flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <SectionLabel className="flex items-center gap-2">
              <Star className="size-4 text-primary" /> Satellite Funnels
            </SectionLabel>
            <Switch
              checked={funnel.Enabled}
              onCheckedChange={(c) => updateFeature("Funnel", { ...funnel, Enabled: c })}
            />
          </div>
          {funnel.Enabled && (
            <div className="flex flex-col gap-3 border-t border-border/40 pt-3">
              <FieldGroup label="Minion Base Preset">
                <select
                  value={funnel.Preset || "DreamDemon"}
                  onChange={(e) => updateFeature("Funnel", { ...funnel, Preset: e.target.value })}
                  className="input-field"
                >
                  <option value="DreamDemon">Daedream (Orbiter)</option>
                  <option value="Dazzi">Dazzi (Shoulder)</option>
                  <option value="Flopie">Flopie (Collector)</option>
                </select>
              </FieldGroup>
              <FieldGroup label="Targeting AI">
                <select
                  value={funnel.TargetingAction || "ShadowBall"}
                  onChange={(e) => updateFeature("Funnel", { ...funnel, TargetingAction: e.target.value })}
                  className="input-field"
                >
                  <option value="ShadowBall">Barrage (ShadowBall)</option>
                  <option value="Thunderbolt">Strike (Thunderbolt)</option>
                  <option value="SeedMachinegun">Stream (SeedMachinegun)</option>
                </select>
              </FieldGroup>
              <FieldGroup label="Attack Skill">
                <SearchableSelect
                  value={funnel.CustomWazaID || "Funnel_DreamDemon"}
                  onChange={(val) => updateFeature("Funnel", { ...funnel, CustomWazaID: val })}
                  options={[
                    { value: "Funnel_DreamDemon", label: "Daedream Base" },
                    { value: "Funnel_RaijinDaughter", label: "Dazzi Base" },
                    ...Object.values(activeSkills).map((s) => ({
                      value: s.id,
                      label: `${s.id.replace(/_/g, " ")} (${s.element})`,
                    })),
                  ]}
                  placeholder="Search Attack Skills..."
                />
              </FieldGroup>
            </div>
          )}
        </div>

        {/* --- DEFENSIVE SHIELD --- */}
        <div className="border border-border/50 p-4 rounded bg-background/30 shadow-inner flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <SectionLabel className="flex items-center gap-2">
              <Shield className="size-4 text-primary" /> Energy Shield
            </SectionLabel>
            <Switch
              checked={shield.Enabled}
              onCheckedChange={(c) => updateFeature("Shield", { ...shield, Enabled: c })}
            />
          </div>
          {shield.Enabled && (
            <div className="flex flex-col gap-3 border-t border-border/40 pt-3">
              <FieldGroup label="Radius">
                <input
                  type="number"
                  value={shield.Radius ?? 110.0}
                  onChange={(e) =>
                    updateFeature("Shield", { ...shield, Radius: parseFloat(e.target.value) || 110.0 })
                  }
                  className="input-field"
                />
              </FieldGroup>
              <FieldGroup label="Attach Socket">
                <input
                  value={shield.AttachSocket || "lowerarm_l"}
                  onChange={(e) => updateFeature("Shield", { ...shield, AttachSocket: e.target.value })}
                  className="input-field"
                />
              </FieldGroup>
            </div>
          )}
        </div>

        {/* --- EVASION & UTILITY --- */}
        <div className="border border-border/50 p-4 rounded bg-background/30 shadow-inner flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <SectionLabel className="flex items-center gap-2">
              <Move className="size-4 text-primary" /> Evasion & Utility
            </SectionLabel>
          </div>
          <div className="flex flex-col gap-3 border-t border-border/40 pt-3">
            <FieldGroup label="Combat Evasion (SideMove)">
              <select
                value={evasion.SideMoveStyle || "None"}
                onChange={(e) =>
                  updateFeature("CombatEvasion", {
                    ...evasion,
                    SideMoveStyle: e.target.value === "None" ? "" : e.target.value,
                  })
                }
                className="input-field"
              >
                <option value="None">Default</option>
                <option value="Teleport">Teleport</option>
                <option value="SideStep">Side Step</option>
                <option value="DashTurn">Dash Turn</option>
                <option value="RoundStep">Round Step</option>
              </select>
            </FieldGroup>
            <FieldGroup label="Disengage (Leave)">
              <select
                value={evasion.LeaveStyle || "None"}
                onChange={(e) =>
                  updateFeature("CombatEvasion", {
                    ...evasion,
                    LeaveStyle: e.target.value === "None" ? "" : e.target.value,
                  })
                }
                className="input-field"
              >
                <option value="None">Default</option>
                <option value="TurnRun">Turn Run</option>
                <option value="BackStep">Back Step</option>
              </select>
            </FieldGroup>
            <FieldGroup label="Coop Utility (Action)">
              <select
                value={utility.SkillType || "None"}
                onChange={(e) =>
                  updateFeature("CoopUtility", {
                    SkillType: e.target.value === "None" ? "" : e.target.value,
                  })
                }
                className="input-field"
              >
                <option value="None">None</option>
                <option value="Heal">Heal Player</option>
                <option value="RevivePlayer">Revive Player</option>
                <option value="MetalDetector">Metal Detector</option>
                <option value="DungeonSearch">Dungeon Search</option>
                <option value="NightVision">Night Vision</option>
              </select>
            </FieldGroup>
          </div>
        </div>

        {/* --- PERMANENT VFX --- */}
        <div className="border border-border/50 p-4 rounded bg-background/30 shadow-inner flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <SectionLabel className="flex items-center gap-2">
              <CloudLightning className="size-4 text-primary" /> Permanent VFX & Lighting
            </SectionLabel>
            <button
              onClick={() =>
                updateFeature("VFX", [
                  ...vfx,
                  {
                    VarName: `VFX_${vfx.length + 1}`,
                    SystemPackage: "/Game/Pal/Effect/Common/Cooking/NS_CookingFlame",
                    SystemName: "NS_CookingFlame",
                    AttachSocket: "root",
                  },
                ])
              }
              className="flex items-center gap-1.5 px-2 py-1 rounded border border-primary text-primary text-[10px] font-semibold hover:bg-primary/10 cursor-pointer"
            >
              <Plus className="size-3" /> Add Particle
            </button>
          </div>
          <div className="flex flex-col gap-3 border-t border-border/40 pt-3">
            {vfx.length === 0 ? (
              <span className="text-xs text-muted-foreground italic">No particles attached.</span>
            ) : (
              vfx.map((v, i) => (
                <div key={i} className="flex flex-col gap-2 p-2 bg-muted/40 rounded border border-border">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-foreground font-mono">{v.VarName}</span>
                    <button
                      onClick={() => updateFeature("VFX", vfx.filter((_, idx) => idx !== i))}
                      className="text-muted-foreground hover:text-status-error p-1 cursor-pointer"
                    >
                      <Trash2 className="size-3.5" />
                    </button>
                  </div>
                  <SearchableSelect
                    value={v.SystemPackage}
                    onChange={(val) => {
                      const next = [...vfx]
                      next[i].SystemPackage = val
                      next[i].SystemName = val.split("/").pop() || ""
                      updateFeature("VFX", next)
                    }}
                    options={niagaraOptions}
                  />
                  <input
                    value={v.AttachSocket}
                    onChange={(e) => {
                      const next = [...vfx]
                      next[i].AttachSocket = e.target.value
                      updateFeature("VFX", next)
                    }}
                    className="input-field text-xs h-7"
                    placeholder="Socket Name (e.g. eye_l)"
                  />
                </div>
              ))
            )}
            <div className="flex items-center justify-between mt-2 pt-2 border-t border-border/40">
              <span className="text-xs text-foreground font-bold">Bioluminescent Night Light</span>
              <Switch
                checked={light.Enabled}
                onCheckedChange={(c) => updateFeature("TimerPointLight", { Enabled: c })}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
"use client"

import { useState, useMemo, useEffect, useRef } from "react"
import { ChevronDown, SlidersHorizontal, Plus } from "lucide-react"
import { useNav } from "@/lib/nav-context"
import { ModManagerAPI, SystemSettingsAPI, UnrealHealthAPI } from "@/lib/data-service"
import { type ModItem } from "@/lib/mock-data"
import { ModCard } from "@/components/mod-manager/mod-card"
import { cn } from "@/lib/utils"
import { useNotifications } from "./mod-card-expanded/use-notifications"
import { NotificationToast } from "./mod-card-expanded/notification-toast"
import { DiagnosticsModal } from "@/components/common/diagnostics-modal"

// Importing Unreal Wizards
import { UnrealClosedModal } from "@/components/common/unreal-wizards/UnrealClosedModal"
import { RemoteExecDisabledModal } from "@/components/common/unreal-wizards/RemoteExecDisabledModal"

// ── Tag definitions ────────────────────────────────────────────────────────────
type Tag = "unextracted" | "raw" | "source" | "ue_assets" | "altermatic" | "src_changed" | "modified"
const TAG_LABELS: Record<Tag, string> = {
  unextracted: "Unextracted",
  raw: "Raw Unpacked",
  source: "Source Files",
  ue_assets: "UE Assets",
  altermatic: "Altermatic",
  src_changed: "Src Changed",
  modified: "Modified (Unreal)",
}

const BASE_TAGS: Tag[] = ["unextracted", "raw", "source", "ue_assets"]
const MODIFIER_TAGS: Tag[] = ["altermatic", "src_changed", "modified"]

function modMatchesTag(mod: ModItem, tag: Tag): boolean {
  const tagToBadge: Record<Tag, string> = {
    unextracted: "UNEXTRACTED",
    raw:         "RAW",
    source:      "SOURCE",
    ue_assets:   "UE ASSETS",
    modified:    "MODIFIED",
    src_changed: "SRC CHANGED",
    altermatic:  "ALTERMATIC",
  }
  const badgeLabel = tagToBadge[tag]
  return (mod.badges || []).some((b) => b && b[0] && b[0].toUpperCase() === badgeLabel)
}

// ── Preset definitions ────────────────────────────────────────────────────────
type Preset = "workspace" | "unextracted" | "in-progress" | "ready" | "done" | "all"

interface PresetDef {
  label:       string
  description: string
  statusMatch: ((mod: ModItem) => boolean) | null
  activeTags:  Tag[] | null
}

const PRESETS: Record<Preset, PresetDef> = {
  workspace: {
    label: "Live Workspace",
    description: "Mods actively being worked on — have source or UE assets",
    statusMatch: null,
    activeTags:  ["raw", "source", "ue_assets"],
  },
  unextracted: {
    label: "Unextracted",
    description: "Raw imports — no fmodel or blend file yet",
    statusMatch: null,
    activeTags:  ["unextracted"],
  },
  "in-progress": {
    label: "In Progress",
    description: "Have source files but not yet pushed to Unreal",
    statusMatch: null,
    activeTags:  ["raw", "source"],
  },
  ready: {
    label: "Ready",
    description: "In Unreal, source unchanged — ready to cook or pack",
    statusMatch: null,
    activeTags:  ["ue_assets"],
  },
  done: {
    label: "Done",
    description: "Packed and verified",
    statusMatch: (m) => m.pak_status === "Packed",
    activeTags:  null,
  },
  all: {
    label: "All",
    description: "Show every mod regardless of state",
    statusMatch: null,
    activeTags:  null,
  },
}

const PRESET_ORDER: Preset[] = ["workspace", "unextracted", "in-progress", "ready", "done", "all"]

const PRESET_CHIP_CLASS: Record<Preset, string> = {
  workspace:    "border-primary/40 text-primary",
  unextracted:  "border-status-error/40 text-status-error",
  "in-progress":"border-status-warning/40 text-status-warning",
  ready:        "border-primary/40 text-primary",
  done:         "border-status-success/40 text-status-success",
  all:          "border-border text-foreground",
}

// ── Helpers ────────────────────────────────────────────────────────────────────
function resolveActiveTags(preset: Preset, customTags: Tag[] | null): Tag[] | null {
  if (customTags !== null) return customTags
  return PRESETS[preset].activeTags
}

function applyFilters(mods: ModItem[], preset: Preset, customTags: Tag[] | null, search: string): ModItem[] {
  const isCustom = customTags !== null
  const def = PRESETS[preset]
  const tags = resolveActiveTags(preset, customTags) || []
  const q = search.trim().toLowerCase()

  const activeBase = tags.filter(t => BASE_TAGS.includes(t))
  const activeMods = tags.filter(t => MODIFIER_TAGS.includes(t))

  return mods.filter((mod) => {
    if (!isCustom && def.statusMatch && !def.statusMatch(mod)) return false
    
    if (activeBase.length > 0 && !activeBase.some((t) => modMatchesTag(mod, t))) return false
    if (activeMods.length > 0 && !activeMods.every((t) => modMatchesTag(mod, t))) return false
    
    if (q && !mod.name.toLowerCase().includes(q) && !(mod.localized_name?.toLowerCase().includes(q))) return false
    return true
  })
}

// ── Component ──────────────────────────────────────────────────────────────────
export function ModManagerPage() {
  const { search: searchQuery } = useNav()
  const { notifications, showNotification, dismissNotification } = useNotifications()
  const [mods, setMods]               = useState<ModItem[]>([])
  const [expandedId, setExpandedId]   = useState<string | null>(null)
  const [loading, setLoading]         = useState(true)
  const [showMapped, setShowMapped]   = useState(false)
  const [activePreset, setActivePreset] = useState<Preset>("workspace")
  const [customTags, setCustomTags]   = useState<Tag[] | null>(null)
  const [advancedOpen, setAdvancedOpen] = useState(false)
  const [diagnosticError, setDiagnosticError] = useState<string | null>(null)
  const [activeUnrealWizard, setActiveUnrealWizard] = useState<"unreal_closed" | "remote_exec_disabled" | null>(null)
  const advancedRef = useRef<HTMLDivElement>(null)

  const effectiveTags = resolveActiveTags(activePreset, customTags)
  const isCustom = customTags !== null

  async function loadMods() {
    try {
      setLoading(true)
      const [data, config] = await Promise.all([
        ModManagerAPI.list(),
        SystemSettingsAPI.getConfig(),
      ])
      setMods(data)
      setShowMapped(config.show_mapped !== false)
    } catch (err) {
      console.error("Failed to load mods:", err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadMods() }, [])

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (advancedRef.current && !advancedRef.current.contains(e.target as Node)) {
        setAdvancedOpen(false)
      }
    }
    if (advancedOpen) document.addEventListener("mousedown", onClickOutside)
    return () => document.removeEventListener("mousedown", onClickOutside)
  }, [advancedOpen])

  function selectPreset(p: Preset) {
    setActivePreset(p)
    setCustomTags(null)
  }

  function toggleCustomTag(tag: Tag) {
    const base = effectiveTags ?? []
    const current = customTags ?? base
    const next = current.includes(tag)
      ? current.filter((t) => t !== tag)
      : [...current, tag]
    setCustomTags(next)
  }

  function resetToPreset() {
    setCustomTags(null)
  }

  // Active Unreal wizards handlers
  async function handleLaunchUnreal() {
    try {
      showNotification("Sending launch command for Unreal Editor... 🦊🚀", "info", "Unreal Editor")
      await UnrealHealthAPI.launchUnreal()
      showNotification("Unreal Editor launch request sent! Please wait for it to boot up.", "success", "Unreal Launching")
    } catch (err: any) {
      console.error("Unreal launch failed:", err)
      setDiagnosticError(String(err.message || err))
    }
  }

  async function handleEnableRemoteExecAndLaunch() {
    try {
      showNotification("Patching DefaultEngine.ini to enable remote Python script execution... ⚙️", "info", "Configuring")
      await SystemSettingsAPI.enableRemoteExec()
      showNotification("Remote Execution successfully enabled! Launching Unreal Editor... 🦊🚀", "success", "Configured")
      await UnrealHealthAPI.launchUnreal()
    } catch (err: any) {
      console.error("Remote exec configure & launch failed:", err)
      setDiagnosticError(String(err.message || err))
    }
  }

  async function handleAction(mod: ModItem, action: string) {
    const isNavigation = ["open_source", "open_ue", "open_pak", "browse_unreal"].includes(action)
    
    if (isNavigation) {
      try {
        const res = await ModManagerAPI.runAction(mod.name, action)
        showNotification(res.message || `Opened folder successfully!`, "success", "Explorer Action")
      } catch (err: any) {
        console.error("Action failed:", err)
        if (err.message === "UNREAL_CLOSED") {
          setActiveUnrealWizard("unreal_closed")
        } else if (err.message === "REMOTE_EXEC_DISABLED") {
          setActiveUnrealWizard("remote_exec_disabled")
        } else {
          setDiagnosticError(String(err.message || err))
        }
      }
      return
    }

    try {
      setLoading(true)
      const res = await ModManagerAPI.runAction(mod.name, action)
      const data = await ModManagerAPI.list()
      setMods(data)
      showNotification(res.message || "Action executed successfully!", "success", "Pipeline Success")
    } catch (err: any) {
      console.error("Action failed:", err)
      if (err.message === "UNREAL_CLOSED") {
        setActiveUnrealWizard("unreal_closed")
      } else if (err.message === "REMOTE_EXEC_DISABLED") {
        setActiveUnrealWizard("remote_exec_disabled")
      } else {
        setDiagnosticError(String(err.message || err))
      }
    } finally {
      setLoading(false)
    }
  }

  const filtered = useMemo(
    () => applyFilters(mods, activePreset, customTags, searchQuery),
    [mods, activePreset, customTags, searchQuery],
  )

  const presetCounts = useMemo(() => {
    const counts: Partial<Record<Preset, number>> = {}
    for (const p of PRESET_ORDER) {
      counts[p] = applyFilters(mods, p, null, "").length
    }
    return counts
  }, [mods])

  return (
    <div className="flex flex-col gap-4">

      {/* ── Filter bar ── */}
      <div className="flex items-center gap-2 flex-wrap">

        {/* Preset chips */}
        {PRESET_ORDER.map((p) => {
          const def = PRESETS[p]
          const isActive = activePreset === p && !isCustom
          const chipClass = PRESET_CHIP_CLASS[p]
          return (
            <button
              key={p}
              title={def.description}
              onClick={() => selectPreset(p)}
              className={cn(
                "flex items-center gap-1.5 px-2.5 py-1 rounded border text-xs font-semibold tracking-wide transition-all",
                chipClass,
                isActive
                  ? "opacity-100 ring-1 ring-current bg-current/10"
                  : "opacity-40 hover:opacity-70 bg-transparent",
              )}
            >
              {def.label}
              <span className="text-[10px] font-bold opacity-70">
                {presetCounts[p] ?? 0}
              </span>
            </button>
          )
        })}

        {/* Divider */}
        <div className="w-px h-4 bg-border mx-1" />

        {/* Advanced / Tags toggle */}
        <div className="relative" ref={advancedRef}>
          <button
            onClick={() => setAdvancedOpen((v) => !v)}
            className={cn(
              "flex items-center gap-1.5 px-2.5 py-1 rounded border text-xs font-medium transition-all",
              isCustom
                ? "border-primary/50 text-primary bg-primary/10"
                : "border-border text-muted-foreground hover:text-foreground hover:border-border/80",
            )}
          >
            <SlidersHorizontal className="size-3" />
            {isCustom ? "Custom" : "Advanced"}
            {isCustom && (
              <span className="text-[10px] bg-primary/20 text-primary rounded px-1">
                {(effectiveTags ?? []).length}
              </span>
            )}
            <ChevronDown className={cn("size-3 transition-transform", advancedOpen && "rotate-180")} />
          </button>

          {/* Dropdown panel */}
          {advancedOpen && (
            <div className="absolute top-full left-0 mt-1.5 z-50 bg-card border border-border rounded-lg shadow-xl p-3 min-w-[220px] flex flex-col gap-3">
              <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-semibold">
                Asset type filter
              </p>
              <div className="flex flex-col gap-1.5">
                {(Object.keys(TAG_LABELS) as Tag[]).map((tag) => {
                  const active = (effectiveTags ?? []).includes(tag)
                  return (
                    <button
                      key={tag}
                      onClick={() => toggleCustomTag(tag)}
                      className={cn(
                        "flex items-center gap-2 px-2.5 py-1.5 rounded border text-xs font-medium transition-all text-left",
                        active
                          ? "border-primary/50 bg-primary/10 text-primary"
                          : "border-border text-muted-foreground hover:text-foreground",
                      )}
                    >
                      <span className={cn(
                        "size-3 rounded-sm border flex items-center justify-center flex-shrink-0",
                        active ? "bg-primary border-primary" : "border-border",
                      )}>
                        {active && (
                          <svg viewBox="0 0 8 8" className="size-2 text-primary-foreground" fill="currentColor">
                            <path d="M1 4l2 2 4-4" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round"/>
                          </svg>
                        )}
                      </span>
                      {TAG_LABELS[tag]}
                    </button>
                  )
                })}
              </div>
              {isCustom && (
                <button
                  onClick={() => { resetToPreset(); setAdvancedOpen(false) }}
                  className="text-[10px] text-muted-foreground hover:text-foreground underline text-left transition-colors"
                >
                  Reset to preset defaults
                </button>
              )}
            </div>
          )}
        </div>

      </div>

      {/* ── Mod list ── */}
      {loading ? (
        <div className="text-muted-foreground text-sm text-center py-12">Loading...</div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center border border-dashed border-border rounded-xl p-12 text-center bg-muted/10 gap-4">
          <p className="text-muted-foreground text-sm max-w-sm leading-relaxed">
            {activePreset === "workspace" && !isCustom
              ? "No active development workspace mods found yet! Your workspace is clean and ready."
              : "No mods match the current filter criteria."}
          </p>
          {activePreset === "workspace" && !isCustom && (
            <button
              onClick={() => selectPreset("unextracted")}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 shadow transition-colors"
            >
              <Plus className="size-3.5" />
              Add New Pal
            </button>
          )}
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {filtered.map((mod) => {
            const itemKey = mod.id || mod.name
            return (
              <ModCard
                key={itemKey}
                mod={mod}
                expanded={expandedId === itemKey}
                onToggle={() => setExpandedId((p) => (p === itemKey ? null : itemKey))}
                onAction={handleAction}
                onRefresh={loadMods}
                showMapped={showMapped}
              />
            )
          })}
        </div>
      )}
      <NotificationToast notifications={notifications} onDismiss={dismissNotification} />

      {/* ── Diagnostics / Self-Healing Smart Modal ── */}
      {diagnosticError && (
        <DiagnosticsModal
          errorText={diagnosticError}
          onClose={() => setDiagnosticError(null)}
        />
      )}

      {/* Sequential Unreal Wizards */}
      <UnrealClosedModal
        isOpen={activeUnrealWizard === "unreal_closed"}
        onClose={() => setActiveUnrealWizard(null)}
        onConfirm={handleLaunchUnreal}
      />

      <RemoteExecDisabledModal
        isOpen={activeUnrealWizard === "remote_exec_disabled"}
        onClose={() => setActiveUnrealWizard(null)}
        onConfirm={handleEnableRemoteExecAndLaunch}
      />
    </div>
  )
}

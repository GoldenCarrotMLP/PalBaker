"use client"

import { useState, useMemo, useEffect, useRef } from "react"
import { ChevronDown, SlidersHorizontal } from "lucide-react"
import { useNav } from "@/lib/nav-context"
import { ModManagerAPI, SystemSettingsAPI, UnrealHealthAPI } from "@/lib/data-service"
import { type ModItem } from "@/lib/mock-data"
import { ModCard } from "@/components/mod-manager/mod-card"
import { cn } from "@/lib/utils"
import { useNotifications } from "./mod-card-expanded/use-notifications"
import { NotificationToast } from "./mod-card-expanded/notification-toast"

// ── Tag definitions ────────────────────────────────────────────────────────────
// A "tag" is a boolean predicate on a ModItem.
type Tag = "unextracted" | "raw" | "source" | "ue" | "altermatic" | "source_changed" | "modified"

const TAG_LABELS: Record<Tag, string> = {
  unextracted: "Unextracted",
  raw: "Raw Unpacked",
  source: ".blend",
  ue: "UE Assets",
  altermatic: "Altermatic",
  source_changed: ".blend Changed",
  modified: "Modified (Unreal)",
}

function modMatchesTag(mod: ModItem, tag: Tag): boolean {
  if (tag === "unextracted")    return !mod.has_fmodel
  if (tag === "raw")            return mod.has_fmodel && !mod.has_blend
  if (tag === "source")         return mod.has_blend
  if (tag === "ue")             return mod.has_ue
  if (tag === "altermatic")     return mod.is_altermatic_active
  if (tag === "source_changed") return mod.source_modified
  if (tag === "modified")       return !!mod.ue_modified
  return false
}

// ── Preset definitions ────────────────────────────────────────────────────────
// Each preset maps to a pak_status filter + an optional tag filter set.
// activeTags: null = no tag filtering (show all). Set = must match at least one.
type Preset = "workspace" | "unextracted" | "in-progress" | "ready" | "done" | "all"

interface PresetDef {
  label:       string
  description: string
  statusMatch: ((mod: ModItem) => boolean) | null  // null = no status filter
  activeTags:  Tag[] | null                         // null = no tag filter
}

const PRESETS: Record<Preset, PresetDef> = {
  workspace: {
    label: "Live Workspace",
    description: "Mods actively being worked on — have source or UE assets",
    statusMatch: null,
    activeTags:  ["raw", "source", "ue"],
  },
  unextracted: {
    label: "Unextracted",
    description: "Raw imports — no fmodel or blend file yet",
    statusMatch: (m) => m.pak_status === "Unextracted",
    activeTags:  null,
  },
  "in-progress": {
    label: "In Progress",
    description: "Have source files but not yet pushed to Unreal",
    statusMatch: (m) => m.has_fmodel && !m.has_ue,
    activeTags:  ["raw", "source"],
  },
  ready: {
    label: "Ready",
    description: "In Unreal, source unchanged — ready to cook or pack",
    statusMatch: (m) => m.has_ue && !m.source_modified,
    activeTags:  ["ue"],
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
  // If user has broken out into custom mode, use their tags
  if (customTags !== null) return customTags
  return PRESETS[preset].activeTags
}

function applyFilters(mods: ModItem[], preset: Preset, customTags: Tag[] | null, search: string): ModItem[] {
  const isCustom = customTags !== null
  const def = PRESETS[preset]
  const tags = resolveActiveTags(preset, customTags)
  const q = search.trim().toLowerCase()

  return mods.filter((mod) => {
    if (!isCustom && def.statusMatch && !def.statusMatch(mod)) return false
    if (tags && tags.length > 0 && !tags.some((t) => modMatchesTag(mod, t))) return false
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
  // null = using preset's default tags; Tag[] = user has customised
  const [customTags, setCustomTags]   = useState<Tag[] | null>(null)
  const [advancedOpen, setAdvancedOpen] = useState(false)
  const [unrealModalOpen, setUnrealModalOpen] = useState(false)
  const advancedRef = useRef<HTMLDivElement>(null)

  async function handleLaunchUnreal() {
    setUnrealModalOpen(false)
    try {
      showNotification("Triggering Unreal Editor launch, please wait...", "info", "Launch Unreal")
      const res = await UnrealHealthAPI.launchUnreal()
      if (res.status === "success") {
        showNotification("Unreal Editor launch successfully triggered!", "success", "Launch Unreal")
      } else {
        showNotification(res.message || "Failed to launch Unreal Editor.", "error", "Launch Unreal")
      }
    } catch (err: any) {
      showNotification(String(err), "error", "Launch Unreal")
    }
  }

  // Derived: the effective active tags for display in the advanced panel
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

  // Close advanced panel on outside click
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
    setCustomTags(null) // reset any custom tag overrides
  }

  function toggleCustomTag(tag: Tag) {
    // First toggle: snapshot the preset's default tags into customTags
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

  async function handleAction(mod: ModItem, action: string) {
    const isNavigation = ["open_source", "open_ue", "open_pak", "browse_unreal"].includes(action)
    
    if (isNavigation) {
      try {
        const res = await ModManagerAPI.runAction(mod.name, action)
        showNotification(res.message || `Opened folder successfully!`, "success", "Explorer Action")
      } catch (err: any) {
        let isUnrealClosed = false
        try {
          const parsed = JSON.parse(String(err))
          if (parsed.error_code === "UNREAL_CLOSED") {
            isUnrealClosed = true
          }
        } catch (e) {}

        if (isUnrealClosed) {
          console.warn("Navigation failed gracefully: Unreal Editor is closed.")
          setUnrealModalOpen(true)
        } else {
          console.error("Action failed:", err)
          showNotification(err.message || String(err), "error", "Operation Failed")
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
      let isUnrealClosed = false
      try {
        const parsed = JSON.parse(String(err))
        if (parsed.error_code === "UNREAL_CLOSED") {
          isUnrealClosed = true
        }
      } catch (e) {}

      if (isUnrealClosed) {
        console.warn("Action failed gracefully: Unreal Editor is closed.")
        setUnrealModalOpen(true)
      } else {
        console.error("Action failed:", err)
        showNotification(err.message || String(err), "error", "Pipeline Failed")
      }
    } finally {
      setLoading(false)
    }
  }

  const filtered = useMemo(
    () => applyFilters(mods, activePreset, customTags, searchQuery),
    [mods, activePreset, customTags, searchQuery],
  )

  // Count per preset for badge display
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
        <div className="text-muted-foreground text-sm text-center py-12">
          No mods match the current filter.
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

      {/* ── Unreal Closed Modal ── */}
      {unrealModalOpen && (
        <div className="fixed inset-0 z-[150] flex items-center justify-center bg-black/70 backdrop-blur-sm animate-fade-in">
          <div className="bg-background border border-border w-full max-w-md p-6 rounded-lg shadow-2xl flex flex-col gap-4 animate-scale-up">
            <div className="flex items-center gap-3 text-status-warning">
              <span className="text-xl">⚠️</span>
              <h3 className="text-lg font-semibold tracking-wide">Unreal Editor Closed</h3>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Unreal Editor is not running! Would you like to open your project in Unreal Editor now?
            </p>
            <div className="flex justify-end gap-3 mt-2">
              <button
                onClick={() => setUnrealModalOpen(false)}
                className="hover:bg-muted text-muted-foreground font-semibold py-2 px-4 rounded-md transition-colors text-sm"
              >
                Cancel
              </button>
              <button
                onClick={handleLaunchUnreal}
                className="bg-primary/20 hover:bg-primary/30 border border-primary/40 hover:border-primary/60 text-primary font-semibold py-2 px-5 rounded-md transition-colors text-sm"
              >
                Okay, open Unreal!
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

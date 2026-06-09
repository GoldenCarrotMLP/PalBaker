"use client"

import { useState, useMemo, useEffect } from "react"
import { useNav } from "@/lib/nav-context"
import { ModManagerAPI, SystemSettingsAPI } from "@/lib/data-service"
import { mockModList, type ModItem, type PakStatus } from "@/lib/mock-data"
import { ModCard } from "@/components/mod-manager/mod-card"
import { cn } from "@/lib/utils"

// Filter chips mirror the status states from mod_card.py
type FilterStatus = "All" | PakStatus

const STATUS_FILTERS: { status: FilterStatus; label: string; chipClass: string }[] = [
  { status: "All",          label: "All",          chipClass: "bg-muted text-foreground border-border"                                    },
  { status: "Unextracted",  label: "Unextracted",  chipClass: "bg-status-error/15  text-status-error   border-status-error/40"             },
  { status: "Unpacked",     label: "Unpacked",     chipClass: "bg-muted            text-muted-foreground border-border"                   },
  { status: "Outdated",     label: "Outdated",     chipClass: "bg-primary/10       text-primary         border-primary/30"                 },
  { status: "Packed",       label: "Packed",       chipClass: "bg-status-success/10 text-status-success  border-status-success/30"         },
  { status: "SrcChanged",   label: "Src Changed",  chipClass: "bg-status-warning/15 text-status-warning  border-status-warning/40"         },
]

const TAG_FILTERS = [
  { tag: "UNEXTRACTED", label: "UNEXTRACTED", activeClass: "bg-red-950/40 border-red-800/40 text-red-300" },
  { tag: "RAW",         label: "RAW",         activeClass: "bg-neutral-800 border-neutral-700 text-neutral-300" },
  { tag: "SOURCE",      label: "SOURCE",      activeClass: "bg-blue-950/40 border-blue-800/40 text-blue-300" },
  { tag: "UE ASSETS",   label: "UE ASSETS",   activeClass: "bg-amber-950/40 border-amber-800/40 text-amber-300" },
  { tag: "MODIFIED",    label: "MODIFIED",    activeClass: "bg-red-950/40 border-red-800/40 text-red-400" },
  { tag: "SRC CHANGED", label: "SRC CHANGED", activeClass: "bg-blue-950/50 border-blue-800/40 text-blue-400" },
  { tag: "ALTERMATIC",  label: "ALTERMATIC",  activeClass: "bg-teal-950/40 border-teal-800/40 text-teal-300" },
]

function StatusFilterChip({
  label,
  chipClass,
  active,
  count,
  onClick,
}: {
  label: string
  chipClass: string
  active: boolean
  count: number
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-1.5 px-2.5 py-1 rounded border text-xs font-semibold tracking-wide transition-all cursor-pointer",
        chipClass,
        active ? "opacity-100 ring-1 ring-current" : "opacity-50 hover:opacity-80",
      )}
    >
      {label}
      <span className={cn(
        "text-[10px] font-bold px-1 py-0.5 rounded",
        active ? "bg-current/20" : "bg-current/10",
      )}>
        {count}
      </span>
    </button>
  )
}

export function ModManagerPage() {
  const { search: searchQuery } = useNav()
  const [mods, setMods] = useState<ModItem[]>([])
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [activeFilter, setActiveFilter] = useState<FilterStatus>("All")
  const [selectedTags, setSelectedTags] = useState<string[]>(["SOURCE", "UE ASSETS"])
  const [loading, setLoading] = useState(true)
  const [showMapped, setShowMapped] = useState(false)

  async function loadMods() {
    try {
      setLoading(true)
      const data = await ModManagerAPI.list()
      setMods(data)

      const config = await SystemSettingsAPI.getConfig()
      setShowMapped(config.show_mapped !== false)
    } catch (err) {
      console.error("Failed to load mods:", err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadMods()
  }, [])

  function toggleExpand(id: string) {
    setExpandedId((prev) => (prev === id ? null : id))
  }

  async function handleAction(mod: ModItem, action: string) {
    try {
      setLoading(true)
      const res = await ModManagerAPI.runAction(mod.name, action)
      const data = await ModManagerAPI.list()
      setMods(data)
      alert(res.message || res.status || "Action executed successfully!")
    } catch (err) {
      console.error("Action failed:", err)
      alert(`Action failed: ${err}`)
    } finally {
      setLoading(false)
    }
  }

  // Count per status for filter chips
  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = { All: mods.length }
    for (const mod of mods) {
      counts[mod.pak_status] = (counts[mod.pak_status] ?? 0) + 1
    }
    return counts
  }, [mods])

  // Apply both search, status and tags filter
  const filtered = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()
    return mods.filter((mod) => {
      const matchesStatus = activeFilter === "All" || mod.pak_status === activeFilter
      const matchesSearch = !q || 
        mod.name.toLowerCase().includes(q) || 
        (mod.localized_name && mod.localized_name.toLowerCase().includes(q))
      
      // OR intersection match for selected tags
      let matchesTags = true
      if (selectedTags.length > 0) {
        const modBadgeKeys = (mod.badges || []).map((b) => b.text.toUpperCase())
        matchesTags = selectedTags.some((tag) => modBadgeKeys.includes(tag.toUpperCase()))
      }

      return matchesStatus && matchesSearch && matchesTags
    })
  }, [mods, activeFilter, searchQuery, selectedTags])

  return (
    <div className="flex flex-col gap-4">
      
      {/* ── Status Filters Row ── */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mr-1">Status:</span>
        {STATUS_FILTERS.map(({ status, label, chipClass }) => (
          <StatusFilterChip
            key={status}
            label={label}
            chipClass={chipClass}
            active={activeFilter === status}
            count={statusCounts[status] ?? 0}
            onClick={() => setActiveFilter(status)}
          />
        ))}
      </div>

      {/* ── Tag/Badge Filters Row ── */}
      <div className="flex items-center gap-2 flex-wrap border-t border-border/20 pt-2.5">
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mr-1">Tags:</span>
        {TAG_FILTERS.map(({ tag, label, activeClass }) => {
          const isActive = selectedTags.includes(tag)
          return (
            <button
              key={tag}
              onClick={() => {
                setSelectedTags((prev) => {
                  if (prev.includes(tag)) {
                    return prev.filter((t) => t !== tag)
                  } else {
                    return [...prev, tag]
                  }
                })
              }}
              className={cn(
                "px-2.5 py-1 rounded-full border text-[10px] font-bold tracking-wider transition-all cursor-pointer",
                isActive 
                  ? `${activeClass} shadow-sm border-current` 
                  : "bg-muted/40 border-border text-muted-foreground hover:bg-muted/70 hover:text-foreground"
              )}
            >
              {label}
            </button>
          )
        })}
        {selectedTags.length > 0 && (
          <button
            onClick={() => setSelectedTags([])}
            className="text-[10px] font-semibold text-primary hover:underline ml-2 cursor-pointer"
          >
            Clear Tags
          </button>
        )}
      </div>

      {/* Mod list */}
      {filtered.length === 0 ? (
        <div className="text-muted-foreground text-sm text-center py-16 flex flex-col items-center justify-center gap-4 border border-dashed border-border rounded-lg bg-muted/5">
          <span>No mods match the active filter criteria.</span>
          {selectedTags.includes("SOURCE") && selectedTags.includes("UE ASSETS") && (
            <button
              onClick={() => setSelectedTags(["UNEXTRACTED"])}
              className="inline-flex h-9 items-center justify-center rounded bg-primary text-primary-foreground px-4 text-sm font-bold hover:bg-primary/90 transition-colors shadow cursor-pointer uppercase tracking-wider"
            >
              Add New Pal
            </button>
          )}
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {filtered.map((mod) => {
            const itemKey = mod.id || mod.name;
            return (
              <ModCard
                key={itemKey}
                mod={mod}
                expanded={expandedId === itemKey}
                onToggle={() => toggleExpand(itemKey)}
                onAction={handleAction}
                onRefresh={loadMods}
                showMapped={showMapped}
              />
            );
          })}
        </div>
      )}
    </div>
  )
}

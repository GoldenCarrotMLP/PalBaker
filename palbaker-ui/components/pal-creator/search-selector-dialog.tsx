"use client"

import { useState, useRef, useEffect } from "react"
import { Search, X } from "lucide-react"
import { type ActiveSkill } from "@/lib/mock-data"
import { Checkbox } from "@/components/ui/checkbox"

interface Props {
  title: string
  dataset: Record<string, ActiveSkill | string>
  palElements?: string[]
  onSelect: (id: string, label: string) => void
  onClose: () => void
}

const MAX_SHOWN = 35

export function SearchSelectorDialog({ title, dataset, palElements, onSelect, onClose }: Props) {
  const [query,          setQuery]          = useState("")
  const [filterElement,  setFilterElement]  = useState("All")
  const [filterCategory, setFilterCategory] = useState("All")
  const [palOnly,        setPalOnly]        = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => { inputRef.current?.focus() }, [])

  const firstVal      = Object.values(dataset)[0]
  const isSkillDataset = !!(firstVal && typeof firstVal === "object" && "element" in firstVal)

  const allElements   = isSkillDataset
    ? [...new Set((Object.values(dataset) as ActiveSkill[]).map((v) => v.element))]
    : []
  const allCategories = isSkillDataset
    ? [...new Set((Object.values(dataset) as ActiveSkill[]).map((v) => v.category))]
    : []

  const filtered = Object.entries(dataset).filter(([label, val]) => {
    if (isSkillDataset) {
      const skill = val as ActiveSkill
      if (palOnly && palElements?.length && !palElements.includes(skill.element)) return false
      if (filterElement  !== "All" && skill.element  !== filterElement)  return false
      if (filterCategory !== "All" && skill.category !== filterCategory) return false
    }
    if (query) {
      const q = query.toLowerCase()
      return label.toLowerCase().includes(q) || String(val).toLowerCase().includes(q)
    }
    return true
  })

  const shown = filtered.slice(0, MAX_SHOWN)
  const extra = filtered.length - MAX_SHOWN

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-card border border-border rounded-lg shadow-2xl w-[420px] max-h-[85vh] flex flex-col">

        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <span className="text-foreground font-semibold text-sm">{title}</span>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors cursor-pointer">
            <X className="size-4" />
          </button>
        </div>

        {/* Search input */}
        <div className="px-4 pt-3 pb-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={`Search ${title}...`}
              className="w-full bg-muted/60 border border-border rounded pl-8 pr-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
        </div>

        {/* Pal-element filter checkbox */}
        {isSkillDataset && palElements && palElements.length > 0 && (
          <label className="flex items-center gap-2 px-4 pb-2 cursor-pointer">
            <Checkbox
              checked={palOnly}
              onCheckedChange={(c) => setPalOnly(!!c)}
              className="border-border data-[state=checked]:bg-primary data-[state=checked]:border-primary"
            />
            <span className="text-xs text-muted-foreground">
              Match Pal Elements ({palElements.join(", ")})
            </span>
          </label>
        )}

        {/* Element + Category dropdowns */}
        {isSkillDataset && (
          <div className="flex gap-2 px-4 pb-3">
            <select
              value={filterElement}
              onChange={(e) => setFilterElement(e.target.value)}
              className="flex-1 bg-muted/60 border border-border rounded px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="All">All Elements</option>
              {allElements.map((el) => <option key={el} value={el}>{el}</option>)}
            </select>
            <select
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              className="flex-1 bg-muted/60 border border-border rounded px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="All">All Types</option>
              {allCategories.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
        )}

        {/* Results list */}
        <div className="overflow-y-auto flex-1 border-t border-border">
          {shown.length === 0 ? (
            <p className="text-muted-foreground text-xs italic px-4 py-3">No entries match criteria.</p>
          ) : (
            shown.map(([label, val]) => {
              const detail = isSkillDataset
                ? `${(val as ActiveSkill).element} • ${(val as ActiveSkill).category} • PWR ${(val as ActiveSkill).power}`
                : undefined
              return (
                <button
                  key={label}
                  onClick={() => { onSelect(label, label); onClose() }}
                  className="w-full text-left px-4 py-2.5 hover:bg-accent transition-colors border-b border-border/40 last:border-0 cursor-pointer"
                >
                  <div className="text-foreground text-sm font-medium">{label}</div>
                  {detail && <div className="text-muted-foreground text-xs font-mono">{detail}</div>}
                </button>
              )
            })
          )}
          {extra > 0 && (
            <p className="text-primary text-xs italic px-4 py-2">...and {extra} more. Type to filter.</p>
          )}
        </div>

      </div>
    </div>
  )
}

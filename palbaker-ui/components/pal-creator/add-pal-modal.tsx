"use client"

import { useState, useMemo } from "react"
import { X } from "lucide-react"
import { SearchableSelect } from "@/components/ui/searchable-select"

interface Props {
  templates: string[]
  palNames: Record<string, string>
  onConfirm: (id: string, template: string) => void
  onCancel: () => void
}

export function AddPalModal({ templates, palNames, onConfirm, onCancel }: Props) {
  const [palId, setPalId] = useState("")

  // Derived state sync (prevents react-hooks/set-state-in-effect)
  const [prevTemplates, setPrevTemplates] = useState(templates)
  const [template, setTemplate] = useState(() => {
    return templates.includes("Anubis") ? "Anubis" : (templates[0] || "")
  })

  if (templates !== prevTemplates) {
    setPrevTemplates(templates)
    if (!template && templates.length > 0) {
      setTemplate(templates.includes("Anubis") ? "Anubis" : templates[0])
    }
  }

  const selectOptions = useMemo(() => {
    return templates.map((t) => ({
      value: t,
      label: `${palNames[t] || t} (${t})`
    }))
  }, [templates, palNames])

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-fade-in">
      <div className="bg-background border border-border rounded-lg shadow-lg w-full max-w-md flex flex-col p-6 gap-5">
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-lg text-foreground">Instantiate Custom Pal</h3>
          <button onClick={onCancel} className="text-muted-foreground hover:text-foreground cursor-pointer transition-colors">
            <X className="size-5" />
          </button>
        </div>
        
        <p className="text-xs text-muted-foreground leading-relaxed">
          The backend will automatically copy the parent template&apos;s base stats, typing, and learnsets so you don&apos;t have to start from zero!
        </p>

        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold uppercase text-muted-foreground">New Standalone Pal ID</label>
          <input
            autoFocus
            type="text"
            placeholder="e.g. ShadowAnubis"
            value={palId}
            onChange={(e) => setPalId(e.target.value.replace(/[^a-zA-Z0-9_]/g, ''))}
            className="h-9 w-full rounded border border-input bg-transparent px-3 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-primary placeholder:text-muted-foreground/40"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold uppercase text-muted-foreground">Parent Template to Clone</label>
          <SearchableSelect
            value={template}
            onChange={(val) => setTemplate(val)}
            options={selectOptions}
            placeholder={templates.length === 0 ? "Loading templates..." : "Select parent template..."}
            emptyText="No templates found."
            className="w-full"
          />
        </div>

        <div className="flex justify-end gap-3 mt-2">
          <button onClick={onCancel} className="h-9 px-4 rounded text-sm font-semibold border border-input hover:bg-muted/50 cursor-pointer transition-colors">
            Cancel
          </button>
          <button 
            disabled={!palId || !template}
            onClick={() => onConfirm(palId, template)} 
            className="h-9 px-4 rounded text-sm font-semibold bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer transition-colors shadow"
          >
            Create Pal
          </button>
        </div>
      </div>
    </div>
  )
}
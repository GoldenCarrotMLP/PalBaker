"use client"
import { useState, useEffect } from "react"
import { X, ChevronDown } from "lucide-react"

interface Props {
  templates: string[]
  palNames: Record<string, string>
  onConfirm: (id: string, template: string) => void
  onCancel: () => void
}

export function AddPalModal({ templates, palNames, onConfirm, onCancel }: Props) {
  const [palId, setPalId] = useState("")
  const [template, setTemplate] = useState("")

  // Safely initialize the default template selection once the async database cache loads
  useEffect(() => {
    if (templates.length > 0 && !template) {
      const defaultTemplate = templates.includes("Anubis") ? "Anubis" : templates[0]
      setTemplate(defaultTemplate)
    }
  }, [templates, template])

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-background border border-border rounded-lg shadow-lg w-full max-w-md flex flex-col p-6 gap-5">
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-lg text-foreground">Instantiate Custom Pal</h3>
          <button onClick={onCancel} className="text-muted-foreground hover:text-foreground cursor-pointer">
            <X className="size-5" />
          </button>
        </div>
        
        <p className="text-xs text-muted-foreground">
          The backend will automatically copy the parent template's base stats, typing, and learnsets so you don't have to start from zero!
        </p>

        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold uppercase text-muted-foreground">New Standalone Pal ID</label>
          <input
            autoFocus
            type="text"
            placeholder="e.g. ShadowAnubis"
            value={palId}
            onChange={(e) => setPalId(e.target.value.replace(/[^a-zA-Z0-9_]/g, ''))}
            className="h-9 w-full rounded border border-input bg-transparent px-3 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold uppercase text-muted-foreground">Parent Template to Clone</label>
          <div className="relative">
            <select
              value={template}
              onChange={(e) => setTemplate(e.target.value)}
              className="h-9 w-full rounded border border-input bg-transparent px-3 text-sm appearance-none pr-8 cursor-pointer focus:outline-none focus:ring-1 focus:ring-primary"
            >
              {templates.length === 0 ? (
                <option className="bg-background">Loading templates...</option>
              ) : (
                templates.map((t) => {
                  const localized = palNames[t] || t
                  return (
                    <option key={t} value={t} className="bg-background">
                      {localized} ({t})
                    </option>
                  )
                })
              )}
            </select>
            <ChevronDown className="absolute right-3 top-2.5 size-4 text-muted-foreground pointer-events-none" />
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-2">
          <button onClick={onCancel} className="h-9 px-4 rounded text-sm font-semibold border border-input hover:bg-muted/50 cursor-pointer">
            Cancel
          </button>
          <button 
            disabled={!palId || !template}
            onClick={() => onConfirm(palId, template)} 
            className="h-9 px-4 rounded text-sm font-semibold bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 cursor-pointer"
          >
            Create Pal
          </button>
        </div>
      </div>
    </div>
  )
}
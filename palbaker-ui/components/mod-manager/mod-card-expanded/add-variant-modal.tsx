// palbaker-ui/components/mod-manager/mod-card-expanded/add-variant-modal.tsx
"use client"

import { useState } from "react"
import { X, ChevronDown } from "lucide-react"
import { ModManagerAPI } from "@/lib/data-service"

interface Props {
  basePal: string
  modName: string
  localizedName: string
  blendFiles: string[]
  onClose: () => void
  onCreated: () => void
  onNotify: (msg: string, type: "success" | "info" | "error" | "warning", title?: string) => void
}

export function AddVariantModal({ basePal, modName, localizedName, blendFiles, onClose, onCreated, onNotify }: Props) {
  const [label, setLabel]   = useState("")
  const [custom, setCustom] = useState(true)
  const [source, setSource] = useState("base")

  const handleCreate = async () => {
    const labelVal = label.trim()
    if (!labelVal) {
      onNotify("Variant Name/Label is required.", "warning", "Validation")
      return
    }
    try {
      await ModManagerAPI.altermaticAdd(basePal, modName, labelVal, custom, source)
      onNotify(`Successfully created variant: ${labelVal}`, "success")
      onCreated()
      onClose()
    } catch (err) {
      onNotify(`Failed to add variant: ${err}`, "error", "Operation Failed")
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-background border border-border rounded-lg shadow-lg w-full max-w-md flex flex-col p-6 gap-4">
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-lg text-foreground">Add Variant to {localizedName || modName}</h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground cursor-pointer">
            <X className="size-5" />
          </button>
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-xs text-muted-foreground font-semibold uppercase">New Variant Name/Label</label>
          <input type="text" placeholder="e.g., Bikini_Gold_Trim" value={label} onChange={(e) => setLabel(e.target.value)} className="flex h-9 w-full rounded border border-input bg-transparent px-3 py-1 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary" />
        </div>

        <div className="flex items-center justify-between border-t border-b border-border py-3">
          <div className="flex flex-col gap-0.5">
            <span className="text-sm font-semibold text-foreground">Custom Model Blend</span>
            <span className="text-xs text-muted-foreground">Create a custom .blend file for this variant?</span>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" checked={custom} onChange={(e) => { setCustom(e.target.checked); if (!e.target.checked) setSource("base") }} className="sr-only peer" />
            <div className="w-9 h-5 bg-muted border border-border peer-checked:bg-primary rounded-full transition-colors" />
            <div className="absolute top-0.5 left-0.5 size-4 bg-white rounded-full shadow transition-transform peer-checked:translate-x-4" />
          </label>
        </div>

        {custom && (
          <div className="flex flex-col gap-1.5">
            <label className="text-xs text-muted-foreground font-semibold uppercase">Clone Skeleton Template From</label>
            <div className="relative">
              <select value={source} onChange={(e) => setSource(e.target.value)} className="flex h-9 w-full rounded border border-input bg-transparent px-3 py-1 text-sm shadow-sm appearance-none pr-8 cursor-pointer focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary">
                <option value="base" className="bg-background">base (Vanilla Canonical Mesh)</option>
                {blendFiles.map((file) => (
                  <option key={file} value={file} className="bg-background">
                    Variant: {file.startsWith(`${modName}_`) ? file.slice(modName.length + 1) : file}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-2.5 top-2.5 size-4 text-muted-foreground pointer-events-none" />
            </div>
          </div>
        )}

        <div className="flex justify-end gap-3 mt-2">
          <button onClick={onClose} className="inline-flex h-9 items-center justify-center rounded px-4 text-sm font-semibold border border-input bg-transparent hover:bg-muted/50 transition-colors cursor-pointer">Cancel</button>
          <button onClick={handleCreate} className="inline-flex h-9 items-center justify-center rounded bg-primary text-primary-foreground px-4 text-sm font-semibold hover:bg-primary/90 transition-colors cursor-pointer shadow">Create</button>
        </div>
      </div>
    </div>
  )
}
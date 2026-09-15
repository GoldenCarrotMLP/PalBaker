// palbaker-ui/components/mod-manager/mod-card-expanded/add-variant-modal.tsx
"use client"

import { useState } from "react"
import { X, ChevronDown } from "lucide-react"
import { ModManagerAPI } from "@/lib/data-service"
import { SearchableSelect } from "@/components/ui/searchable-select"

interface Props {
  basePal: string
  modName: string
  localizedName: string
  blendFiles: string[]
  allBlendFiles?: Record<string, string[]>
  onClose: () => void
  onCreated: () => void
  onNotify: (msg: string, type: "success" | "info" | "error" | "warning", title?: string) => void
}

export function AddVariantModal({ basePal, modName, localizedName, blendFiles, allBlendFiles, onClose, onCreated, onNotify }: Props) {
  const [label, setLabel]         = useState("")
  const [cloneFile, setCloneFile] = useState(false)
  
  const [enableAnimTarget, setEnableAnimTarget] = useState(false)
  const [source, setSource] = useState("base")
  const [crossPalSource, setCrossPalSource] = useState("")

  const handleCreate = async () => {
    const labelVal = label.trim()
    if (!labelVal) {
      onNotify("Variant Name/Label is required.", "warning", "Validation")
      return
    }

    let finalSource = source
    let animTarget = ""

    // Auto-resolve properties from global dropdown
    if (enableAnimTarget && crossPalSource) {
      const [targetPal, blendPath] = crossPalSource.split("|||")
      finalSource = blendPath
      animTarget = targetPal
    }

    try {
      await ModManagerAPI.dynamicPalsAdd(basePal, modName, labelVal, cloneFile, finalSource, animTarget)
      onNotify(`Successfully added Dynamic Pal variant: ${labelVal}`, "success")
      onCreated()
      onClose()
    } catch (err) {
      onNotify(`Failed to add variant: ${err}`, "error", "Operation Failed")
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-fade-in">
      <div className="bg-background border border-border rounded-lg shadow-2xl w-full max-w-md flex flex-col p-6 gap-4">
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-lg text-foreground">Add Dynamic Pal Variant</h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground cursor-pointer">
            <X className="size-5" />
          </button>
        </div>

        {/* 1. Variant Label */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs text-muted-foreground font-semibold uppercase">Variant Label / Name</label>
          <input 
            type="text" 
            placeholder="e.g., Bikini_Gold_Trim, Winter_Coat" 
            value={label} 
            onChange={(e) => setLabel(e.target.value)} 
            className="flex h-9 w-full rounded border border-input bg-transparent px-3 py-1 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary" 
            autoFocus
          />
        </div>

        {/* --- ANIM TARGET TOGGLE --- */}
        <div className="flex items-center justify-between border-t border-border pt-3">
          <div className="flex flex-col gap-0.5 pr-4">
            <span className="text-xs font-bold text-foreground">Global Mesh Select (AnimTarget)</span>
            <span className="text-[10px] text-muted-foreground">
              Select a model from ANY Pal folder to borrow its mesh and animations.
            </span>
          </div>
          <label className="relative inline-flex items-center cursor-pointer shrink-0">
            <input type="checkbox" checked={enableAnimTarget} onChange={(e) => setEnableAnimTarget(e.target.checked)} className="sr-only peer" />
            <div className="w-8 h-4.5 bg-muted border border-border peer-checked:bg-yellow-600 rounded-full transition-colors" />
            <div className="absolute top-0.5 left-0.5 size-3.5 bg-white rounded-full shadow transition-transform peer-checked:translate-x-3.5" />
          </label>
        </div>

        {/* --- DYNAMIC SELECTOR --- */}
        <div className="flex flex-col gap-1.5 pb-2 border-b border-border">
          <div className="relative">
            {enableAnimTarget ? (
              <SearchableSelect
                value={crossPalSource}
                onChange={(val) => setCrossPalSource(val)}
                options={allBlendFiles 
                  ? Object.entries(allBlendFiles).flatMap(([palKey, files]) => 
                      files.map(f => ({
                        value: `${palKey}|||${f}`,
                        label: `[${palKey}] ${f}`
                      }))
                    )
                  : []
                }
                placeholder="-- Search any Pal .blend --"
              />
            ) : (
              <>
                <select value={source} onChange={(e) => setSource(e.target.value)} className="flex h-9 w-full rounded border border-input bg-transparent px-3 py-1 text-sm shadow-sm appearance-none pr-8 cursor-pointer focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary">
                  <option value="base" className="bg-background">base (Vanilla Canonical Mesh)</option>
                  {blendFiles.map((file) => (
                    <option key={file} value={file} className="bg-background">
                      {file.startsWith(`${modName}_`) ? file.slice(modName.length + 1) : file} ({file})
                    </option>
                  ))}
                </select>
                <ChevronDown className="absolute right-2.5 top-2.5 size-4 text-muted-foreground pointer-events-none" />
              </>
            )}
          </div>
        </div>

        {/* Optional Clone Checkbox */}
        <div className="flex items-center justify-between border-b border-border pb-3">
          <div className="flex flex-col gap-0.5 pr-4">
            <span className="text-xs font-semibold text-foreground">Duplicate into new .blend file</span>
            <span className="text-[10px] text-muted-foreground">
              Only enable this if you need a brand-new .blend file to sculpt custom 3D geometry in Blender.
            </span>
          </div>
          <label className="relative inline-flex items-center cursor-pointer shrink-0">
            <input 
              type="checkbox" 
              checked={cloneFile} 
              onChange={(e) => setCloneFile(e.target.checked)} 
              className="sr-only peer" 
            />
            <div className="w-8 h-4.5 bg-muted border border-border peer-checked:bg-primary rounded-full transition-colors" />
            <div className="absolute top-0.5 left-0.5 size-3.5 bg-white rounded-full shadow transition-transform peer-checked:translate-x-3.5" />
          </label>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end gap-3 mt-1">
          <button onClick={onClose} className="inline-flex h-9 items-center justify-center rounded px-4 text-sm font-semibold border border-input bg-transparent hover:bg-muted/50 transition-colors cursor-pointer">
            Cancel
          </button>
          <button onClick={handleCreate} className="inline-flex h-9 items-center justify-center rounded bg-primary text-primary-foreground px-4 text-sm font-semibold hover:bg-primary/90 transition-colors cursor-pointer shadow">
            Create Variant
          </button>
        </div>
      </div>
    </div>
  )
}
// palbaker-ui/components/mod-manager/mod-card-expanded/selective-push-panel.tsx
"use client"

import { useState } from "react"
import { type ModItem } from "@/lib/mock-data"
import { ModManagerAPI } from "@/lib/data-service"
import { Sparkles, Image, Workflow } from "lucide-react"

interface Props {
  mod: ModItem
  onRefresh?: () => void
  onNotify: (msg: string, type: "success" | "info" | "error" | "warning", title?: string) => void
  onUpdateMod: (modKey: string, patch: Partial<ModItem>) => void
}

export function SelectivePushPanel({
  mod,
  onRefresh, // <-- Destructured here!
  onNotify,
  onUpdateMod,
}: Props) {
  const [pushMaterials, setPushMaterials] = useState(mod.push_materials !== false)
  const [pushTextures, setPushTextures] = useState(mod.push_textures !== false)
  const [pushAnimBP, setPushAnimBP] = useState(mod.push_animbp !== false)

  const handleToggle = async (key: "materials" | "textures" | "animbp", val: boolean) => {
    // 1. Instant local UI update
    if (key === "materials") setPushMaterials(val)
    if (key === "textures") setPushTextures(val)
    if (key === "animbp") setPushAnimBP(val)

    const patchKey = `push_${key}` as keyof ModItem
    onUpdateMod(mod.id || mod.name, { [patchKey]: val })

    // 2. Persist in background
    try {
      await ModManagerAPI.setModPushSetting(mod.base_pal, mod.name, key, val)
      onNotify(`Push ${key} ${val ? "enabled" : "disabled"}.`, "info")
    } catch (err) {
      onUpdateMod(mod.id || mod.name, { [patchKey]: !val })
      onNotify(`Failed to update ${key} setting: ${err}`, "error", "Setting Error")
      onRefresh?.()
    }
  }

  return (
    <div className="flex flex-col gap-2.5">
      <span className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">
        Selective Push
      </span>

      <div className="grid grid-cols-3 gap-2">
        {/* Materials */}
        <label className="flex items-center justify-between gap-2 p-2 rounded border border-border bg-muted/30 cursor-pointer hover:bg-muted/50 transition-colors">
          <div className="flex items-center gap-1.5 min-w-0">
            <Sparkles className="size-3.5 text-primary shrink-0" />
            <span className="text-xs font-medium text-foreground truncate">Materials</span>
          </div>
          <div className="relative inline-flex items-center shrink-0">
            <input
              type="checkbox"
              checked={pushMaterials}
              onChange={(e) => handleToggle("materials", e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-7 h-4 bg-muted border border-border peer-checked:bg-primary rounded-full transition-colors" />
            <div className="absolute top-0.5 left-0.5 size-3 bg-white rounded-full shadow transition-transform peer-checked:translate-x-3" />
          </div>
        </label>

        {/* Textures */}
        <label className="flex items-center justify-between gap-2 p-2 rounded border border-border bg-muted/30 cursor-pointer hover:bg-muted/50 transition-colors">
          <div className="flex items-center gap-1.5 min-w-0">
            <Image className="size-3.5 text-primary shrink-0" />
            <span className="text-xs font-medium text-foreground truncate">Textures</span>
          </div>
          <div className="relative inline-flex items-center shrink-0">
            <input
              type="checkbox"
              checked={pushTextures}
              onChange={(e) => handleToggle("textures", e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-7 h-4 bg-muted border border-border peer-checked:bg-primary rounded-full transition-colors" />
            <div className="absolute top-0.5 left-0.5 size-3 bg-white rounded-full shadow transition-transform peer-checked:translate-x-3" />
          </div>
        </label>

        {/* AnimBP */}
        <label className="flex items-center justify-between gap-2 p-2 rounded border border-border bg-muted/30 cursor-pointer hover:bg-muted/50 transition-colors">
          <div className="flex items-center gap-1.5 min-w-0">
            <Workflow className="size-3.5 text-primary shrink-0" />
            <span className="text-xs font-medium text-foreground truncate">AnimBP</span>
          </div>
          <div className="relative inline-flex items-center shrink-0">
            <input
              type="checkbox"
              checked={pushAnimBP}
              onChange={(e) => handleToggle("animbp", e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-7 h-4 bg-muted border border-border peer-checked:bg-primary rounded-full transition-colors" />
            <div className="absolute top-0.5 left-0.5 size-3 bg-white rounded-full shadow transition-transform peer-checked:translate-x-3" />
          </div>
        </label>
      </div>
    </div>
  )
}
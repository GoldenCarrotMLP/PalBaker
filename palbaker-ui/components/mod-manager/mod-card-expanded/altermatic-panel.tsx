"use client"

import { Plus } from "lucide-react"
import { type ModItem } from "@/lib/mock-data"
import { ModManagerAPI } from "@/lib/data-service"
import { VariantChip } from "./variant-chip"

interface Props {
  mod: ModItem
  enabled: boolean
  onToggle: (val: boolean) => void
  onOpenAdd: () => void
  onOpenEdit: (variant: ModItem["altermatic_variants"][number], index: number) => void
  onNotify: (msg: string, type: "success" | "info" | "error" | "warning", title?: string) => void
  onRefresh: () => void
}

export function AltermaticPanel({ mod, enabled, onToggle, onOpenAdd, onOpenEdit, onNotify, onRefresh }: Props) {
  const handleToggle = async (val: boolean) => {
    try {
      await ModManagerAPI.altermaticToggle(mod.name, val)
      onToggle(val)
      onNotify(`Altermatic framework ${val ? "enabled" : "disabled"}.`, "success")
      onRefresh()
    } catch (err) {
      onNotify(`Failed to toggle Altermatic: ${err}`, "error", "Operation Failed")
    }
  }

  return (
    <div className="flex flex-col gap-2 min-w-[220px] shrink-0">
      <div className="flex items-center justify-between gap-3">
        <span className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">
          Altermatic Variants
        </span>
        <label className="flex items-center gap-1.5 cursor-pointer shrink-0">
          <span className="text-xs text-muted-foreground font-mono">ENABLE</span>
          <div className="relative w-9 h-5">
            <input
              type="checkbox"
              checked={enabled}
              onChange={(e) => handleToggle(e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-9 h-5 bg-muted border border-border peer-checked:bg-primary rounded-full transition-colors" />
            <div className="absolute top-0.5 left-0.5 size-4 bg-white rounded-full shadow transition-transform peer-checked:translate-x-4" />
          </div>
        </label>
      </div>

      {enabled && (
        <div className="flex flex-col gap-2">
          {(mod.altermatic_variants || []).length === 0 ? (
            <p className="text-muted-foreground text-xs italic">No custom variants added yet.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {(mod.altermatic_variants || []).map((v, i) => (
                <VariantChip
                  key={i}
                  variant={v}
                  modName={mod.name}
                  onClick={() => onOpenEdit(v, i)}
                />
              ))}
            </div>
          )}
          <button
            onClick={onOpenAdd}
            className="flex items-center justify-center gap-1.5 border border-dashed border-border rounded px-3 py-2 text-xs text-muted-foreground hover:text-foreground hover:border-primary/50 transition-colors mt-1 cursor-pointer"
          >
            <Plus className="size-3.5" />
            ADD VARIANT
          </button>
        </div>
      )}
    </div>
  )
}

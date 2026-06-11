"use client"

import { Folder } from "lucide-react"
import { cn } from "@/lib/utils"

interface Props {
  label: string
  value: string
  onChange: (v: string) => void
  iconVariant?: "folder" | "file"
  wide?: boolean
  onPick?: () => void
}

export function PathField({ label, value, onChange, wide = false, onPick }: Props) {
  return (
    <div className={cn("flex flex-col gap-1.5", wide && "col-span-2")}>
      <label className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">{label}</label>
      <div className="flex items-center gap-0">
        <input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="flex-1 bg-muted/50 border border-border border-r-0 rounded-l px-3 py-2 text-sm text-foreground font-mono placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
        />
        <button
          onClick={onPick}
          className="px-3 py-2 bg-muted border border-border rounded-r hover:bg-accent transition-colors cursor-pointer"
        >
          <Folder className="size-4 text-muted-foreground" />
        </button>
      </div>
    </div>
  )
}
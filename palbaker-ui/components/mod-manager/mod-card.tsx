// palbaker-ui/components/mod-manager/mod-card.tsx
"use client"

import { useState } from "react"
import { cn } from "@/lib/utils"
import { type ModItem } from "@/lib/mock-data"
import { ModManagerAPI } from "@/lib/data-service"
import { convertFileSrc } from "@tauri-apps/api/core"
import {
  ChevronUp,
  ChevronDown,
  AlertTriangle,
  CheckCircle2,
  Circle,
  MoreVertical,
  Folder,
  FolderOpen,
  MonitorPlay,
} from "lucide-react"
import { ModCardExpanded } from "@/components/mod-manager/mod-card-expanded"
import { ContextMenuPortal, type ContextMenuEntry } from "@/components/ui/context-menu-portal"

interface Props {
  mod: ModItem
  expanded: boolean
  onToggle: () => void
  onAction: (mod: ModItem, action: string) => void
  onRefresh: () => void
  showMapped?: boolean
}

function getPrimaryButton(mod: ModItem): { label: string; actionClass: string; action: string } {
  const hasVariants = !mod.is_variant && mod.physical_variants && mod.physical_variants.length > 0

  // 1. Variant Routing: Variants cannot be extracted, but can have sources generated if they exist in UE
  if (mod.is_variant) {
    if (mod.has_ue && !mod.has_fmodel) {
      return { label: "GENERATE SOURCES", actionClass: "bg-primary hover:bg-primary/80 text-primary-foreground", action: "decompile" }
    }
  } else {
    // 2. Base Pal Routing: If it has physical variant subfolders, treat it as a ready workspace compiler
    if (hasVariants) {
      return { label: "RECURSIVE COOK & PACK", actionClass: "bg-status-success hover:bg-status-success/80 text-white", action: "cook" }
    }
    // Unextracted base game Pals must be extracted
    if (!mod.has_fmodel) {
      return { label: "EXTRACT PAL", actionClass: "bg-status-error hover:bg-status-error/80 text-white", action: "extract_pal" }
    }
  }

  // 3. Standard compilation/pipeline choices
  if (mod.has_ue) {
    if (mod.source_modified) {
      return { label: "FULL PIPELINE (PUSH & COOK)", actionClass: "bg-status-warning hover:bg-status-warning/80 text-white", action: "full" }
    }
    return { label: "COOK & PACK", actionClass: "bg-status-success hover:bg-status-success/80 text-white", action: "cook" }
  }
  if (mod.has_blend) {
    return { label: "PUSH TO UNREAL", actionClass: "bg-primary hover:bg-primary/80 text-primary-foreground", action: "push" }
  }
  return { label: "CREATE .BLEND FILE", actionClass: "bg-muted hover:bg-muted/80 text-foreground border border-border", action: "create_blend" }
}

function StatusIcon({ mod }: { mod: ModItem }) {
  if (!mod.has_fmodel) return <AlertTriangle className="size-4 text-status-error shrink-0" />
  if (mod.source_modified) return <AlertTriangle className="size-4 text-status-warning shrink-0" />
  if (mod.has_ue) return <CheckCircle2 className="size-4 text-status-success shrink-0" />
  if (mod.has_blend) return <CheckCircle2 className="size-4 text-primary shrink-0" />
  return <Circle className="size-4 text-muted-foreground shrink-0" />
}

function ModCardIcon({ mod }: { mod: ModItem }) {
  const [failed, setFailed] = useState(false)

  const getStatusDot = () => {
    if (!mod.has_fmodel) return "bg-status-error"
    if (mod.source_modified) return "bg-status-warning"
    if (mod.has_ue) return "bg-status-success"
    if (mod.has_blend) return "bg-primary"
    return "bg-muted-foreground"
  }

  if (mod.has_icon && mod.icon_path && !failed) {
    const isLive = typeof window !== "undefined" && (window as unknown as { __TAURI_INTERNALS__?: unknown }).__TAURI_INTERNALS__ !== undefined
    const src = isLive
      ? convertFileSrc(mod.icon_path)
      : mod.icon_path.startsWith("http") ? mod.icon_path : `https://asset.localhost/${mod.icon_path}`
    return (
      <div className="size-8 rounded border border-border bg-muted/40 flex items-center justify-center shrink-0 overflow-hidden relative">
        <img src={src} alt={mod.name} className="size-full object-cover" onError={() => setFailed(true)} />
        <span className={cn("absolute bottom-0.5 right-0.5 size-2 rounded-full border border-card shadow-sm", getStatusDot())} />
      </div>
    )
  }

  return (
    <div className="size-8 flex items-center justify-center shrink-0">
      <StatusIcon mod={mod} />
    </div>
  )
}

export function ModCard({ mod, expanded, onToggle, onAction, onRefresh, showMapped }: Props) {
  const [menuOpen, setMenuOpen] = useState(false)
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number } | null>(null)
  const primary = getPrimaryButton(mod)

  const handleReplacerChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value
    try {
      await ModManagerAPI.setVanillaReplacer(mod.base_pal, val)
      onRefresh()
    } catch (err) {
      console.error(err)
    }
  }

  const contextItems: ContextMenuEntry[] = [
    {
      label: "Open source files in Explorer",
      icon: <Folder className="size-3.5" />,
      disabled: !mod.has_fmodel,
    },
    {
      label: "Open Unreal assets in Explorer",
      icon: <Folder className="size-3.5" />,
      disabled: !mod.has_ue,
    },
    {
      label: "Open PAK in Explorer",
      icon: <FolderOpen className="size-3.5" />,
      disabled: mod.pak_status !== "Packed",
    },
    { separator: true },
    {
      label: "Show in Unreal Content Browser",
      icon: <MonitorPlay className="size-3.5" />,
      disabled: !mod.has_ue,
    },
  ]

  const contextActionMap: Record<string, string> = {
    "Open source files in Explorer": "open_source",
    "Open Unreal assets in Explorer": "open_ue",
    "Open PAK in Explorer": "open_pak",
    "Show in Unreal Content Browser": "browse_unreal",
  }

  const displayTitle = mod.is_variant ? mod.name : (showMapped ? (mod.localized_name || mod.name) : mod.name)
  const displaySubtitle = mod.is_variant ? mod.base_pal : (showMapped ? mod.name : null)
  const hasVariants = !mod.is_variant && mod.physical_variants && mod.physical_variants.length > 0

  return (
    <>
      <div
        onContextMenu={(e) => {
          e.preventDefault()
          setCtxMenu({ x: e.clientX, y: e.clientY })
        }}
        className={cn(
          "rounded-md border bg-card transition-colors",
          expanded ? "border-border/80" : "border-border",
          mod.source_modified && "border-l-2 border-l-status-warning",
          !mod.has_fmodel && !hasVariants && "border-l-2 border-l-status-error",
          hasVariants && "border-l-2 border-l-status-success",
          mod.has_ue && !mod.source_modified && "border-l-2 border-l-status-success",
        )}
      >
        <div className="flex items-center gap-3 px-4 py-3.5">
          <ModCardIcon mod={mod} />

          <div className="flex-1 min-w-0">
            <div className="font-semibold text-foreground text-sm leading-snug">
              {displayTitle}
            </div>
            <div className="flex items-center gap-2 mt-0.5 flex-wrap">
              {displaySubtitle && (
                <span className="text-muted-foreground text-xs">{displaySubtitle}</span>
              )}
              {mod.badges.map((badge, idx) => {
                const text = badge[0]
                const colorHex = badge[1]
                return (
                  <span
                    key={text || idx}
                    className="text-[10px] font-bold px-1.5 py-0.5 rounded border tracking-wide cursor-default select-none"
                    style={{
                      borderColor: colorHex,
                      color: colorHex,
                      backgroundColor: `${colorHex}1A`,
                    }}
                  >
                    {text}
                  </span>
                )
              })}
            </div>
          </div>

          {!mod.is_variant && mod.physical_variants && mod.physical_variants.length > 0 && (
            <div className="flex flex-col gap-0.5 max-w-[150px] shrink-0 mr-2">
              <span className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground leading-none">Vanilla Replacer</span>
              <select
                value={mod.active_vanilla_replacer || ""}
                onChange={handleReplacerChange}
                className="bg-muted/80 text-foreground border border-border rounded px-2 py-1 text-xs focus:outline-none cursor-pointer w-full"
              >
                <option value="" className="bg-background">Default Vanilla</option>
                {mod.physical_variants.map((varName: string) => (
                  <option key={varName} value={varName} className="bg-background">{varName}</option>
                ))}
              </select>
            </div>
          )}

          <button
            onClick={onToggle}
            disabled={!mod.has_fmodel && !hasVariants}
            className="p-1.5 rounded text-muted-foreground hover:text-foreground hover:bg-accent transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            aria-label={expanded ? "Collapse" : "Expand"}
          >
            {expanded ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
          </button>

          <button
            onClick={() => onAction(mod, primary.action)}
            className={cn(
              "px-3.5 py-1.5 rounded text-xs font-bold tracking-wider uppercase transition-colors whitespace-nowrap shrink-0",
              primary.actionClass,
            )}
          >
            {primary.label}
          </button>

          <div className="relative shrink-0">
            <button
              onClick={() => setMenuOpen((v) => !v)}
              className="p-1.5 rounded text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
              aria-label="More pipeline actions"
            >
              <MoreVertical className="size-4" />
            </button>
            {menuOpen && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
                <div className="absolute right-0 top-full mt-1 z-20 w-64 bg-popover border border-border rounded-md shadow-xl py-1 text-sm">
                  <div className="px-3 py-1.5 text-[10px] font-semibold text-muted-foreground uppercase tracking-widest">
                    Pipeline Actions
                  </div>
                  {[
                    { 
                      label: mod.preserve_materials === false 
                        ? "Push to Unreal (Overwrite)" 
                        : "Push to Unreal (Preserve)", 
                      action: "push",       
                      disabled: !hasVariants && (!mod.has_fmodel || !mod.has_blend) 
                    },
                    { label: "Cook (Compile only)",       action: "cook_only",  disabled: !hasVariants && !mod.has_ue },
                    { label: "Pack (Package only)",       action: "pack_only",  disabled: !hasVariants && !mod.has_ue },
                    { label: "Cook & Pack (Skip Import)", action: "cook",       disabled: !hasVariants && !mod.has_ue },
                    { label: "Push & Cook & Pack",        action: "full",       disabled: !hasVariants && (!mod.has_fmodel || !mod.has_blend) },
                    { label: "Generate Sources",          action: "decompile",  disabled: !mod.has_ue },
                  ].map(({ label, action, disabled }) => (
                    <button
                      key={action}
                      disabled={disabled}
                      onClick={() => { setMenuOpen(false); onAction(mod, action) }}
                      className={cn(
                        "w-full text-left px-4 py-2 transition-colors",
                        disabled ? "text-muted-foreground/40 cursor-not-allowed" : "text-foreground hover:bg-accent",
                      )}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>

        {expanded && <ModCardExpanded mod={mod} onRefresh={onRefresh} />}
      </div>

      {ctxMenu && (
        <ContextMenuPortal
          x={ctxMenu.x}
          y={ctxMenu.y}
          items={contextItems}
          onClose={() => setCtxMenu(null)}
          onSelect={(label) => {
            const action = contextActionMap[label]
            if (action) onAction(mod, action)
          }}
        />
      )}
    </>
  )
}
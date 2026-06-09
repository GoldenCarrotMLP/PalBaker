"use client"

import { useState } from "react"
import { cn } from "@/lib/utils"
import { type ModItem } from "@/lib/mock-data"
import { convertFileSrc } from "@tauri-apps/api/core"
import {
  ChevronUp,
  ChevronDown,
  AlertTriangle,
  CheckCircle2,
  Circle,
  MoreVertical,
  FolderOpen,
  Folder,
} from "lucide-react"
import { ModCardExpanded } from "@/components/mod-manager/mod-card-expanded"

interface Props {
  mod: ModItem
  expanded: boolean
  onToggle: () => void
  onAction: (mod: ModItem, action: string) => void
  onRefresh: () => void
  showMapped?: boolean
}

// Mirrors mod_card.py ModItem.update_primary_button_config()
function getPrimaryButton(mod: ModItem): { label: string; actionClass: string; action: string } {
  if (!mod.has_fmodel) {
    return {
      label: "EXTRACT PAL",
      actionClass: "bg-status-error hover:bg-status-error/80 text-white",
      action: "extract_pal",
    }
  }
  if (mod.has_ue) {
    if (mod.source_modified) {
      return {
        label: "FULL PIPELINE (PUSH & COOK)",
        actionClass: "bg-status-warning hover:bg-status-warning/80 text-white",
        action: "full",
      }
    }
    return {
      label: "COOK & PACK",
      actionClass: "bg-status-success hover:bg-status-success/80 text-white",
      action: "cook",
    }
  }
  if (mod.has_blend) {
    return {
      label: "PUSH TO UNREAL",
      actionClass: "bg-primary hover:bg-primary/80 text-primary-foreground",
      action: "push",
    }
  }
  return {
    label: "CREATE .BLEND FILE",
    actionClass: "bg-muted hover:bg-muted/80 text-foreground border border-border",
    action: "create_blend",
  }
}

// Status dot icon
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
    const isLive = typeof window !== "undefined" && (window as any).__TAURI_INTERNALS__ !== undefined
    const src = isLive
      ? convertFileSrc(mod.icon_path)
      : mod.icon_path.startsWith("http") ? mod.icon_path : `https://asset.localhost/${mod.icon_path}`
      
    return (
      <div className="size-8 rounded border border-border bg-muted/40 flex items-center justify-center shrink-0 overflow-hidden relative">
        <img
          src={src}
          alt={mod.name}
          className="size-full object-cover"
          onError={() => setFailed(true)}
        />
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
  const primary = getPrimaryButton(mod)

  return (
    <div
      className={cn(
        "rounded-md border bg-card transition-colors",
        expanded ? "border-border/80" : "border-border",
        mod.source_modified && "border-l-2 border-l-status-warning",
        !mod.has_fmodel && "border-l-2 border-l-status-error",
        mod.has_ue && !mod.source_modified && "border-l-2 border-l-status-success",
      )}
    >
      {/* Main row */}
      <div className="flex items-center gap-3 px-4 py-3.5">
        <ModCardIcon mod={mod} />

        {/* Name + meta */}
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-foreground text-sm leading-snug">
            {showMapped ? (mod.localized_name || mod.name) : mod.name}
          </div>
          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
            {showMapped && (
              <span className="text-muted-foreground text-xs">
                {mod.name}
              </span>
            )}
            {mod.badges.map((badge, idx) => {
              const text = Array.isArray(badge) ? badge[0] : badge.text;
              const tooltip = Array.isArray(badge) ? "" : badge.tooltip;
              return (
                <span
                  key={text || idx}
                  title={tooltip}
                  className={cn(
                    "text-[10px] font-bold px-1.5 py-0.5 rounded border tracking-wide cursor-default select-none",
                    !Array.isArray(badge) && badge.color,
                  )}
                  style={Array.isArray(badge) && badge[1].startsWith('#') ? {
                    borderColor: badge[1],
                    color: badge[1],
                    backgroundColor: `${badge[1]}1A` // 10% opacity
                  } : undefined}
                >
                  {text}
                </span>
              );
            })}
          </div>
        </div>

        {/* Expand toggle */}
        <button
          onClick={onToggle}
          disabled={!mod.has_fmodel}
          className="p-1.5 rounded text-muted-foreground hover:text-foreground hover:bg-accent transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          aria-label={expanded ? "Collapse" : "Expand"}
        >
          {expanded ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
        </button>

        {/* Primary action button */}
        <button
          onClick={() => onAction(mod, primary.action)}
          className={cn(
            "px-3.5 py-1.5 rounded text-xs font-bold tracking-wider uppercase transition-colors whitespace-nowrap shrink-0",
            primary.actionClass,
          )}
        >
          {primary.label}
        </button>

        {/* Overflow menu — mirrors popup menu in mod_card.py */}
        <div className="relative shrink-0">
          <button
            onClick={() => setMenuOpen((v) => !v)}
            className="p-1.5 rounded text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            aria-label="More actions"
          >
            <MoreVertical className="size-4" />
          </button>
          {menuOpen && (
            <>
              {/* Backdrop */}
              <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
              <div className="absolute right-0 top-full mt-1 z-20 w-52 bg-popover border border-border rounded-md shadow-xl py-1 text-sm">
                {[
                  { label: "Push to Unreal",        action: "push",       disabled: !mod.has_fmodel || !mod.has_blend },
                  { label: "Cook (Compile only)",    action: "cook_only",  disabled: !mod.has_ue },
                  { label: "Pack (Package only)",    action: "pack_only",  disabled: !mod.has_ue },
                  { label: "Cook & Pack (Skip Import)", action: "cook",    disabled: !mod.has_ue },
                  { label: "Push & Cook & Pack",     action: "full",       disabled: !mod.has_fmodel || !mod.has_blend },
                  { label: "Generate Sources",       action: "decompile",  disabled: !mod.has_ue },
                ].map(({ label, action, disabled }) => (
                  <button
                    key={action}
                    disabled={disabled}
                    onClick={() => { setMenuOpen(false); onAction(mod, action) }}
                    className={cn(
                      "w-full text-left px-4 py-2 transition-colors",
                      disabled
                        ? "text-muted-foreground/40 cursor-not-allowed"
                        : "text-foreground hover:bg-accent",
                    )}
                  >
                    {label}
                  </button>
                ))}
                <div className="border-t border-border my-1" />
                {[
                  { label: "Open source in explorer",   action: "open_source", disabled: !mod.has_fmodel },
                  { label: "Open UE assets in explorer", action: "open_ue",    disabled: !mod.has_ue },
                  { label: "Open PAK in explorer",       action: "open_pak",   disabled: mod.pak_status !== "Packed" },
                ].map(({ label, action, disabled }) => (
                  <button
                    key={action}
                    disabled={disabled}
                    onClick={() => { setMenuOpen(false); onAction(mod, action) }}
                    className={cn(
                      "w-full text-left px-4 py-2 transition-colors flex items-center gap-2",
                      disabled
                        ? "text-muted-foreground/40 cursor-not-allowed"
                        : "text-foreground hover:bg-accent",
                    )}
                  >
                    <Folder className="size-3.5 shrink-0" />
                    {label}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Expanded detail panel */}
      {expanded && <ModCardExpanded mod={mod} onRefresh={onRefresh} />}
    </div>
  )
}

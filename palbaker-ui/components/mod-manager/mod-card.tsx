"use client"

import { cn } from "@/lib/utils"
import { type ModItem, type ModStatus } from "@/lib/mock-data"
import { ChevronUp, ChevronDown, AlertTriangle, CheckCircle2, Circle, RefreshCw } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { ModCardExpanded } from "@/components/mod-manager/mod-card-expanded"

interface Props {
  mod: ModItem
  expanded: boolean
  onToggle: () => void
}

const STATUS_CONFIG: Record<
  ModStatus,
  { label: string; className: string; actionLabel: string; actionClass: string; icon: React.ReactNode }
> = {
  OUT_OF_SYNC: {
    label: "OUT OF SYNC",
    className: "border border-status-error text-status-error bg-transparent",
    actionLabel: "EXTRACT PAL",
    actionClass: "bg-status-error hover:bg-status-error/80 text-white",
    icon: <AlertTriangle className="size-4 text-status-warning shrink-0" />,
  },
  IDLE: {
    label: "IDLE",
    className: "border border-muted-foreground text-muted-foreground bg-transparent",
    actionLabel: "CREATE .BLEND FILE",
    actionClass: "bg-muted hover:bg-muted/80 text-foreground",
    icon: <Circle className="size-4 text-muted-foreground shrink-0" />,
  },
  READY: {
    label: "READY",
    className: "border border-primary text-primary bg-transparent",
    actionLabel: "PUSH TO UNREAL",
    actionClass: "bg-primary hover:bg-primary/80 text-primary-foreground",
    icon: <CheckCircle2 className="size-4 text-primary shrink-0" />,
  },
  SUCCESS: {
    label: "SUCCESS",
    className: "border border-status-success text-status-success bg-transparent",
    actionLabel: "COOK & PACK",
    actionClass: "bg-status-success hover:bg-status-success/80 text-white",
    icon: <CheckCircle2 className="size-4 text-status-success shrink-0" />,
  },
  ERROR: {
    label: "ERROR",
    className: "border border-status-error text-status-error bg-transparent",
    actionLabel: "RETRY",
    actionClass: "bg-status-error hover:bg-status-error/80 text-white",
    icon: <AlertTriangle className="size-4 text-status-error shrink-0" />,
  },
}

// Special combined action for OUT_OF_SYNC on .blend
const FULL_PIPELINE_STATUSES = new Set(["OUT_OF_SYNC"])

export function ModCard({ mod, expanded, onToggle }: Props) {
  const config = STATUS_CONFIG[mod.status]
  const isFullPipeline = FULL_PIPELINE_STATUSES.has(mod.status) && mod.source_ext === ".blend"

  return (
    <div className={cn("rounded-md border border-border bg-card transition-all", expanded && "border-border/60")}>
      {/* Header row */}
      <div className="flex items-center gap-4 px-5 py-4">
        <div className="shrink-0">{config.icon}</div>

        {/* Name + meta */}
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-foreground text-sm">{mod.name}</div>
          <div className="text-muted-foreground text-xs mt-0.5">
            Modified {mod.modified} &bull; Source: {mod.source_ext}
          </div>
        </div>

        {/* Status badge */}
        <Badge
          variant="outline"
          className={cn("text-xs font-bold tracking-wide px-2.5 py-0.5 shrink-0", config.className)}
        >
          {config.label}
        </Badge>

        {/* Expand / collapse chevron */}
        <button
          onClick={onToggle}
          className="p-1.5 rounded text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
          aria-label={expanded ? "Collapse" : "Expand"}
        >
          {expanded ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
        </button>

        {/* Primary action */}
        <button
          className={cn(
            "px-4 py-1.5 rounded text-xs font-bold tracking-wider uppercase transition-colors whitespace-nowrap shrink-0",
            isFullPipeline
              ? "bg-status-warning hover:bg-status-warning/80 text-white"
              : config.actionClass
          )}
        >
          {isFullPipeline ? "FULL PIPELINE (PUSH & COOK)" : config.actionLabel}
        </button>
      </div>

      {/* Expanded detail */}
      {expanded && <ModCardExpanded mod={mod} />}
    </div>
  )
}

"use client"

import { Database, CheckCircle } from "lucide-react"
import { cn } from "@/lib/utils"

const PIPELINE_ITEMS = [
  { key: "blender_rpc", label: "BLENDER RPC" },
  { key: "ue_live_link", label: "UE LIVE LINK" },
  { key: "asset_watcher", label: "ASSET WATCHER" },
  { key: "build_queue", label: "BUILD QUEUE" },
] as const

const PIPELINE_COLORS: Record<string, string> = {
  CONNECTED: "text-status-success",
  STANDBY:   "text-status-warning",
  RUNNING:   "text-primary",
  IDLE:      "text-muted-foreground",
}

interface Props {
  envStatus: any
  onRebuildDb: () => void
  onVerify: () => void
}

export function PipelineHealth({ envStatus, onRebuildDb, onVerify }: Props) {
  return (
    <section className="bg-card rounded-md border border-border p-5">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="text-foreground font-bold text-sm uppercase tracking-widest">Pipeline Health Monitor</h2>
          <p className="text-muted-foreground text-xs mt-1">Current connection states and diagnostic tools</p>
        </div>
        <div className="flex gap-2">
          <button onClick={onRebuildDb} className="flex items-center gap-1.5 text-xs text-primary hover:text-primary-foreground hover:bg-primary font-semibold border border-primary/20 rounded px-3 py-1.5 transition-all cursor-pointer">
            <Database className="size-3.5" />
            Rebuild Game Database
          </button>
          <button onClick={onVerify} className="flex items-center gap-1.5 text-xs text-primary hover:text-primary-foreground hover:bg-primary font-semibold border border-primary/20 rounded px-3 py-1.5 transition-all cursor-pointer">
            <CheckCircle className="size-3.5" />
            Verify Environment Prerequisites
          </button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-3">
        {PIPELINE_ITEMS.map(({ key, label }) => {
          const status = (envStatus.pipeline && envStatus.pipeline[key]) || "IDLE"
          return (
            <div key={key} className="bg-muted/40 rounded border border-border p-4">
              <div className="text-muted-foreground text-xs font-semibold uppercase tracking-wider mb-2">{label}</div>
              <div className={cn("text-sm font-bold flex items-center gap-1.5", PIPELINE_COLORS[status] ?? "text-muted-foreground")}>
                <span className={cn("size-1.5 rounded-full inline-block", {
                  "bg-status-success": status === "CONNECTED" || status === "RUNNING",
                  "bg-status-warning": status === "STANDBY",
                  "bg-muted-foreground": status === "IDLE",
                })} />
                {status}
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
"use client"

import { useState } from "react"
import { Terminal, ChevronUp, ChevronDown, X } from "lucide-react"
import { cn } from "@/lib/utils"
import { CONSOLE_LOGS } from "@/lib/mock-data"

const LEVEL_COLORS = {
  SUCCESS: "text-status-success",
  INFO: "text-primary",
  ERROR: "text-status-error",
  WARNING: "text-status-warning",
}

export function BuildConsole() {
  const [expanded, setExpanded] = useState(false)
  const latest = CONSOLE_LOGS[0]

  return (
    <div className="shrink-0 border-t border-border bg-console-bg">
      {/* Collapsed bar (always visible) */}
      <div
        className="flex items-center gap-3 px-4 h-9 cursor-pointer select-none"
        onClick={() => setExpanded((v) => !v)}
      >
        <Terminal className="size-3.5 text-primary shrink-0" />
        <span className="text-primary text-xs font-semibold font-mono uppercase tracking-wider whitespace-nowrap">
          Build Console Terminal
        </span>
        <span className="text-muted-foreground text-xs font-mono shrink-0">•</span>
        <span className="text-muted-foreground text-xs font-mono shrink-0">[{latest.time}]</span>
        <span
          className={cn("text-xs font-mono truncate flex-1", LEVEL_COLORS[latest.level] ?? "text-foreground")}
        >
          {latest.msg}
        </span>
        <div className="flex items-center gap-3 ml-2 shrink-0">
          <span className="text-muted-foreground text-xs font-mono">BUFFER: 4.2KB</span>
          <span className="text-muted-foreground text-xs font-mono">
            STATUS: <span className="text-status-success">READY</span>
          </span>
          {expanded ? (
            <ChevronDown className="size-3.5 text-muted-foreground" />
          ) : (
            <ChevronUp className="size-3.5 text-muted-foreground" />
          )}
        </div>
      </div>

      {/* Expanded log panel */}
      {expanded && (
        <div className="border-t border-border px-4 py-3 max-h-48 overflow-y-auto">
          <div className="flex flex-col gap-1">
            {CONSOLE_LOGS.map((log, i) => (
              <div key={i} className="flex items-start gap-3 text-xs font-mono">
                <span className="text-muted-foreground shrink-0">[{log.time}]</span>
                <span className={cn("shrink-0 font-semibold w-[52px]", LEVEL_COLORS[log.level] ?? "text-foreground")}>
                  {log.level}
                </span>
                <span className="text-foreground/80">{log.msg}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

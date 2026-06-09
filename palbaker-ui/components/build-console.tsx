"use client"

import { useState, useEffect } from "react"
import { Terminal, ChevronUp, ChevronDown, X } from "lucide-react"
import { cn } from "@/lib/utils"
import { CONSOLE_LOGS, type LogEntry } from "@/lib/mock-data"
import { BuildConsoleAPI } from "@/lib/data-service"

const LEVEL_COLORS = {
  SUCCESS: "text-status-success",
  INFO: "text-primary",
  ERROR: "text-status-error",
  WARNING: "text-status-warning",
}

export function BuildConsole() {
  const [expanded, setExpanded] = useState(false)
  const [logs, setLogs] = useState<LogEntry[]>([])

  useEffect(() => {
    const isLive = typeof window !== "undefined" && (window as any).__TAURI_INTERNALS__ !== undefined
    if (isLive) {
      setLogs([
        {
          time: new Date().toLocaleTimeString("en-US", { hour12: false }),
          level: "INFO",
          msg: "Terminal connected to Tauri backend. Listening for subprocess logs...",
        }
      ])
    } else {
      setLogs(CONSOLE_LOGS)
    }
  }, [])

  useEffect(() => {
    const unsubscribe = BuildConsoleAPI.subscribe((newLog) => {
      setLogs((prev) => [newLog, ...prev])
    })
    return () => unsubscribe()
  }, [])

  const latest = logs[0] || { time: "00:00:00", level: "INFO" as const, msg: "Terminal Ready." }

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
          <span className="text-muted-foreground text-xs font-mono">BUFFER: {(JSON.stringify(logs).length / 1024).toFixed(1)}KB</span>
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
            {logs.map((log, i) => (
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

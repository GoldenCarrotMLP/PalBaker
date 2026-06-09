"use client"

import { useState, useEffect } from "react"
import { Terminal, ChevronUp, ChevronDown, Copy, Trash2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { CONSOLE_LOGS, type LogEntry } from "@/lib/mock-data"
import { BuildConsoleAPI, UnrealHealthAPI } from "@/lib/data-service"
import { ContextMenuPortal, type ContextMenuEntry } from "@/components/ui/context-menu-portal"

const LEVEL_COLORS = {
  SUCCESS: "text-status-success",
  INFO: "text-primary",
  ERROR: "text-status-error",
  WARNING: "text-status-warning",
}

export function BuildConsole() {
  const [expanded, setExpanded] = useState(false)
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number } | null>(null)
  
  const [unrealStatus, setUnrealStatus] = useState<string>("READY")
  const [statusColorClass, setStatusColorClass] = useState<string>("text-status-success")
  const [statusTooltip, setStatusTooltip] = useState<string>("Initializing connectivity status...")

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await UnrealHealthAPI.ping()
        if (res.diagnostic_code === "FULLY_CONNECTED") {
          setUnrealStatus("CONNECTED")
          setStatusColorClass("text-status-success")
          setStatusTooltip(res.message || "Connected and ready.")
        } else if (res.diagnostic_code === "MISSING_HELPER_PLUGIN") {
          setUnrealStatus("NO_PLUGIN")
          setStatusColorClass("text-primary")
          setStatusTooltip(res.message || "Remote connection active but plugin is not loaded.")
        } else if (res.diagnostic_code === "NEEDS_RESTART_OR_FIREWALL") {
          setUnrealStatus("BLOCKED")
          setStatusColorClass("text-status-warning animate-pulse")
          setStatusTooltip(res.message || "Unreal config is set to True, but connection timed out.")
        } else if (res.diagnostic_code === "REMOTE_EXEC_DISABLED") {
          setUnrealStatus("REMOTE_OFF")
          setStatusColorClass("text-status-warning")
          setStatusTooltip(res.message || "Unreal is running but Remote Execution is unchecked.")
        } else {
          setUnrealStatus("OFFLINE")
          setStatusColorClass("text-muted-foreground")
          setStatusTooltip(res.message || "Unreal Editor is closed.")
        }
      } catch (err) {
        console.error("Failed to check Unreal health:", err)
        setUnrealStatus("OFFLINE")
        setStatusColorClass("text-muted-foreground")
        setStatusTooltip("Failed to query Unreal connection status.")
      }
    }

    checkHealth()
    const interval = setInterval(checkHealth, 10000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const isLive = typeof window !== "undefined" && (window as any).__TAURI_INTERNALS__ !== undefined
    if (isLive) {
      setLogs([
        {
          time: new Date().toLocaleTimeString("en-US", { hour12: false }),
          level: "INFO",
          msg: "Terminal connected to Tauri backend. Listening for subprocess logs...",
        },
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

  const copyAll = () => {
    const text = logs
      .map((l) => `[${l.time}] ${l.level.padEnd(7)} ${l.msg}`)
      .join("\n")
    navigator.clipboard.writeText(text).catch(() => {})
  }

  const consoleContextItems: ContextMenuEntry[] = [
    { label: "Copy all to clipboard", icon: <Copy className="size-3.5" /> },
    { separator: true },
    { label: "Clear console", icon: <Trash2 className="size-3.5" />, danger: true },
  ]

  const latest = logs[0] || { time: "00:00:00", level: "INFO" as const, msg: "Terminal Ready." }

  return (
    <>
      <div className="shrink-0 border-t border-border bg-console-bg">
        {/* Collapsed bar */}
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
          <span className={cn("text-xs font-mono truncate flex-1", LEVEL_COLORS[latest.level] ?? "text-foreground")}>
            {latest.msg}
          </span>
          <div className="flex items-center gap-3 ml-2 shrink-0">
            <span className="text-muted-foreground text-xs font-mono">
              BUFFER: {(JSON.stringify(logs).length / 1024).toFixed(1)}KB
            </span>
            <span className="text-muted-foreground text-xs font-mono">
              UNREAL: <span className={statusColorClass} title={statusTooltip}>{unrealStatus}</span>
            </span>
            {expanded ? (
              <ChevronDown className="size-3.5 text-muted-foreground" />
            ) : (
              <ChevronUp className="size-3.5 text-muted-foreground" />
            )}
          </div>
        </div>

        {/* Expanded log panel — right-click for Clear / Copy */}
        {expanded && (
          <div
            className="border-t border-border px-4 py-3 max-h-48 overflow-y-auto"
            onContextMenu={(e) => {
              e.preventDefault()
              setCtxMenu({ x: e.clientX, y: e.clientY })
            }}
          >
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

      {ctxMenu && (
        <ContextMenuPortal
          x={ctxMenu.x}
          y={ctxMenu.y}
          items={consoleContextItems}
          onClose={() => setCtxMenu(null)}
          onSelect={(label) => {
            if (label === "Copy all to clipboard") copyAll()
            if (label === "Clear console") setLogs([])
          }}
        />
      )}
    </>
  )
}

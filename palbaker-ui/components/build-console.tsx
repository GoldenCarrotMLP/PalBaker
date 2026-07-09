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
let logIdCounter = 0;

export function BuildConsole() {
  const [expanded, setExpanded] = useState(false)
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number } | null>(null)
  
  // Hydration Mount Guard
  const [mounted, setMounted] = useState(false)
  
  const [unrealStatus, setUnrealStatus] = useState<string>("READY")
  const [statusColorClass, setStatusColorClass] = useState<string>("text-status-success")
  const [statusTooltip, setStatusTooltip] = useState<string>("Initializing connectivity status...")

  const [logs, setLogs] = useState<(LogEntry & { id: number })[]>(() => {
    const isLive = typeof window !== "undefined" && (window as unknown as { __TAURI_INTERNALS__?: unknown }).__TAURI_INTERNALS__ !== undefined
    if (isLive) {
      return [
        {
          id: ++logIdCounter,
          time: new Date().toLocaleTimeString("en-US", { hour12: false }),
          level: "INFO",
          msg: "Terminal connected to Tauri backend. Listening for subprocess logs...",
        },
      ]
    }
    return CONSOLE_LOGS.map(l => ({ ...l, id: ++logIdCounter }))
  })

  useEffect(() => {
    setMounted(true)
    
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
    const unsubscribe = BuildConsoleAPI.subscribe((newLog) => {
      setLogs((prev) => {
        const nextLogs = [{ ...newLog, id: ++logIdCounter }, ...prev]
        return nextLogs.length > 500 ? nextLogs.slice(0, 500) : nextLogs
      })
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

  // Dynamic Parameter Decoupler: Forces default fallbacks during the hydration render pass
  const latestTime = mounted && logs[0] ? logs[0].time : "00:00:00"
  const latestMsg = mounted && logs[0] ? logs[0].msg : "Terminal Ready."
  const latestLevel = mounted && logs[0] ? logs[0].level : ("INFO" as const)

  return (
    <>
      <div
        onContextMenu={(e) => {
          e.preventDefault()
          setCtxMenu({ x: e.clientX, y: e.clientY })
        }}
        className="rounded-md border bg-card transition-colors"
      >
        <div className="flex items-center gap-3 px-4 py-3.5">
          <span className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">Terminal</span>
          <span className="text-muted-foreground text-xs font-mono shrink-0">•</span>
          <span className="text-muted-foreground text-xs font-mono shrink-0">[{latestTime}]</span>
          <span className={cn("text-xs font-mono truncate flex-1", LEVEL_COLORS[latestLevel])}>
            {latestMsg}
          </span>
          <div className="flex items-center gap-3 ml-2 shrink-0">
            <span className="text-muted-foreground text-xs font-mono">
              UNREAL: <span className={statusColorClass} title={statusTooltip}>{unrealStatus}</span>
            </span>
            {expanded ? (
              <ChevronDown className="size-3.5 text-muted-foreground cursor-pointer" onClick={() => setExpanded(false)} />
            ) : (
              <ChevronUp className="size-3.5 text-muted-foreground cursor-pointer" onClick={() => setExpanded(true)} />
            )}
          </div>
        </div>

        {expanded && (
          <div
            className="border-t border-border px-4 py-3 max-h-48 overflow-y-auto"
            onContextMenu={(e) => {
              e.preventDefault()
              setCtxMenu({ x: e.clientX, y: e.clientY })
            }}
          >
            <div className="flex flex-col gap-1">
              {logs.map((log) => (
                <div key={log.id} className="flex items-start gap-3 text-xs font-mono">
                  <span className="text-muted-foreground shrink-0">[{log.time}]</span>
                  <span className={cn("shrink-0 font-semibold w-[52px]", LEVEL_COLORS[log.level])}>
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
"use client"

import React, { useState, useEffect } from "react"
import { useTaskQueue, type QueueTask } from "@/lib/task-queue-context"
import { 
  Layers, 
  ChevronUp, 
  ChevronDown, 
  Loader2, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  Trash2, 
  X,
  AlertTriangle 
} from "lucide-react"
import { cn } from "@/lib/utils"

function formatElapsed(start?: number, end?: number) {
  if (!start) return "0s"
  const finish = end || Date.now()
  const sec = Math.floor((finish - start) / 1000)
  const min = Math.floor(sec / 60)
  const remSec = sec % 60
  if (min > 0) return `${min}m ${remSec}s`
  return `${sec}s`
}

export function ProcessQueueWidget() {
  const { tasks, activeCount, queuedCount, clearCompleted, cancelTask } = useTaskQueue()
  const [expanded, setExpanded] = useState(false)
  const [, setTick] = useState(0)

  // 1-second interval to update live elapsed timers on running tasks
  useEffect(() => {
    if (activeCount === 0) return
    const interval = setInterval(() => setTick((t) => t + 1), 1000)
    return () => clearInterval(interval)
  }, [activeCount])

  const hasTasks = tasks.length > 0
  const runningUnreal = tasks.filter((t) => t.channel === "unreal" && t.status === "running").length
  const runningBlender = tasks.filter((t) => t.channel === "blender" && t.status === "running").length

  return (
    <div className="fixed bottom-14 right-6 z-[80] flex flex-col items-end pointer-events-none select-none">
      
      {/* Expanded Task Queue Drawer Card */}
      {expanded && (
        <div className="pointer-events-auto mb-2 w-96 max-h-[440px] bg-card/95 backdrop-blur-md border border-border shadow-2xl rounded-xl flex flex-col overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-200">
          
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-muted/30 shrink-0">
            <div className="flex items-center gap-2">
              <Layers className="size-4 text-primary" />
              <span className="font-bold text-xs uppercase tracking-wider text-foreground">
                Process Queue
              </span>
              <span className="text-[10px] font-mono text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                {tasks.length} total
              </span>
            </div>

            <div className="flex items-center gap-1">
              <button
                onClick={clearCompleted}
                title="Clear completed and failed tasks"
                className="p-1 hover:bg-muted rounded text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
              >
                <Trash2 className="size-3.5" />
              </button>
              <button
                onClick={() => setExpanded(false)}
                className="p-1 hover:bg-muted rounded text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
              >
                <ChevronDown className="size-4" />
              </button>
            </div>
          </div>

          {/* Channel Concurrency Status Bar */}
          <div className="flex items-center justify-between px-4 py-1.5 bg-muted/10 border-b border-border text-[10px] font-mono text-muted-foreground">
            <div className="flex items-center gap-1.5">
              <span className={cn("size-1.5 rounded-full", runningUnreal > 0 ? "bg-status-warning animate-pulse" : "bg-muted-foreground")} />
              <span>Unreal Channel: <strong className="text-foreground">{runningUnreal}/1</strong></span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className={cn("size-1.5 rounded-full", runningBlender > 0 ? "bg-primary animate-pulse" : "bg-muted-foreground")} />
              <span>Blender Parallel: <strong className="text-foreground">{runningBlender}/3</strong></span>
            </div>
          </div>

          {/* Task List Items */}
          <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2 max-h-[320px]">
            {!hasTasks ? (
              <div className="py-8 text-center text-xs text-muted-foreground italic">
                Queue is empty. Trigger an import, cook, or Blender action to populate! ;3
              </div>
            ) : (
              tasks.slice().reverse().map((task) => {
                const isRunning = task.status === "running"
                const isQueued = task.status === "queued"
                const isCompleted = task.status === "completed"
                const isError = task.status === "error"

                const channelColor =
                  task.channel === "unreal"
                    ? "bg-amber-950/40 text-amber-300 border-amber-800/50"
                    : task.channel === "blender"
                    ? "bg-cyan-950/40 text-cyan-300 border-cyan-800/50"
                    : "bg-purple-950/40 text-purple-300 border-purple-800/50"

                return (
                  <div
                    key={task.id}
                    className={cn(
                      "p-2.5 rounded-lg border bg-background/60 flex flex-col gap-1.5 transition-all text-xs",
                      isRunning && "border-primary/40 shadow-xs",
                      isError && "border-status-error/40 bg-status-error/5"
                    )}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5 min-w-0">
                        <span className={cn("text-[9px] font-mono font-bold px-1 rounded border", channelColor)}>
                          {task.channel.toUpperCase()}
                        </span>
                        <span className="font-bold text-foreground truncate">{task.name}</span>
                      </div>

                      <div className="flex items-center gap-1.5 shrink-0 text-[11px] font-mono">
                        {isRunning && (
                          <span className="flex items-center gap-1 text-primary">
                            <Loader2 className="size-3 animate-spin" />
                            {formatElapsed(task.startTime)}
                          </span>
                        )}
                        {isQueued && (
                          <span className="flex items-center gap-1 text-muted-foreground">
                            <Clock className="size-3" />
                            Queued
                          </span>
                        )}
                        {isCompleted && (
                          <span className="flex items-center gap-1 text-status-success font-semibold">
                            <CheckCircle2 className="size-3" />
                            {formatElapsed(task.startTime, task.endTime)}
                          </span>
                        )}
                        {isError && (
                          <span className="flex items-center gap-1 text-status-error font-semibold">
                            <XCircle className="size-3" />
                            Failed
                          </span>
                        )}
                        {isQueued && (
                          <button
                            onClick={() => cancelTask(task.id)}
                            className="text-muted-foreground hover:text-foreground ml-1 p-0.5"
                            title="Cancel queued task"
                          >
                            <X className="size-3" />
                          </button>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                      <span className="truncate">{task.actionLabel}</span>
                    </div>

                    {/* Progress Bar & Status Text */}
                    {isRunning && (
                      <div className="flex flex-col gap-1 mt-0.5">
                        <div className="w-full h-1 bg-muted rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary transition-all duration-300"
                            style={{ width: `${Math.max(task.progress, 15)}%` }}
                          />
                        </div>
                        <span className="text-[10px] text-primary/80 font-mono truncate">
                          {task.statusMessage}
                        </span>
                      </div>
                    )}

                    {isError && task.error && (
                      <div className="bg-status-error/10 border border-status-error/20 rounded p-1.5 text-[10px] font-mono text-status-error break-words whitespace-pre-wrap">
                        {task.error}
                      </div>
                    )}
                  </div>
                )
              })
            )}
          </div>
        </div>
      )}

      {/* Collapsed Pill Button Trigger */}
      <button
        onClick={() => setExpanded(!expanded)}
        className={cn(
          "pointer-events-auto flex items-center gap-2.5 px-3 py-1.5 rounded-full border shadow-xl backdrop-blur-md transition-all cursor-pointer",
          activeCount > 0
            ? "bg-card border-primary/50 text-foreground ring-1 ring-primary/30"
            : queuedCount > 0
            ? "bg-card border-status-warning/40 text-foreground"
            : "bg-card/90 border-border text-muted-foreground hover:text-foreground"
        )}
      >
        {activeCount > 0 ? (
          <>
            <span className="relative flex size-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
              <span className="relative inline-flex rounded-full size-2 bg-primary" />
            </span>
            <span className="text-xs font-mono font-bold text-foreground">
              {activeCount} Running {queuedCount > 0 && `(${queuedCount} Queued)`}
            </span>
          </>
        ) : queuedCount > 0 ? (
          <>
            <Clock className="size-3.5 text-status-warning" />
            <span className="text-xs font-mono text-foreground font-semibold">
              {queuedCount} Queued
            </span>
          </>
        ) : (
          <>
            <Layers className="size-3.5 text-muted-foreground" />
            <span className="text-xs font-mono text-muted-foreground">Queue Idle</span>
          </>
        )}

        {expanded ? <ChevronDown className="size-3" /> : <ChevronUp className="size-3" />}
      </button>
    </div>
  )
}
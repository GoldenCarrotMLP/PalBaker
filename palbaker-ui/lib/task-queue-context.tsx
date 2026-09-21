"use client"

import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from "react"
import { BuildConsoleAPI } from "@/lib/data-service"

export type ChannelType = "unreal" | "blender" | "general"

export const CHANNEL_CONCURRENCY: Record<ChannelType, number> = {
  unreal: 1,   // Strictly serialized to prevent Unreal locks & cooker collisions
  blender: 3,  // Parallel headless blender instances
  general: 2,  // Extractions, DB builds, audio transcoding
}

export interface QueueTask {
  id: string
  name: string         // e.g. "Katress_big_head"
  basePal: string      // e.g. "CatMage"
  actionLabel: string  // e.g. "Full Pipeline (Push & Cook)"
  actionKey: string    // e.g. "full", "push", "create_blend"
  channel: ChannelType
  status: "queued" | "running" | "completed" | "error" | "cancelled"
  progress: number     // 0 to 100
  statusMessage: string
  startTime?: number
  endTime?: number
  error?: string
  run: (updateStatus: (msg: string, progress?: number) => void) => Promise<any>
  onSuccess?: (res?: any) => void
  onError?: (err: any) => void
}

export function getChannelForAction(action: string): ChannelType {
  switch (action) {
    case "create_blend":
    case "create-blend":
    case "refresh_blend":
    case "refresh-blend":
    case "sidecar":
      return "blender"

    case "push":
    case "cook":
    case "cook_only":
    case "pack":
    case "pack_only":
    case "full":
    case "recursive_cook":
    case "recursive-cook":
    case "decompile":
    case "push_anims":
    case "push-anims":
    case "dump_anims":
    case "dump-anims":
    case "launch_unreal":
    case "restart_unreal":
      return "unreal"

    default:
      return "general"
  }
}

export function getActionFriendlyLabel(action: string): string {
  const map: Record<string, string> = {
    full: "Full Pipeline (Push & Cook)",
    push: "Push to Unreal",
    cook: "Cook & Pack",
    cook_only: "Cook (Compile only)",
    pack: "Pack",
    pack_only: "Pack (Package only)",
    recursive_cook: "Recursive Cook & Pack",
    create_blend: "Create .blend file",
    refresh_blend: "Sync Layouts",
    decompile: "Generate Sources (Decompile)",
    extract_pal: "Extract Game Assets",
    dump_anims: "Dump Animations",
    push_anims: "Push Animations",
  }
  return map[action] || action.replace(/[-_]/g, " ").toUpperCase()
}

interface TaskQueueContextValue {
  tasks: QueueTask[]
  activeCount: number
  queuedCount: number
  addTask: (options: {
    name: string
    basePal: string
    actionKey: string
    actionLabel?: string
    channel?: ChannelType
    run: (updateStatus: (msg: string, progress?: number) => void) => Promise<any>
    onSuccess?: (res?: any) => void
    onError?: (err: any) => void
  }) => string
  cancelTask: (id: string) => void
  clearCompleted: () => void
  isTaskActiveForMod: (modName: string) => boolean
}

const TaskQueueContext = createContext<TaskQueueContextValue | null>(null)

export function TaskQueueProvider({ children }: { children: React.ReactNode }) {
  const [tasks, setTasks] = useState<QueueTask[]>([])
  const runningIdsRef = useRef<Set<string>>(new Set())

  // Listen to live terminal logs to update active task progress percentages
  useEffect(() => {
    const unsub = BuildConsoleAPI.subscribe((log) => {
      const msg = log.msg.toLowerCase()
      setTasks((prev) => {
        // Find running tasks
        const hasRunning = prev.some((t) => t.status === "running")
        if (!hasRunning) return prev

        return prev.map((t) => {
          if (t.status !== "running") return t

          let progress = t.progress
          let statusMessage = t.statusMessage

          if (msg.includes("running headless blender") || msg.includes("exporting fbx")) {
            progress = 25
            statusMessage = "Exporting FBX from Blender..."
          } else if (msg.includes("connecting to open unreal engine")) {
            progress = 45
            statusMessage = "Connecting to Unreal Editor via Remote Link..."
          } else if (msg.includes("importing skeletal fbx") || msg.includes("importing texture")) {
            progress = 65
            statusMessage = "Importing Mesh & Textures in Unreal..."
          } else if (msg.includes("cooking target folders")) {
            progress = 80
            statusMessage = "Targeted Micro-Cooking assets..."
          } else if (msg.includes("building final pak")) {
            progress = 92
            statusMessage = "Packaging _P.pak archive..."
          } else if (msg.includes("cue4parse") || msg.includes("extracting")) {
            progress = 50
            statusMessage = "Extracting Game Archives..."
          }

          return { ...t, progress, statusMessage }
        })
      })
    })

    return () => unsub()
  }, [])

  const executeTask = useCallback(async (task: QueueTask) => {
    try {
      const res = await task.run((msg: string, p?: number) => {
        setTasks((pTasks) =>
          pTasks.map((pt) =>
            pt.id === task.id
              ? { ...pt, statusMessage: msg, ...(p !== undefined ? { progress: p } : {}) }
              : pt
          )
        )
      })
      setTasks((pTasks) =>
        pTasks.map((pt) =>
          pt.id === task.id
            ? {
                ...pt,
                status: "completed",
                progress: 100,
                endTime: Date.now(),
                statusMessage: "Completed successfully!",
              }
            : pt
        )
      )
      task.onSuccess?.(res)
    } catch (err: any) {
      const errStr = err?.message || String(err)
      setTasks((pTasks) =>
        pTasks.map((pt) =>
          pt.id === task.id
            ? {
                ...pt,
                status: "error",
                endTime: Date.now(),
                error: errStr,
                statusMessage: "Execution failed",
              }
            : pt
        )
      )
      task.onError?.(errStr)
    } finally {
      runningIdsRef.current.delete(task.id)
    }
  }, [])

  // Side-effect scheduler: runs outside setState updaters, protected from React StrictMode duplicate calls
  useEffect(() => {
    const channels: ChannelType[] = ["unreal", "blender", "general"]
    const tasksToStart: QueueTask[] = []

    for (const ch of channels) {
      const runningInChannel = tasks.filter((t) => t.channel === ch && t.status === "running").length
      const maxConcurrency = CHANNEL_CONCURRENCY[ch]
      const availableSlots = maxConcurrency - runningInChannel

      if (availableSlots > 0) {
        const queuedTasks = tasks.filter(
          (t) => t.channel === ch && t.status === "queued" && !runningIdsRef.current.has(t.id)
        )
        tasksToStart.push(...queuedTasks.slice(0, availableSlots))
      }
    }

    if (tasksToStart.length === 0) return

    // Immediately lock IDs so duplicate render passes cannot execute the same task twice
    for (const t of tasksToStart) {
      runningIdsRef.current.add(t.id)
    }

    const startIds = new Set(tasksToStart.map((t) => t.id))
    const now = Date.now()

    setTasks((prev) =>
      prev.map((t) => {
        if (startIds.has(t.id)) {
          return {
            ...t,
            status: "running" as const,
            startTime: now,
            statusMessage: "Starting process...",
            progress: 10,
          }
        }
        return t
      })
    )

    for (const t of tasksToStart) {
      executeTask(t)
    }
  }, [tasks, executeTask])

  const addTask = useCallback(
    (options: {
      name: string
      basePal: string
      actionKey: string
      actionLabel?: string
      channel?: ChannelType
      run: (updateStatus: (msg: string, progress?: number) => void) => Promise<any>
      onSuccess?: (res?: any) => void
      onError?: (err: any) => void
    }) => {
      // Check if an identical task for this mod is already queued or running
      const isDuplicate = tasks.some(
        (t) =>
          t.name === options.name &&
          t.actionKey === options.actionKey &&
          (t.status === "queued" || t.status === "running")
      )
      if (isDuplicate) {
        return ""
      }

      const id = `${options.name}-${options.actionKey}-${Date.now()}`
      const channel = options.channel || getChannelForAction(options.actionKey)
      const actionLabel = options.actionLabel || getActionFriendlyLabel(options.actionKey)

      const newTask: QueueTask = {
        id,
        name: options.name,
        basePal: options.basePal,
        actionKey: options.actionKey,
        actionLabel,
        channel,
        status: "queued",
        progress: 0,
        statusMessage: "Waiting in queue...",
        run: options.run,
        onSuccess: options.onSuccess,
        onError: options.onError,
      }

      setTasks((prev) => [...prev, newTask])
      return id
    },
    [tasks]
  )

  const cancelTask = useCallback((id: string) => {
    setTasks((prev) =>
      prev.map((t) => (t.id === id && t.status === "queued" ? { ...t, status: "cancelled", statusMessage: "Cancelled by user" } : t))
    )
  }, [])

  const clearCompleted = useCallback(() => {
    setTasks((prev) => prev.filter((t) => t.status === "running" || t.status === "queued"))
  }, [])

  const isTaskActiveForMod = useCallback(
    (modName: string) => {
      return tasks.some((t) => t.name === modName && (t.status === "running" || t.status === "queued"))
    },
    [tasks]
  )

  const activeCount = tasks.filter((t) => t.status === "running").length
  const queuedCount = tasks.filter((t) => t.status === "queued").length

  return (
    <TaskQueueContext.Provider
      value={{
        tasks,
        activeCount,
        queuedCount,
        addTask,
        cancelTask,
        clearCompleted,
        isTaskActiveForMod,
      }}
    >
      {children}
    </TaskQueueContext.Provider>
  )
}

export function useTaskQueue() {
  const ctx = useContext(TaskQueueContext)
  if (!ctx) {
    throw new Error("useTaskQueue must be used within a TaskQueueProvider")
  }
  return ctx
}
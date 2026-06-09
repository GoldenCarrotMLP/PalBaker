"use client"

import { X } from "lucide-react"
import { cn } from "@/lib/utils"
import type { Notification } from "./use-notifications"

interface Props {
  notifications: Notification[]
  onDismiss: (id: string) => void
}

export function NotificationToast({ notifications, onDismiss }: Props) {
  if (notifications.length === 0) return null

  return (
    <div className="fixed top-6 right-6 z-[100] flex flex-col gap-3 max-w-sm w-full pointer-events-none">
      {notifications.map((n) => (
        <div
          key={n.id}
          className={cn(
            "p-4 rounded-lg border shadow-xl flex gap-3 items-start pointer-events-auto animate-in fade-in slide-in-from-top-4 duration-300 bg-background/95 backdrop-blur",
            n.type === "success" && "border-green-800/40 bg-green-950/20 text-green-300",
            n.type === "info"    && "border-blue-800/40 bg-blue-950/20 text-blue-300",
            n.type === "error"   && "border-red-800/40 bg-red-950/20 text-red-300",
            n.type === "warning" && "border-amber-800/40 bg-amber-950/20 text-amber-300"
          )}
        >
          <div className="flex-1">
            {n.title && <div className="font-bold text-sm mb-0.5">{n.title}</div>}
            <div className="text-xs">{n.message}</div>
          </div>
          <button
            onClick={() => onDismiss(n.id)}
            className="text-muted-foreground hover:text-foreground shrink-0 cursor-pointer"
          >
            <X className="size-4" />
          </button>
        </div>
      ))}
    </div>
  )
}

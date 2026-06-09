"use client"

import { useState } from "react"

export interface Notification {
  id: string
  message: string
  type: "success" | "info" | "error" | "warning"
  title?: string
}

export function useNotifications() {
  const [notifications, setNotifications] = useState<Notification[]>([])

  function showNotification(
    message: string,
    type: Notification["type"] = "info",
    title?: string
  ) {
    const id = Math.random().toString(36).slice(2, 9)
    setNotifications((prev) => [...prev, { id, message, type, title }])
    setTimeout(() => {
      setNotifications((prev) => prev.filter((n) => n.id !== id))
    }, 4000)
  }

  function dismissNotification(id: string) {
    setNotifications((prev) => prev.filter((n) => n.id !== id))
  }

  return { notifications, showNotification, dismissNotification }
}

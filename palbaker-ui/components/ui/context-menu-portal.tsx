"use client"

import { useEffect, useRef } from "react"
import { createPortal } from "react-dom"
import { cn } from "@/lib/utils"

export interface ContextMenuItem {
  label: string
  icon?: React.ReactNode
  disabled?: boolean
  danger?: boolean
  separator?: never
}

export interface ContextMenuSeparator {
  separator: true
  label?: never
  icon?: never
  disabled?: never
  danger?: never
}

export type ContextMenuEntry = ContextMenuItem | ContextMenuSeparator

interface Props {
  x: number
  y: number
  items: ContextMenuEntry[]
  onClose: () => void
  onSelect: (label: string) => void
}

export function ContextMenuPortal({ x, y, items, onClose, onSelect }: Props) {
  const menuRef = useRef<HTMLDivElement>(null)

  // Close on outside click or Escape
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose() }
    const onMouse = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) onClose()
    }
    document.addEventListener("mousedown", onMouse)
    document.addEventListener("keydown", onKey)
    return () => {
      document.removeEventListener("mousedown", onMouse)
      document.removeEventListener("keydown", onKey)
    }
  }, [onClose])

  // Adjust position to avoid viewport overflow
  const style: React.CSSProperties = {
    position: "fixed",
    top: y,
    left: x,
    zIndex: 9999,
  }

  if (typeof document === "undefined") return null

  return createPortal(
    <div
      ref={menuRef}
      style={style}
      className="min-w-48 bg-popover border border-border rounded-md shadow-xl py-1 text-sm animate-in fade-in-0 zoom-in-95 duration-100"
    >
      {items.map((item, i) => {
        if ("separator" in item && item.separator) {
          return <div key={i} className="border-t border-border my-1" />
        }
        const entry = item as ContextMenuItem
        return (
          <button
            key={entry.label}
            disabled={entry.disabled}
            onClick={() => {
              if (!entry.disabled) {
                onSelect(entry.label)
                onClose()
              }
            }}
            className={cn(
              "w-full text-left px-4 py-2 flex items-center gap-2.5 transition-colors",
              entry.disabled
                ? "text-muted-foreground/40 cursor-not-allowed"
                : entry.danger
                ? "text-status-error hover:bg-status-error/10"
                : "text-foreground hover:bg-accent",
            )}
          >
            {entry.icon && (
              <span className="shrink-0 size-3.5 flex items-center justify-center">
                {entry.icon}
              </span>
            )}
            {entry.label}
          </button>
        )
      })}
    </div>,
    document.body,
  )
}

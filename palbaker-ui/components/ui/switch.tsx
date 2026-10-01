"use client"

import * as React from "react"
import { cn } from "@/lib/utils"

export type SwitchProps = Omit<
  React.InputHTMLAttributes<HTMLInputElement>,
  "size"
> & {
  checked: boolean
  onCheckedChange?: (checked: boolean) => void
  size?: "sm" | "default"
}

export function Switch({
  checked,
  onCheckedChange,
  className,
  disabled,
  size = "default",
  ...props
}: SwitchProps) {
  const isSm = size === "sm"
  return (
    <label
      className={cn(
        "relative inline-flex items-center cursor-pointer shrink-0 select-none",
        disabled && "opacity-40 cursor-not-allowed",
        className
      )}
    >
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onCheckedChange?.(e.target.checked)}
        className="sr-only peer"
        {...props}
      />
      <div
        className={cn(
          "bg-muted/80 border border-border/80 peer-checked:bg-primary peer-checked:border-primary rounded-full transition-colors duration-200",
          isSm ? "w-7 h-4" : "w-9 h-5"
        )}
      />
      <div
        className={cn(
          "absolute top-0.5 left-0.5 bg-white rounded-full shadow-md transition-transform duration-200",
          isSm
            ? "size-3 peer-checked:translate-x-3"
            : "size-4 peer-checked:translate-x-4"
        )}
      />
    </label>
  )
}
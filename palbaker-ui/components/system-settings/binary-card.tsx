"use client"

import { useState, useEffect } from "react"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

interface Action {
  label: string
  actionKey: string
  variant: "ghost" | "primary" | "warning"
  disabled?: boolean
}

interface Props {
  name: string
  status: string
  statusClass: string
  description: string
  accentColor: string
  actions: Action[]
  onAction?: (actionKey: string) => void
  repoBranch?: string
}

export function BinaryCard({ name, status: initialStatus, statusClass: initialStatusClass, description, accentColor: initialAccentColor, actions: initialActions, onAction, repoBranch }: Props) {
  const [latestVersion, setLatestVersion] = useState<string | null>(null)
  const [isLoadingRelease, setIsLoadingRelease] = useState(false)

  let creator = "UE4SS Team"
  let sourceUrl = "https://github.com/UE4SS-RE/RE-UE4SS"
  let repoPath = "UE4SS-RE/RE-UE4SS"

  if (name === "PalSchema Plugin") {
    creator = "Okaetsu / Palworld Modding Community"
    sourceUrl = "https://github.com/Okaetsu/RE-UE4SS"
    repoPath = "Okaetsu/PalSchema"
  } else if (name === "UE4SS") {
    if (repoBranch === "Palworld-Experimental") {
      creator = "Okaetsu"
      sourceUrl = "https://github.com/Okaetsu/RE-UE4SS"
      repoPath = "Okaetsu/RE-UE4SS"
    } else {
      creator = "UE4SS Team"
      sourceUrl = "https://github.com/UE4SS-RE/RE-UE4SS"
      repoPath = "UE4SS-RE/RE-UE4SS"
    }
  }

  let currentVersion = "3.0.1"
  if (name === "PalSchema Plugin") {
    currentVersion = "0.5.2"
  } else if (name === "UE4SS") {
    currentVersion = repoBranch === "Palworld-Experimental" ? "experimental-palworld" : "3.0.1"
  }

  const isOutdated = latestVersion && currentVersion !== latestVersion
  const status = isOutdated ? "UPDATE AVAILABLE" : initialStatus
  const statusClass = isOutdated ? "bg-status-warning/15 text-status-warning border-status-warning/30" : initialStatusClass
  const accentColor = isOutdated ? "border-l-status-warning" : initialAccentColor

  const actions = initialActions.map((a) => {
    const isInstalled = initialStatus.startsWith("INSTALLED") || initialStatus.includes("ACTIVE")
    if (isOutdated && isInstalled && (a.actionKey === "repair" || a.actionKey === "install")) {
      return { ...a, label: "UPDATE", variant: "primary" as const }
    }
    return a
  })

  useEffect(() => {
    if (!repoPath) return
    async function fetchLatestRelease() {
      setIsLoadingRelease(true)
      try {
        const res = await fetch(`https://api.github.com/repos/${repoPath}/releases/latest`)
        if (res.ok) {
          const data = await res.json()
          if (data && data.tag_name) {
            setLatestVersion(data.tag_name.replace(/^v/, ""))
          }
        }
      } catch (err) {
        console.error("Failed to check latest release:", err)
      } finally {
        setIsLoadingRelease(false)
      }
    }
    fetchLatestRelease()
  }, [repoPath])

  const actionClasses = {
    ghost: "border border-border bg-transparent text-foreground hover:bg-accent",
    primary: "bg-primary text-primary-foreground hover:bg-primary/80",
    warning: "bg-status-warning text-white hover:bg-status-warning/80",
  }

  return (
    <div className={cn("flex items-center gap-4 bg-muted/30 rounded border-l-2 border border-border px-4 py-3", accentColor)}>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-foreground text-sm font-semibold">{name}</span>
          <Badge variant="outline" className={cn("text-xs font-bold border px-2 py-0", statusClass)}>
            {status}
          </Badge>
          {latestVersion && (
            <Badge variant="secondary" className="text-[10px] font-semibold border px-1.5 py-0 bg-primary/10 text-primary border-primary/20">
              {isLoadingRelease ? "v..." : `Latest: v${latestVersion}`}
            </Badge>
          )}
        </div>
        <p className="text-muted-foreground text-xs leading-relaxed">{description}</p>
        
        {(creator || sourceUrl) && (
          <div className="flex items-center gap-2 mt-1.5 text-[11px] text-muted-foreground">
            {creator && <span>Creator: <span className="text-foreground/80 font-medium">{creator}</span></span>}
            {creator && sourceUrl && <span className="opacity-50">•</span>}
            {sourceUrl && <a href={sourceUrl} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline font-medium">Source / Credits</a>}
          </div>
        )}
      </div>
      <div className="flex items-center gap-2 shrink-0 flex-wrap max-w-[280px] justify-end">
        {actions.map((a) => (
          <button
            key={a.actionKey}
            onClick={() => { if (!a.disabled) onAction?.(a.actionKey) }}
            disabled={a.disabled}
            className={cn("px-3 py-1.5 rounded text-xs font-semibold transition-colors whitespace-nowrap cursor-pointer", a.disabled ? "opacity-50 cursor-not-allowed bg-muted text-muted-foreground border border-border" : actionClasses[a.variant])}
          >
            {a.label}
          </button>
        ))}
      </div>
    </div>
  )
}
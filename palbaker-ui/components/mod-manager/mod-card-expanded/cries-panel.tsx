// palbaker-ui/components/mod-manager/mod-card-expanded/cries-panel.tsx
"use client"

import { useRef, useEffect } from "react"
import { Play, Trash2, Upload } from "lucide-react"
import { type ModItem } from "@/lib/mock-data"
import { ModManagerAPI } from "@/lib/data-service"
import { convertFileSrc } from "@tauri-apps/api/core"
import { cn } from "@/lib/utils"

const CRY_SLOTS = ["Normal", "Joy", "Anger", "Sorrow", "Pain", "Death"] as const

interface Props {
  mod: ModItem
  onRefresh: () => void
  onNotify: (msg: string, type: "success" | "info" | "error" | "warning", title?: string) => void
}

export function CriesPanel({ mod, onRefresh, onNotify }: Props) {
  const audioInputRefs = useRef<Record<string, HTMLInputElement | null>>({})
  const activeAudioRef = useRef<HTMLAudioElement | null>(null)
  
  const availableCries = CRY_SLOTS.filter((s) => mod.sound_metadata[s] !== undefined)
  const hasSoundData   = availableCries.length > 0

  useEffect(() => {
    return () => {
      if (activeAudioRef.current) {
        activeAudioRef.current.pause()
        activeAudioRef.current = null
      }
    }
  }, [])

  const handleAudioChange = async (slot: string, e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const reader = new FileReader()
      reader.onload = async () => {
        const bytes = Array.from(new Uint8Array(reader.result as ArrayBuffer))
        await ModManagerAPI.saveModAudioBytes(mod.base_pal, mod.name, slot, file.name, bytes)
        onNotify("Custom audio override updated successfully!", "success")
        onRefresh()
      }
      reader.readAsArrayBuffer(file)
    } catch (err) {
      onNotify(`Failed to save audio: ${err}`, "error", "Operation Failed")
    }
  }

  const handleAudioClear = async (slot: string) => {
    if (!window.confirm(`Clear the custom override for ${slot}?`)) return
    try {
      await ModManagerAPI.audioClear(mod.base_pal, mod.name, slot)
      onNotify(`Cleared custom override for ${slot}.`, "success")
      onRefresh()
    } catch (err) {
      onNotify(`Failed to clear audio: ${err}`, "error", "Operation Failed")
    }
  }

  const handleAudioPlay = async (slot: string) => {
    try {
      const res = await ModManagerAPI.audioPlay(mod.base_pal, mod.name, slot)
      if (res && res.status === "success" && res.path) {
        if (activeAudioRef.current) {
          activeAudioRef.current.pause()
          activeAudioRef.current = null
        }
        const isLive = typeof window !== "undefined" && (window as any).__TAURI_INTERNALS__ !== undefined
        const src = isLive ? convertFileSrc(res.path) : res.path.startsWith("http") ? res.path : `https://asset.localhost/${res.path}`
        const cacheBusterSrc = `${src}?t=${Date.now()}`
        const audio = new Audio(cacheBusterSrc)
        activeAudioRef.current = audio
        await audio.play()
      } else {
        onNotify(res.message || "Failed to locate playable preview path.", "error", "Playback Failed")
      }
    } catch (err: any) {
      onNotify(`Failed to play audio: ${err.message || err}`, "error", "Playback Failed")
    }
  }

  return (
    <div className="flex flex-col gap-2 flex-1 min-w-0">
      <span className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">Cries Replacement</span>
      {!hasSoundData ? (
        <p className="text-muted-foreground text-xs italic">
          {mod.has_fmodel ? "No mapped audio database found for this Pal." : "Audio replacement requires raw FModel files. Click 'Create .blend file' or 'Generate Sources' first."}
        </p>
      ) : (
        <div className="grid grid-cols-2 gap-2">
          {availableCries.map((slot) => {
            const hasOverride = !!mod.audio_overrides[slot]
            return (
              <div key={slot} className={cn("flex items-center gap-2 rounded px-3 py-2 border", hasOverride ? "bg-primary/5 border-primary/30" : "bg-muted/50 border-border")}>
                <input type="file" ref={(el) => { audioInputRefs.current[slot] = el }} onChange={(e) => handleAudioChange(slot, e)} accept="audio/wav, audio/mp3, audio/ogg" className="hidden" />
                <button onClick={() => handleAudioPlay(slot)} className="shrink-0 size-6 rounded-full bg-primary/10 hover:bg-primary/20 flex items-center justify-center transition-colors cursor-pointer">
                  <Play className="size-3 text-primary" />
                </button>
                <div className="flex-1 min-w-0">
                  <div className="text-foreground text-xs font-semibold">{slot}</div>
                  <div className={cn("text-[10px] truncate", hasOverride ? "text-status-warning" : "text-muted-foreground")}>{hasOverride ? "Custom Override" : "Original Game Sound"}</div>
                </div>
                {hasOverride ? (
                  <button onClick={() => handleAudioClear(slot)} className="shrink-0 cursor-pointer">
                    <Trash2 className="size-3.5 text-status-error" />
                  </button>
                ) : (
                  <button onClick={() => audioInputRefs.current[slot]?.click()} className="shrink-0 text-muted-foreground hover:text-foreground transition-colors cursor-pointer">
                    <Upload className="size-3.5" />
                  </button>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
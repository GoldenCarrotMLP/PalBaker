"use client"

import { useState } from "react"
import { Loader2 } from "lucide-react"

interface Props {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => Promise<void>
}

export function UnrealClosedModal({ isOpen, onClose, onConfirm }: Props) {
  const [loading, setLoading] = useState(false)

  if (!isOpen) return null

  const handleLaunch = async () => {
    setLoading(true)
    try {
      await onConfirm()
      onClose()
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="bg-card border-2 border-primary/30 rounded-xl max-w-md w-full shadow-2xl p-6 relative flex flex-col items-center text-center gap-4">
        <div className="size-16 rounded-full bg-primary/10 flex items-center justify-center text-3xl animate-bounce">
          🦊
        </div>
        
        <h3 className="text-foreground font-extrabold text-lg uppercase tracking-wider">
          Unreal Editor is Closed!
        </h3>
        
        <p className="text-muted-foreground text-sm leading-relaxed">
          Oh noes, Poki! Unreal Editor needs to be running so I can communicate with it to cook or decompile assets! Let me launch it for you! ;3
        </p>

        <div className="flex flex-col gap-2.5 w-full mt-2">
          <button
            onClick={handleLaunch}
            disabled={loading}
            className="w-full py-2.5 rounded bg-primary text-primary-foreground font-bold text-xs uppercase tracking-wider hover:bg-primary/90 transition-colors shadow flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading && <Loader2 className="size-3.5 animate-spin" />}
            Launch Unreal Editor
          </button>
          
          <button
            onClick={onClose}
            disabled={loading}
            className="w-full py-2 border border-border rounded text-muted-foreground hover:text-foreground text-xs font-semibold hover:bg-accent transition-colors cursor-pointer disabled:opacity-50"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}

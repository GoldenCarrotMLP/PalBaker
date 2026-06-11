"use client"

import { useState } from "react"
import { Loader2 } from "lucide-react"

interface Props {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => Promise<void>
}

export function AssetInjectModal({ isOpen, onClose, onConfirm }: Props) {
  const [loading, setLoading] = useState(false)

  if (!isOpen) return null

  const handleInject = async () => {
    setLoading(true)
    try {
      await onConfirm()
      // No onClose() call here; the page's state-driven re-verification loop handles transition/unmounting!
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="bg-card border-2 border-primary/30 rounded-xl max-w-md w-full shadow-2xl p-6 relative flex flex-col items-center text-center gap-4">
        <div className="size-16 rounded-full bg-primary/10 flex items-center justify-center text-3xl">
          📦
        </div>
        
        <h3 className="text-foreground font-extrabold text-lg uppercase tracking-wider">
          Missing Required Assets!
        </h3>
        
        <p className="text-muted-foreground text-sm leading-relaxed">
          Some required material assets and templates are missing from your ModKit's Content folder. I can inject these matching assets automatically for you! 🦊✨
        </p>

        <div className="flex flex-col gap-2.5 w-full mt-2">
          <button
            onClick={handleInject}
            disabled={loading}
            className="w-full py-2.5 rounded bg-primary text-primary-foreground font-bold text-xs uppercase tracking-wider hover:bg-primary/90 transition-colors shadow flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading && <Loader2 className="size-3.5 animate-spin" />}
            Yes, Inject Assets
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
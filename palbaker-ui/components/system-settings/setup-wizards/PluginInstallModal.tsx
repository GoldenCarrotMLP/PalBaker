"use client"

import { useState } from "react"
import { Loader2 } from "lucide-react"

interface Props {
  isOpen: boolean
  isOutdated?: boolean
  needsCompile?: boolean
  onClose: () => void
  onConfirm: () => Promise<void>
}

export function PluginInstallModal({ isOpen, isOutdated = false, needsCompile = false, onClose, onConfirm }: Props) {
  const [loading, setLoading] = useState(false)

  if (!isOpen) return null

  const handleInstall = async () => {
    setLoading(true)
    try {
      await onConfirm()
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  let title = "Missing Unreal Helper Plugin!"
  let description = "The PalBaker C++ editor helper plugin is not installed in your Unreal ModKit. I need this helper so I can cook, pack, and export standalone assets! ;3"

  if (isOutdated) {
    title = "Outdated Unreal Helper Plugin!"
    description = "Your PalBaker C++ editor helper plugin is outdated! Please make sure Unreal Editor is closed to avoid file locks, then I can update it for you! ;3"
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="bg-card border-2 border-primary/30 rounded-xl max-w-md w-full shadow-2xl p-6 relative flex flex-col items-center text-center gap-4">
        <div className="size-16 rounded-full bg-primary/10 flex items-center justify-center text-3xl">
          🔌
        </div>
        
        <h3 className="text-foreground font-extrabold text-lg uppercase tracking-wider">
          {title}
        </h3>
        
        <p className="text-muted-foreground text-sm leading-relaxed">
          {description}
        </p>

        {/* Clear, honest transparency warning about compiler actions vs simple copies */}
        <div className="bg-muted/40 border border-border rounded-lg p-3 text-left w-full text-xs flex flex-col gap-1">
          <span className="font-bold text-foreground">📦 Installation Method:</span>
          {needsCompile ? (
            <span className="text-status-warning leading-relaxed">
              ⚠️ <strong>C++ Compilation Required:</strong> The pre-compiled binaries are missing or modified. This will build the helper plugin from scratch using your local MSVC compiler, which can take up to <strong>1 to 2 minutes</strong>. Please ensure Unreal Editor is closed to prevent file locks!
            </span>
          ) : (
            <span className="text-status-success leading-relaxed">
              ⚡ <strong>Sub-second File Sync:</strong> Pre-compiled binaries detected! This will simply copy and register the compiled plugin files into your Unreal project. It takes less than a second and does not require building!
            </span>
          )}
        </div>

        <div className="flex flex-col gap-2.5 w-full mt-2">
          <button
            onClick={handleInstall}
            disabled={loading}
            className={`w-full py-2.5 rounded font-bold text-xs uppercase tracking-wider transition-colors shadow flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${
              isOutdated 
                ? "bg-status-warning text-white hover:bg-status-warning/90" 
                : "bg-primary text-primary-foreground hover:bg-primary/90"
            }`}
          >
            {loading && <Loader2 className="size-3.5 animate-spin" />}
            {isOutdated ? "Yes, Update Plugin" : "Yes, Install Plugin"}
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
"use client"

import { useState } from "react"
import { Loader2 } from "lucide-react"

interface Props {
  isOpen: boolean
  needsRemoteExec?: boolean
  needsCooking?: boolean
  onClose: () => void
  onConfirm: () => Promise<void>
}

export function ConfigFixModal({ isOpen, needsRemoteExec = false, needsCooking = false, onClose, onConfirm }: Props) {
  const [loading, setLoading] = useState(false)

  if (!isOpen) return null

  const handleConfigure = async () => {
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

  let title = "Configure Project Settings!"
  let description = "Your Unreal ModKit project configuration files need to be modified to enable compiling and cooking. Let me automatically patch these settings for you! ;3"

  if (needsRemoteExec && !needsCooking) {
    title = "Enable Remote Execution!"
    description = "Your Unreal ModKit project settings need to be modified to enable Python Remote Execution inside DefaultEngine.ini. Let me automatically patch this setting! ;3"
  } else if (!needsRemoteExec && needsCooking) {
    title = "Configure Cooking Settings!"
    description = "Your Unreal ModKit project settings need to be modified to disable the I/O Store and Material Shader Sharing inside DefaultGame.ini. This is required to force compilation into loose .uasset files! Let me automatically patch this setting! ;3"
  } else if (needsRemoteExec && needsCooking) {
    title = "Configure Engine & Cooking!"
    description = "Your Unreal ModKit project settings need to be patched to enable Python Remote Execution (DefaultEngine.ini) and configure uncompressed loose cooking properties (DefaultGame.ini). Let me automatically patch these settings! ;3"
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="bg-card border-2 border-primary/30 rounded-xl max-w-md w-full shadow-2xl p-6 relative flex flex-col items-center text-center gap-4">
        <div className="size-16 rounded-full bg-primary/10 flex items-center justify-center text-3xl">
          ⚙️
        </div>
        
        <h3 className="text-foreground font-extrabold text-lg uppercase tracking-wider">
          {title}
        </h3>
        
        <p className="text-muted-foreground text-sm leading-relaxed">
          {description}
        </p>

        <div className="flex flex-col gap-2.5 w-full mt-2">
          <button
            onClick={handleConfigure}
            disabled={loading}
            className="w-full py-2.5 rounded bg-primary text-primary-foreground font-bold text-xs uppercase tracking-wider hover:bg-primary/90 transition-colors shadow flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading && <Loader2 className="size-3.5 animate-spin" />}
            Yes, Configure & Restart
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
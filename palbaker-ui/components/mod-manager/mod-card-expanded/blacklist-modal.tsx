// palbaker-ui/components/mod-manager/mod-card-expanded/blacklist-modal.tsx
"use client"

import { useState } from "react"
import { X, Save, ShieldAlert } from "lucide-react"
import { ModManagerAPI } from "@/lib/data-service"

interface Props {
  basePal: string
  modName: string
  initialBlacklist: string[]
  onClose: () => void
  onSaved: () => void
  onNotify: (msg: string, type: "success" | "info" | "error" | "warning", title?: string) => void
}

export function BlacklistModal({ basePal, modName, initialBlacklist, onClose, onSaved, onNotify }: Props) {
  const [text, setText] = useState(initialBlacklist.join("\n"))

  const handleSave = async () => {
    const arr = text.split("\n").map(l => l.trim()).filter(l => l.length > 0)
    try {
      await ModManagerAPI.setModBlacklist(basePal, modName, arr)
      onNotify("Packaging blacklist saved successfully!", "success")
      onSaved()
      onClose()
    } catch (err) {
      onNotify(`Failed to save blacklist: ${err}`, "error", "Operation Failed")
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-fade-in">
      <div className="bg-card border border-border rounded-lg shadow-2xl w-full max-w-lg flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-border bg-muted/20">
          <div className="flex items-center gap-2 text-foreground font-semibold">
            <ShieldAlert className="size-4 text-status-warning" />
            Packaging Blacklist
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors cursor-pointer">
            <X className="size-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 flex flex-col gap-4">
          <p className="text-xs text-muted-foreground leading-relaxed">
            Enter the virtual paths of any `.uasset` files or folders you want to <span className="font-bold text-foreground">exclude</span> from the final compiled `.pak` archive. This is useful for preventing unwanted assets from loading into the game.
          </p>
          <div className="bg-primary/10 border border-primary/20 rounded p-2.5 text-[10px] text-primary font-mono leading-relaxed">
            Format: One virtual path per line.<br/>
            Example: <span className="text-foreground/80">/Game/Pal/Model/Character/Monster/Baphomet/SK_Baphomet.uasset</span><br/>
            Example: <span className="text-foreground/80">/Game/Pal/Model/Character/Monster/Baphomet/Textures/</span>
          </div>

          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            className="w-full h-48 bg-console-bg border border-border rounded p-3 text-xs text-foreground font-mono focus:outline-none focus:ring-1 focus:ring-primary resize-none placeholder:text-muted-foreground/30"
            placeholder={`/Game/Pal/Model/Character/Monster/${basePal}/...`}
            spellCheck={false}
          />

          <div className="flex justify-end gap-3 mt-1">
            <button onClick={onClose} className="px-4 py-2 rounded text-xs font-semibold text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors cursor-pointer">
              Cancel
            </button>
            <button onClick={handleSave} className="flex items-center gap-1.5 px-4 py-2 rounded text-xs font-bold bg-primary text-primary-foreground hover:bg-primary/90 shadow transition-colors cursor-pointer">
              <Save className="size-3.5" />
              Save Blacklist
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
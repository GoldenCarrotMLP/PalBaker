"use client"

import { useState } from "react"
import { X, Plus, Trash2, Volume2, Sparkles, Eye } from "lucide-react"
import { type CustomAnimationEntry, type AnimNotifyEntry } from "@/lib/mock-data"
import { ModManagerAPI } from "@/lib/data-service"

interface Props {
  basePal: string
  modName: string
  animKey: string
  anim: CustomAnimationEntry
  onClose: () => void
  onSaved: () => void
  onNotify: (msg: string, type: "success" | "info" | "error" | "warning") => void
}

export function EditNotifiesModal({ basePal, modName, animKey, anim, onClose, onSaved, onNotify }: Props) {
  const [notifies, setNotifies] = useState<AnimNotifyEntry[]>(anim.notifies || [])
  const [notifyName, setNotifyName] = useState("PalSoundNotify")
  const [notifyTime, setNotifyTime] = useState(0.5)

  const handleAddNotify = () => {
    const next = [...notifies, { Name: notifyName, Time: notifyTime, NotifyPayload: {} }]
    setNotifies(next)
  }

  const handleRemoveNotify = (idx: number) => {
    setNotifies(notifies.filter((_, i) => i !== idx))
  }

  const handleSave = async () => {
    try {
      await ModManagerAPI.saveAnimationNotifies(basePal, modName, animKey, notifies)
      onNotify("Animation notifies updated successfully! ;3", "success")
      onSaved()
      onClose()
    } catch (err) {
      onNotify(`Failed to save notifies: ${err}`, "error")
    }
  }

  return (
    <div className="fixed inset-0 z-[110] flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-fade-in">
      <div className="bg-card border border-border rounded-xl shadow-2xl w-full max-w-lg flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-border bg-muted/20">
          <div className="flex flex-col">
            <span className="text-[10px] font-mono text-primary font-bold uppercase">AnimMontage Notifies</span>
            <h3 className="font-bold text-sm text-foreground">{anim.display_name}</h3>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground cursor-pointer"><X className="size-4" /></button>
        </div>

        <div className="p-5 flex flex-col gap-4 max-h-[60vh] overflow-y-auto">
          <div className="flex items-center justify-between border-b border-border/40 pb-3">
            <span className="text-xs font-semibold text-muted-foreground uppercase">Registered Notifies ({notifies.length})</span>
          </div>

          <div className="flex flex-col gap-2">
            {notifies.length === 0 ? (
              <p className="text-xs text-muted-foreground italic">No custom notifies added. Click below to add sound, particle, or blink events.</p>
            ) : (
              notifies.map((n, idx) => (
                <div key={idx} className="flex items-center justify-between bg-muted/40 p-2.5 rounded border border-border">
                  <div className="flex items-center gap-2">
                    {n.Name.includes("Sound") ? <Volume2 className="size-4 text-primary" /> : n.Name.includes("Blink") ? <Eye className="size-4 text-purple-400" /> : <Sparkles className="size-4 text-amber-400" />}
                    <div className="flex flex-col">
                      <span className="text-xs font-bold text-foreground font-mono">{n.Name}</span>
                      <span className="text-[10px] text-muted-foreground font-mono">Timestamp: {n.Time.toFixed(2)}s</span>
                    </div>
                  </div>
                  <button onClick={() => handleRemoveNotify(idx)} className="text-muted-foreground hover:text-status-error p-1 cursor-pointer"><Trash2 className="size-3.5" /></button>
                </div>
              ))
            )}
          </div>

          <div className="border-t border-border/40 pt-3 flex gap-2 items-end">
            <div className="flex flex-col gap-1 flex-1">
              <label className="text-[10px] uppercase font-semibold text-muted-foreground">Notify Type</label>
              <select value={notifyName} onChange={(e) => setNotifyName(e.target.value)} className="bg-muted/60 border border-border rounded px-2.5 py-1.5 text-xs text-foreground cursor-pointer">
                <option value="PalSoundNotify">Sound Event (PalSoundNotify)</option>
                <option value="PlayEffect">Niagara Particle (PlayEffect)</option>
                <option value="PalBlinkNotify">Eye Blink (PalBlinkNotify)</option>
                <option value="PalCustomNotify">Custom Action (PalCustomNotify)</option>
              </select>
            </div>
            <div className="flex flex-col gap-1 w-24">
              <label className="text-[10px] uppercase font-semibold text-muted-foreground">Time (s)</label>
              <input type="number" step="0.05" min="0" value={notifyTime} onChange={(e) => setNotifyTime(parseFloat(e.target.value) || 0)} className="bg-muted/60 border border-border rounded px-2.5 py-1.5 text-xs text-foreground font-mono" />
            </div>
            <button onClick={handleAddNotify} className="flex items-center gap-1 bg-primary text-primary-foreground text-xs font-semibold px-3 py-1.5 rounded hover:bg-primary/90 cursor-pointer h-[34px]"><Plus className="size-3" /> Add</button>
          </div>
        </div>

        <div className="flex justify-end gap-3 px-5 py-3 border-t border-border bg-muted/10">
          <button onClick={onClose} className="px-3 py-1.5 rounded text-xs font-semibold border border-border hover:bg-muted/50 cursor-pointer">Cancel</button>
          <button onClick={handleSave} className="px-4 py-1.5 rounded text-xs font-bold bg-primary text-primary-foreground hover:bg-primary/90 shadow cursor-pointer">Apply Notifies</button>
        </div>
      </div>
    </div>
  )
}
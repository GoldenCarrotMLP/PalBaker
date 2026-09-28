"use client"

import { useState, useMemo } from "react"
import { 
  X, 
  Plus, 
  Trash2, 
  Volume2, 
  Sparkles, 
  Eye, 
  Film, 
  CheckCircle2, 
  ShieldAlert, 
  Wand2 
} from "lucide-react"
import { type CustomAnimationEntry, type AnimNotifyEntry } from "@/lib/mock-data"
import { validateMontageNotifies } from "@/lib/action-rules"

interface Props {
  basePal: string
  modName: string
  animKey: string
  anim: CustomAnimationEntry
  allAnims?: Record<string, CustomAnimationEntry>
  onClose: () => void
  onSaved: () => void
  onNotify: (msg: string, type: "success" | "info" | "error" | "warning") => void
  onSaveEntry?: (patch: Partial<CustomAnimationEntry>) => Promise<void>
}

export function EditNotifiesModal({
  basePal,
  modName,
  animKey,
  anim,
  allAnims = {},
  onClose,
  onSaved,
  onNotify,
  onSaveEntry,
}: Props) {
  const [notifies, setNotifies] = useState<AnimNotifyEntry[]>(anim.notifies || [])
  const [notifyName, setNotifyName] = useState("PalSoundNotify")
  const [notifyTime, setNotifyTime] = useState(0.5)

  // Extract all available sequence assets from the mod's animation inventory
  const availableSequences = useMemo(() => {
    const seqs = new Set<string>()
    Object.values(allAnims).forEach((entry) => {
      if (entry.sequence_asset) seqs.add(entry.sequence_asset)
      if (entry.nla_track_name) seqs.add(`AS_${modName}_${entry.nla_track_name}`)
    })
    return Array.from(seqs).sort()
  }, [allAnims, modName])

  const defaultSequence =
    anim.sequence_asset || (anim.nla_track_name ? `AS_${modName}_${anim.nla_track_name}` : "")
  const [selectedSequence, setSelectedSequence] = useState<string>(defaultSequence)

  // Real-time Action Rule Validation
  const validation = useMemo(() => {
    const actionLookup = anim.nla_track_name || anim.display_name || animKey
    return validateMontageNotifies(actionLookup, notifies)
  }, [anim.nla_track_name, anim.display_name, animKey, notifies])

  const handleAutoAddRequired = () => {
    if (!validation.missingRequired.length) return
    const newItems: AnimNotifyEntry[] = validation.missingRequired.map((rule, idx) => {
      const parts = rule.Key.split(":")
      const mainName = parts[0]
      const eventName = parts[1]
      return {
        Name: mainName,
        Time: Math.min(0.2 + idx * 0.1, 1.0),
        NotifyPayload: {
          EventName: eventName,
          DetailType: rule.DetailType,
          IsStateNotify: rule.IsStateNotify,
          Templates: rule.Templates,
        },
      }
    })
    setNotifies((prev) => [...prev, ...newItems])
    onNotify(`Auto-injected ${newItems.length} required notify event(s)! ;3`, "info")
  }

  const handleAddNotify = () => {
    const next = [...notifies, { Name: notifyName, Time: notifyTime, NotifyPayload: {} }]
    setNotifies(next)
  }

  const handleRemoveNotify = (idx: number) => {
    setNotifies(notifies.filter((_, i) => i !== idx))
  }

  const handleSave = async () => {
    // STRICT REJECTION GATE: Block saving if required action notifies are missing
    if (!validation.isValid) {
      const missingList = validation.missingRequired.map((r) => r.Key).join(", ")
      onNotify(`Cannot save montage! Missing REQUIRED notifies for this action: ${missingList}`, "error")
      return
    }

    try {
      if (onSaveEntry) {
        await onSaveEntry({
          sequence_asset: selectedSequence,
          notifies: notifies,
        })
      }
      onNotify("Montage sequence & notifies verified and updated successfully! ;3", "success")
      onSaved()
      onClose()
    } catch (err: any) {
      onNotify(`Failed to save settings: ${err.message || err}`, "error")
    }
  }

  return (
    <div className="fixed inset-0 z-[110] flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-fade-in">
      <div className="bg-card border border-border rounded-xl shadow-2xl w-full max-w-lg flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-border bg-muted/20">
          <div className="flex flex-col">
            <span className="text-[10px] font-mono text-primary font-bold uppercase">AnimMontage Configuration</span>
            <h3 className="font-bold text-sm text-foreground">{anim.display_name}</h3>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground cursor-pointer">
            <X className="size-4" />
          </button>
        </div>

        <div className="p-5 flex flex-col gap-4 max-h-[65vh] overflow-y-auto">
          {/* SEQUENCE ASSIGNMENT DROPDOWN */}
          <div className="flex flex-col gap-1.5 p-3 rounded-lg border border-border/50 bg-muted/30">
            <div className="flex items-center justify-between">
              <label className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider flex items-center gap-1.5">
                <Film className="size-3.5 text-primary" />
                Assigned Animation Sequence
              </label>
              {selectedSequence && (
                <span className="text-[10px] font-mono text-primary bg-primary/10 px-1.5 py-0.5 rounded">
                  {selectedSequence}
                </span>
              )}
            </div>
            <select
              value={selectedSequence}
              onChange={(e) => setSelectedSequence(e.target.value)}
              className="bg-background border border-border rounded px-2.5 py-1.5 text-xs text-foreground font-mono cursor-pointer focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="">-- Default / None --</option>
              {availableSequences.map((seq) => (
                <option key={seq} value={seq}>
                  {seq}
                </option>
              ))}
            </select>
            <span className="text-[10px] text-muted-foreground leading-tight">
              The underlying AnimSequence clip played by this montage container.
            </span>
          </div>

          {/* MONTAGE VALIDATION BANNER */}
          {validation.actionRule && (
            <div
              className={`p-3 rounded-lg border flex flex-col gap-2 ${
                validation.isValid
                  ? "border-green-800/40 bg-green-950/20 text-green-300"
                  : "border-red-800/50 bg-red-950/30 text-red-300"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 font-bold text-xs">
                  {validation.isValid ? (
                    <>
                      <CheckCircle2 className="size-4 text-status-success shrink-0" />
                      <span>Montage Rules Verified</span>
                    </>
                  ) : (
                    <>
                      <ShieldAlert className="size-4 text-status-error shrink-0" />
                      <span>Action Rule Violation: Missing Required Notifies</span>
                    </>
                  )}
                </div>

                <div className="flex items-center gap-2 text-[10px] font-mono opacity-80">
                  <span>Flow: {validation.actionRule.ExpectedSectionFlow}</span>
                  <span>•</span>
                  <span>Loop: {validation.actionRule.IsLooping ? "Yes" : "No"}</span>
                </div>
              </div>

              {!validation.isValid && (
                <div className="flex flex-col gap-1.5 pt-1 border-t border-red-800/40">
                  <span className="text-[11px] leading-relaxed">
                    This action requires the following notifies to function correctly in-game:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {validation.missingRequired.map((r) => (
                      <span
                        key={r.Key}
                        className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-red-900/60 text-red-200 border border-red-700/60"
                      >
                        {r.Key} {r.Templates ? `(${r.Templates[0]})` : ""}
                      </span>
                    ))}
                  </div>
                  <button
                    type="button"
                    onClick={handleAutoAddRequired}
                    className="self-start mt-1 flex items-center gap-1.5 px-3 py-1 rounded bg-red-800/50 hover:bg-red-800 text-white font-bold text-xs transition-colors cursor-pointer"
                  >
                    <Wand2 className="size-3.5" /> Auto-Add Required Notifies
                  </button>
                </div>
              )}
            </div>
          )}

          <div className="flex items-center justify-between border-b border-border/40 pb-2">
            <span className="text-xs font-semibold text-muted-foreground uppercase">
              Registered Notifies ({notifies.length})
            </span>
          </div>

          <div className="flex flex-col gap-2">
            {notifies.length === 0 ? (
              <p className="text-xs text-muted-foreground italic">
                No custom notifies added. Click below to add sound, particle, or blink events.
              </p>
            ) : (
              notifies.map((n, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between bg-muted/40 p-2.5 rounded border border-border"
                >
                  <div className="flex items-center gap-2">
                    {n.Name.includes("Sound") || n.Name.includes("AkEvent") ? (
                      <Volume2 className="size-4 text-primary" />
                    ) : n.Name.includes("Blink") ? (
                      <Eye className="size-4 text-purple-400" />
                    ) : (
                      <Sparkles className="size-4 text-amber-400" />
                    )}
                    <div className="flex flex-col">
                      <span className="text-xs font-bold text-foreground font-mono">{n.Name}</span>
                      <span className="text-[10px] text-muted-foreground font-mono">
                        Timestamp: {n.Time.toFixed(2)}s
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={() => handleRemoveNotify(idx)}
                    className="text-muted-foreground hover:text-status-error p-1 cursor-pointer"
                  >
                    <Trash2 className="size-3.5" />
                  </button>
                </div>
              ))
            )}
          </div>

          <div className="border-t border-border/40 pt-3 flex gap-2 items-end">
            <div className="flex flex-col gap-1 flex-1">
              <label className="text-[10px] uppercase font-semibold text-muted-foreground">Notify Type</label>
              <select
                value={notifyName}
                onChange={(e) => setNotifyName(e.target.value)}
                className="bg-muted/60 border border-border rounded px-2.5 py-1.5 text-xs text-foreground cursor-pointer"
              >
                <option value="PalSoundNotify">Sound Event (PalSoundNotify)</option>
                <option value="PlayEffect">Niagara Particle (PlayEffect)</option>
                <option value="PalEffect">State Effect (PalEffect)</option>
                <option value="PalAttackCollision">Attack Hitbox (PalAttackCollision)</option>
                <option value="PalBlinkNotify">Eye Blink (PalBlinkNotify)</option>
                <option value="PalCustomNotify">Custom Action (PalCustomNotify)</option>
              </select>
            </div>
            <div className="flex flex-col gap-1 w-24">
              <label className="text-[10px] uppercase font-semibold text-muted-foreground">Time (s)</label>
              <input
                type="number"
                step="0.05"
                min="0"
                value={notifyTime}
                onChange={(e) => setNotifyTime(parseFloat(e.target.value) || 0)}
                className="bg-muted/60 border border-border rounded px-2.5 py-1.5 text-xs text-foreground font-mono"
              />
            </div>
            <button
              onClick={handleAddNotify}
              className="flex items-center gap-1 bg-primary text-primary-foreground text-xs font-semibold px-3 py-1.5 rounded hover:bg-primary/90 cursor-pointer h-[34px]"
            >
              <Plus className="size-3" /> Add
            </button>
          </div>
        </div>

        <div className="flex justify-end gap-3 px-5 py-3 border-t border-border bg-muted/10">
          <button
            onClick={onClose}
            className="px-3 py-1.5 rounded text-xs font-semibold border border-border hover:bg-muted/50 cursor-pointer"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!validation.isValid}
            className={`px-4 py-1.5 rounded text-xs font-bold shadow cursor-pointer transition-colors ${
              validation.isValid
                ? "bg-primary text-primary-foreground hover:bg-primary/90"
                : "bg-muted text-muted-foreground opacity-50 cursor-not-allowed border border-border"
            }`}
          >
            {validation.isValid ? "Apply Changes" : "Fix Required Notifies to Save"}
          </button>
        </div>
      </div>
    </div>
  )
}
"use client"

import { useState, useMemo } from "react"
import { 
  X, 
  Plus, 
  Trash2, 
  Volume2, 
  Sparkles, 
  Film, 
  Lock,
  AlertTriangle,
  Info
} from "lucide-react"
import { type CustomAnimationEntry, type AnimNotifyEntry } from "@/lib/mock-data"
import { validateMontageNotifies } from "@/lib/action-rules"
import { SearchableSelect } from "@/components/ui/searchable-select"
import { cn } from "@/lib/utils"

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
  // Separate Sequence vs Montage notifies
  const initialSeq = useMemo(() => {
    if (Array.isArray(anim.sequence_notifies)) return anim.sequence_notifies
    return (anim.notifies || []).filter((n) => n.Source === "sequence")
  }, [anim.sequence_notifies, anim.notifies])

  const initialMontage = useMemo(() => {
    if (Array.isArray(anim.montage_notifies)) return anim.montage_notifies
    return (anim.notifies || []).filter((n) => n.Source === "montage")
  }, [anim.montage_notifies, anim.notifies])

  const [seqNotifies, setSeqNotifies] = useState<AnimNotifyEntry[]>(initialSeq)
  const [montNotifies, setMontNotifies] = useState<AnimNotifyEntry[]>(initialMontage)
  const [activeTab, setActiveTab] = useState<"sequence" | "montage">("sequence")

  // READ-ONLY SEQUENCE DURATION (From Blender Sidecar)
  const duration = useMemo(() => {
    if (typeof anim.duration === "number" && anim.duration > 0) {
      return anim.duration
    }
    return 0.0
  }, [anim.duration])

  const frameCount = useMemo(() => {
    return duration > 0 ? Math.round(duration * 30) : 0
  }, [duration])

  // New notify form states
  const [seqNotifyType, setSeqNotifyType] = useState<"PalAttackCollision" | "PalEffect" | "PlayNiagaraEffect" | "Custom">("PalAttackCollision")
  const [seqCustomName, setSeqCustomName] = useState("")
  const [seqTime, setSeqTime] = useState(0.1)
  const [seqDuration, setSeqDuration] = useState(0.2)
  const [seqTrack, setSeqTrack] = useState(1)
  const [seqBone, setSeqBone] = useState("Socket_Mouth")
  const [seqWaza, setSeqWaza] = useState(`Unique_${basePal}_Bite`)
  const [seqNiagara, setSeqNiagara] = useState("")

  const [montNotifyType, setMontNotifyType] = useState<"PalFacialEye" | "AkEvent_C" | "BP_FootStep_C" | "PlayMontageNotifyWindow" | "Custom">("PalFacialEye")
  const [montCustomName, setMontCustomName] = useState("")
  const [montTime, setMontTime] = useState(0.1)
  const [montDuration, setMontDuration] = useState(0.0)
  const [montTrack, setMontTrack] = useState(0)
  const [montEyeType, setMontEyeType] = useState("Close")
  const [montAudioEvent, setMontAudioEvent] = useState(`AKE_UniqueSkill_${basePal}_Start`)
  const [montEventName, setMontEventName] = useState("Move1")

  // Available sequence assets
  const availableSequences = useMemo(() => {
    const seqs = new Set<string>()
    Object.values(allAnims).forEach((entry) => {
      if (entry.sequence_asset) seqs.add(entry.sequence_asset)
      if (entry.nla_track_name) seqs.add(`AS_${modName}_${entry.nla_track_name}`)
    })
    return Array.from(seqs).sort()
  }, [allAnims, modName])

  const defaultSequence = anim.sequence_asset || (anim.nla_track_name ? `AS_${modName}_${anim.nla_track_name}` : "")
  const [selectedSequence, setSelectedSequence] = useState<string>(defaultSequence)

  // STRICT OUT-OF-BOUNDS CALCULATION: Only inspect start time!
  const isNotifyOOB = (n: AnimNotifyEntry) => {
    if (duration <= 0) return false
    return n.Time > duration + 0.0001
  }

  const seqOOBCount = useMemo(() => seqNotifies.filter(isNotifyOOB).length, [seqNotifies, duration])
  const montOOBCount = useMemo(() => montNotifies.filter(isNotifyOOB).length, [montNotifies, duration])
  const totalOOBCount = seqOOBCount + montOOBCount

  // Action Rules Validation (Treated as informative, non-blocking)
  const validation = useMemo(() => {
    const actionLookup = anim.nla_track_name || anim.display_name || animKey
    const all = [...seqNotifies, ...montNotifies]
    return validateMontageNotifies(actionLookup, all)
  }, [anim.nla_track_name, anim.display_name, animKey, seqNotifies, montNotifies])

  // Update existing notify fields inline
  const updateNotifyField = (
    index: number,
    field: "Time" | "Duration" | "Track",
    value: number,
    isSequence: boolean
  ) => {
    const setter = isSequence ? setSeqNotifies : setMontNotifies
    setter((prev) =>
      prev.map((n, i) => (i === index ? { ...n, [field]: value } : n))
    )
  }

  const removeNotify = (index: number, isSequence: boolean) => {
    const setter = isSequence ? setSeqNotifies : setMontNotifies
    setter((prev) => prev.filter((_, i) => i !== index))
  }

  const handleAddSeqNotify = () => {
    const name = seqNotifyType === "Custom" ? (seqCustomName.trim() || "PalCustomNotify") : seqNotifyType
    const entry: AnimNotifyEntry = {
      Name: name,
      Time: Number(seqTime) || 0.0,
      Duration: ["PalAttackCollision", "PalEffect"].includes(seqNotifyType) ? Number(seqDuration) || 0.0 : 0.0,
      Track: Number(seqTrack) || 0,
      Source: "sequence",
      AttachBone: seqBone.trim() || undefined,
      WazaID: seqNotifyType === "PalAttackCollision" ? (seqWaza.trim() || undefined) : undefined,
      NiagaraSystem: ["PalEffect", "PlayNiagaraEffect"].includes(seqNotifyType) ? (seqNiagara.trim() || undefined) : undefined,
    }
    setSeqNotifies((prev) => [...prev, entry])
  }

  const handleAddMontNotify = () => {
    const name = montNotifyType === "Custom" ? (montCustomName.trim() || "PalCustomNotify") : montNotifyType
    const entry: AnimNotifyEntry = {
      Name: name,
      Time: Number(montTime) || 0.0,
      Duration: montNotifyType === "PlayMontageNotifyWindow" ? Number(montDuration) || 0.0 : 0.0,
      Track: Number(montTrack) || 0,
      Source: "montage",
      EyeType: montNotifyType === "PalFacialEye" ? montEyeType : undefined,
      AudioEvent: montNotifyType === "AkEvent_C" ? (montAudioEvent.trim() || undefined) : undefined,
      EventName: montNotifyType === "PlayMontageNotifyWindow" ? (montEventName.trim() || undefined) : undefined,
    }
    setMontNotifies((prev) => [...prev, entry])
  }

  const handleSave = async () => {
    if (totalOOBCount > 0) {
      onNotify(
        `Cannot save! ${totalOOBCount} notify(s) have a start time past the animation duration (${duration.toFixed(4)}s). Reduce timestamps to fit inside keyframes.`,
        "error"
      )
      return
    }

    try {
      if (onSaveEntry) {
        await onSaveEntry({
          sequence_asset: selectedSequence,
          sequence_notifies: seqNotifies,
          montage_notifies: montNotifies,
        })
      }

      if (!validation.isValid) {
        const missingList = validation.missingRequired.map((r) => r.Key).join(", ")
        onNotify(`Saved with warnings: Missing recommended action notifies (${missingList}).`, "warning")
      } else {
        onNotify("Animation sequence & montage notifies saved successfully! ;3", "success")
      }

      onSaved()
      onClose()
    } catch (err: any) {
      onNotify(`Failed to save settings: ${err.message || err}`, "error")
    }
  }

  return (
    <div className="fixed inset-0 z-[110] flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-fade-in">
      <div className="bg-card border border-border rounded-xl shadow-2xl w-full max-w-3xl flex flex-col overflow-hidden max-h-[90vh]">
        
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-border bg-muted/20 shrink-0">
          <div className="flex flex-col">
            <span className="text-[10px] font-mono text-primary font-bold uppercase tracking-wider">
              Notify Timing &amp; Event Editor
            </span>
            <h3 className="font-bold text-sm text-foreground">{anim.display_name}</h3>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground cursor-pointer">
            <X className="size-4" />
          </button>
        </div>

        <div className="p-5 flex flex-col gap-4 overflow-y-auto flex-1">
          {/* SEQUENCE ASSIGNMENT & READ-ONLY DURATION DISPLAY */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-3.5 rounded-lg border border-border/60 bg-muted/30">
            {/* Sequence Selector */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider flex items-center gap-1.5">
                <Film className="size-3.5 text-primary" />
                Assigned Animation Sequence
              </label>
              <SearchableSelect
                value={selectedSequence}
                onChange={(val) => setSelectedSequence(val)}
                options={availableSequences.map((seq) => ({ value: seq, label: seq }))}
                placeholder="-- Select Sequence (AS_) --"
                emptyText="No matching sequences found."
              />
            </div>

            {/* Read-Only Animation Length */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider flex items-center gap-1.5">
                <Lock className="size-3 text-muted-foreground" />
                Baked Timeline Duration (Blender)
              </label>
              <div className="flex items-center justify-between h-9 px-3 rounded border border-border bg-background/80 text-xs font-mono select-none">
                {duration > 0 ? (
                  <>
                    <span className="font-bold text-foreground">
                      {duration.toFixed(4)}s
                    </span>
                    <span className="text-muted-foreground text-[10px]">
                      {frameCount} frames @ 30 FPS
                    </span>
                  </>
                ) : (
                  <span className="text-muted-foreground/60 italic text-[11px] flex items-center gap-1">
                    <Info className="size-3" />
                    Duration not found in sidecar (Run Sync Layout)
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* OUT-OF-BOUNDS WARNING BANNER */}
          {totalOOBCount > 0 && (
            <div className="p-3.5 rounded-lg border border-status-error/60 bg-status-error/15 text-status-error text-xs flex items-center gap-3 animate-pulse">
              <AlertTriangle className="size-5 shrink-0" />
              <div className="flex-1 leading-relaxed">
                <strong>{totalOOBCount} Notify Start Time(s) Out of Bounds!</strong>
                <p className="text-[11px] opacity-90 mt-0.5">
                  Notify start times placed past the animation duration (<code className="font-bold underline">{duration.toFixed(4)}s</code>) will never trigger in-game. Reduce timestamps or extend keyframes in Blender to save.
                </p>
              </div>
            </div>
          )}

          {/* DUAL NOTIFY TABS */}
          <div className="flex items-center border-b border-border gap-2">
            <button
              type="button"
              onClick={() => setActiveTab("sequence")}
              className={cn(
                "flex items-center gap-2 pb-2 px-3 text-xs font-bold uppercase tracking-wider transition-colors cursor-pointer border-b-2",
                activeTab === "sequence"
                  ? "border-cyan-400 text-cyan-400"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              <Sparkles className="size-3.5" />
              Sequence Notifies (AS_)
              <span className={cn(
                "text-[10px] px-1.5 py-0.2 rounded-full font-mono",
                seqOOBCount > 0 ? "bg-status-error text-white font-bold" : "bg-cyan-950 text-cyan-300"
              )}>
                {seqNotifies.length}
              </span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("montage")}
              className={cn(
                "flex items-center gap-2 pb-2 px-3 text-xs font-bold uppercase tracking-wider transition-colors cursor-pointer border-b-2",
                activeTab === "montage"
                  ? "border-purple-400 text-purple-400"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              <Volume2 className="size-3.5" />
              Montage Notifies (AM_)
              <span className={cn(
                "text-[10px] px-1.5 py-0.2 rounded-full font-mono",
                montOOBCount > 0 ? "bg-status-error text-white font-bold" : "bg-purple-950 text-purple-300"
              )}>
                {montNotifies.length}
              </span>
            </button>
          </div>

          {/* TAB 1: SEQUENCE NOTIFIES (AS_) */}
          {activeTab === "sequence" && (
            <div className="flex flex-col gap-3">
              <span className="text-[11px] text-muted-foreground leading-tight">
                Notifies serialized into the <strong>AnimSequence</strong> asset (hitboxes, attacks, particle trails).
              </span>

              {seqNotifies.length === 0 ? (
                <p className="text-xs text-muted-foreground italic py-4 text-center border border-dashed border-border rounded-lg">
                  No sequence notifies registered.
                </p>
              ) : (
                <div className="flex flex-col gap-2 max-h-52 overflow-y-auto pr-1">
                  {seqNotifies.map((n, idx) => {
                    const isOOB = isNotifyOOB(n)
                    return (
                      <div
                        key={idx}
                        className={cn(
                          "flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-2.5 rounded-lg border text-xs font-mono transition-all",
                          isOOB
                            ? "border-status-error bg-status-error/15 text-status-error ring-1 ring-status-error/40 animate-pulse"
                            : "border-border/60 bg-muted/30 text-foreground"
                        )}
                      >
                        <div className="flex flex-col min-w-0 flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-[9px] px-1 rounded bg-cyan-950 text-cyan-300 border border-cyan-800/60 font-bold uppercase">
                              AS
                            </span>
                            <span className="font-bold text-foreground truncate">{n.Name}</span>
                            {isOOB && (
                              <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-status-error text-white uppercase tracking-wider flex items-center gap-1 shrink-0">
                                <AlertTriangle className="size-2.5" />
                                START TIME OOB ({n.Time.toFixed(4)}s &gt; {duration.toFixed(4)}s)
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-2 text-[10px] text-muted-foreground pl-6 truncate mt-0.5">
                            {n.AttachBone && <span>Bone: <strong className="text-foreground">{n.AttachBone}</strong></span>}
                            {n.WazaID && <span>Waza: <strong className="text-foreground">{n.WazaID}</strong></span>}
                            {n.NiagaraSystem && <span>VFX: <strong className="text-foreground">{n.NiagaraSystem}</strong></span>}
                          </div>
                        </div>

                        {/* Editable Time & Duration */}
                        <div className="flex items-center gap-2 shrink-0">
                          <div className="flex items-center gap-1 bg-background border border-border rounded px-2 py-1">
                            <span className="text-[9px] uppercase font-bold text-muted-foreground select-none">Time:</span>
                            <input
                              type="number"
                              step="0.02"
                              min="0"
                              value={n.Time}
                              onChange={(e) => updateNotifyField(idx, "Time", parseFloat(e.target.value) || 0, true)}
                              className="w-16 bg-transparent text-xs font-mono font-bold text-foreground focus:outline-none"
                            />
                            <span className="text-[9px] text-muted-foreground select-none">s</span>
                          </div>

                          <div className="flex items-center gap-1 bg-background border border-border rounded px-2 py-1">
                            <span className="text-[9px] uppercase font-bold text-muted-foreground select-none">Dur:</span>
                            <input
                              type="number"
                              step="0.02"
                              min="0"
                              value={n.Duration || 0}
                              onChange={(e) => updateNotifyField(idx, "Duration", parseFloat(e.target.value) || 0, true)}
                              className="w-14 bg-transparent text-xs font-mono font-bold text-foreground focus:outline-none"
                            />
                            <span className="text-[9px] text-muted-foreground select-none">s</span>
                          </div>

                          <button
                            type="button"
                            onClick={() => removeNotify(idx, true)}
                            className="text-muted-foreground hover:text-status-error p-1.5 rounded hover:bg-muted/50 cursor-pointer transition-colors shrink-0"
                            title="Delete notify"
                          >
                            <Trash2 className="size-3.5" />
                          </button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}

              {/* Add Sequence Notify Form */}
              <div className="border-t border-border/50 pt-3 flex flex-col gap-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                  Add Sequence Notify
                </span>
                <div className="grid grid-cols-4 gap-2">
                  <div className="flex flex-col gap-1">
                    <label className="text-[9px] uppercase font-bold text-muted-foreground">Preset</label>
                    <select
                      value={seqNotifyType}
                      onChange={(e) => setSeqNotifyType(e.target.value as any)}
                      className="bg-background border border-border rounded px-2 py-1 text-xs text-foreground cursor-pointer"
                    >
                      <option value="PalAttackCollision">PalAttackCollision</option>
                      <option value="PalEffect">PalEffect (State)</option>
                      <option value="PlayNiagaraEffect">PlayNiagaraEffect (Instant)</option>
                      <option value="Custom">Custom Name</option>
                    </select>
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-[9px] uppercase font-bold text-muted-foreground">Time (s)</label>
                    <input
                      type="number"
                      step="0.05"
                      min="0"
                      value={seqTime}
                      onChange={(e) => setSeqTime(parseFloat(e.target.value) || 0)}
                      className="bg-background border border-border rounded px-2 py-1 text-xs text-foreground font-mono"
                    />
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-[9px] uppercase font-bold text-muted-foreground">Duration (s)</label>
                    <input
                      type="number"
                      step="0.05"
                      min="0"
                      value={seqDuration}
                      onChange={(e) => setSeqDuration(parseFloat(e.target.value) || 0)}
                      className="bg-background border border-border rounded px-2 py-1 text-xs text-foreground font-mono"
                    />
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-[9px] uppercase font-bold text-muted-foreground">Track</label>
                    <input
                      type="number"
                      min="0"
                      max="10"
                      value={seqTrack}
                      onChange={(e) => setSeqTrack(parseInt(e.target.value) || 0)}
                      className="bg-background border border-border rounded px-2 py-1 text-xs text-foreground font-mono"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-2">
                  {seqNotifyType === "Custom" ? (
                    <div className="flex flex-col gap-1 col-span-2">
                      <label className="text-[9px] uppercase font-bold text-muted-foreground">Custom Name</label>
                      <input
                        type="text"
                        placeholder="PalCustomNotify"
                        value={seqCustomName}
                        onChange={(e) => setSeqCustomName(e.target.value)}
                        className="bg-background border border-border rounded px-2 py-1 text-xs text-foreground font-mono"
                      />
                    </div>
                  ) : seqNotifyType === "PalAttackCollision" ? (
                    <div className="flex flex-col gap-1 col-span-2">
                      <label className="text-[9px] uppercase font-bold text-muted-foreground">Waza ID</label>
                      <input
                        type="text"
                        value={seqWaza}
                        onChange={(e) => setSeqWaza(e.target.value)}
                        className="bg-background border border-border rounded px-2 py-1 text-xs text-foreground font-mono"
                      />
                    </div>
                  ) : (
                    <div className="flex flex-col gap-1 col-span-2">
                      <label className="text-[9px] uppercase font-bold text-muted-foreground">Niagara System</label>
                      <input
                        type="text"
                        placeholder="NS_UniqueSkill_..."
                        value={seqNiagara}
                        onChange={(e) => setSeqNiagara(e.target.value)}
                        className="bg-background border border-border rounded px-2 py-1 text-xs text-foreground font-mono"
                      />
                    </div>
                  )}

                  <div className="flex flex-col gap-1">
                    <label className="text-[9px] uppercase font-bold text-muted-foreground">Attach Bone</label>
                    <input
                      type="text"
                      value={seqBone}
                      onChange={(e) => setSeqBone(e.target.value)}
                      className="bg-background border border-border rounded px-2 py-1 text-xs text-foreground font-mono"
                    />
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleAddSeqNotify}
                  className="self-end flex items-center gap-1.5 px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs rounded transition-colors cursor-pointer mt-1"
                >
                  <Plus className="size-3.5" /> Add Sequence Notify
                </button>
              </div>
            </div>
          )}

          {/* TAB 2: MONTAGE NOTIFIES (AM_) */}
          {activeTab === "montage" && (
            <div className="flex flex-col gap-3">
              <span className="text-[11px] text-muted-foreground leading-tight">
                Notifies evaluated at the <strong>AnimMontage</strong> level (facial expressions, sounds, jump requests).
              </span>

              {montNotifies.length === 0 ? (
                <p className="text-xs text-muted-foreground italic py-4 text-center border border-dashed border-border rounded-lg">
                  No montage notifies registered.
                </p>
              ) : (
                <div className="flex flex-col gap-2 max-h-52 overflow-y-auto pr-1">
                  {montNotifies.map((n, idx) => {
                    const isOOB = isNotifyOOB(n)
                    return (
                      <div
                        key={idx}
                        className={cn(
                          "flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-2.5 rounded-lg border text-xs font-mono transition-all",
                          isOOB
                            ? "border-status-error bg-status-error/15 text-status-error ring-1 ring-status-error/40 animate-pulse"
                            : "border-border/60 bg-muted/30 text-foreground"
                        )}
                      >
                        <div className="flex flex-col min-w-0 flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-[9px] px-1 rounded bg-purple-950 text-purple-300 border border-purple-800/60 font-bold uppercase">
                              AM
                            </span>
                            <span className="font-bold text-foreground truncate">{n.Name}</span>
                            {isOOB && (
                              <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-status-error text-white uppercase tracking-wider flex items-center gap-1 shrink-0">
                                <AlertTriangle className="size-2.5" />
                                START TIME OOB ({n.Time.toFixed(4)}s &gt; {duration.toFixed(4)}s)
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-2 text-[10px] text-muted-foreground pl-6 truncate mt-0.5">
                            {n.EyeType && <span>Eye: <strong className="text-foreground">{n.EyeType}</strong></span>}
                            {n.AudioEvent && <span>Audio: <strong className="text-foreground">{n.AudioEvent}</strong></span>}
                            {n.EventName && <span>Event: <strong className="text-foreground">{n.EventName}</strong></span>}
                          </div>
                        </div>

                        {/* Editable Time & Duration */}
                        <div className="flex items-center gap-2 shrink-0">
                          <div className="flex items-center gap-1 bg-background border border-border rounded px-2 py-1">
                            <span className="text-[9px] uppercase font-bold text-muted-foreground select-none">Time:</span>
                            <input
                              type="number"
                              step="0.02"
                              min="0"
                              value={n.Time}
                              onChange={(e) => updateNotifyField(idx, "Time", parseFloat(e.target.value) || 0, false)}
                              className="w-16 bg-transparent text-xs font-mono font-bold text-foreground focus:outline-none"
                            />
                            <span className="text-[9px] text-muted-foreground select-none">s</span>
                          </div>

                          <div className="flex items-center gap-1 bg-background border border-border rounded px-2 py-1">
                            <span className="text-[9px] uppercase font-bold text-muted-foreground select-none">Dur:</span>
                            <input
                              type="number"
                              step="0.02"
                              min="0"
                              value={n.Duration || 0}
                              onChange={(e) => updateNotifyField(idx, "Duration", parseFloat(e.target.value) || 0, false)}
                              className="w-14 bg-transparent text-xs font-mono font-bold text-foreground focus:outline-none"
                            />
                            <span className="text-[9px] text-muted-foreground select-none">s</span>
                          </div>

                          <button
                            type="button"
                            onClick={() => removeNotify(idx, false)}
                            className="text-muted-foreground hover:text-status-error p-1.5 rounded hover:bg-muted/50 cursor-pointer transition-colors shrink-0"
                            title="Delete notify"
                          >
                            <Trash2 className="size-3.5" />
                          </button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}

              {/* Add Montage Notify Form */}
              <div className="border-t border-border/50 pt-3 flex flex-col gap-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                  Add Montage Notify
                </span>
                <div className="grid grid-cols-4 gap-2">
                  <div className="flex flex-col gap-1">
                    <label className="text-[9px] uppercase font-bold text-muted-foreground">Preset</label>
                    <select
                      value={montNotifyType}
                      onChange={(e) => setMontNotifyType(e.target.value as any)}
                      className="bg-background border border-border rounded px-2 py-1 text-xs text-foreground cursor-pointer"
                    >
                      <option value="PalFacialEye">PalFacialEye</option>
                      <option value="AkEvent_C">AkEvent_C (Sound)</option>
                      <option value="BP_FootStep_C">BP_FootStep_C</option>
                      <option value="PlayMontageNotifyWindow">PlayMontageNotifyWindow</option>
                      <option value="Custom">Custom Name</option>
                    </select>
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-[9px] uppercase font-bold text-muted-foreground">Time (s)</label>
                    <input
                      type="number"
                      step="0.05"
                      min="0"
                      value={montTime}
                      onChange={(e) => setMontTime(parseFloat(e.target.value) || 0)}
                      className="bg-background border border-border rounded px-2 py-1 text-xs text-foreground font-mono"
                    />
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-[9px] uppercase font-bold text-muted-foreground">Duration (s)</label>
                    <input
                      type="number"
                      step="0.05"
                      min="0"
                      value={montDuration}
                      onChange={(e) => setMontDuration(parseFloat(e.target.value) || 0)}
                      className="bg-background border border-border rounded px-2 py-1 text-xs text-foreground font-mono"
                    />
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-[9px] uppercase font-bold text-muted-foreground">Track</label>
                    <input
                      type="number"
                      min="0"
                      max="10"
                      value={montTrack}
                      onChange={(e) => setMontTrack(parseInt(e.target.value) || 0)}
                      className="bg-background border border-border rounded px-2 py-1 text-xs text-foreground font-mono"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  {montNotifyType === "PalFacialEye" ? (
                    <div className="flex flex-col gap-1 col-span-2">
                      <label className="text-[9px] uppercase font-bold text-muted-foreground">Eye Expression (EyeType)</label>
                      <select
                        value={montEyeType}
                        onChange={(e) => setMontEyeType(e.target.value)}
                        className="bg-background border border-border rounded px-2 py-1 text-xs text-foreground cursor-pointer font-mono"
                      >
                        <option value="Close">Close</option>
                        <option value="Anger">Anger</option>
                        <option value="Default">Default</option>
                        <option value="Smile">Smile</option>
                        <option value="Pain">Pain</option>
                      </select>
                    </div>
                  ) : montNotifyType === "AkEvent_C" ? (
                    <div className="flex flex-col gap-1 col-span-2">
                      <label className="text-[9px] uppercase font-bold text-muted-foreground">Audio Event (AKE_...)</label>
                      <input
                        type="text"
                        value={montAudioEvent}
                        onChange={(e) => setMontAudioEvent(e.target.value)}
                        className="bg-background border border-border rounded px-2 py-1 text-xs text-foreground font-mono"
                      />
                    </div>
                  ) : montNotifyType === "PlayMontageNotifyWindow" ? (
                    <div className="flex flex-col gap-1 col-span-2">
                      <label className="text-[9px] uppercase font-bold text-muted-foreground">Window Event Name</label>
                      <input
                        type="text"
                        value={montEventName}
                        onChange={(e) => setMontEventName(e.target.value)}
                        className="bg-background border border-border rounded px-2 py-1 text-xs text-foreground font-mono"
                      />
                    </div>
                  ) : (
                    <div className="flex flex-col gap-1 col-span-2">
                      <label className="text-[9px] uppercase font-bold text-muted-foreground">Custom Name</label>
                      <input
                        type="text"
                        placeholder="PalCustomNotify"
                        value={montCustomName}
                        onChange={(e) => setMontCustomName(e.target.value)}
                        className="bg-background border border-border rounded px-2 py-1 text-xs text-foreground font-mono"
                      />
                    </div>
                  )}
                </div>

                <button
                  type="button"
                  onClick={handleAddMontNotify}
                  className="self-end flex items-center gap-1.5 px-3 py-1.5 bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs rounded transition-colors cursor-pointer mt-1"
                >
                  <Plus className="size-3.5" /> Add Montage Notify
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-between items-center px-5 py-3.5 border-t border-border bg-muted/10 shrink-0">
          <div className="text-[11px] font-mono text-muted-foreground">
            Total Notifies: <strong className="text-cyan-400">{seqNotifies.length} AS</strong> + <strong className="text-purple-400">{montNotifies.length} AM</strong>
            {totalOOBCount > 0 && <span className="text-status-error font-bold ml-2">({totalOOBCount} OUT OF BOUNDS)</span>}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-3.5 py-1.5 rounded text-xs font-semibold border border-border hover:bg-muted/50 cursor-pointer"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={totalOOBCount > 0}
              className={cn(
                "px-4 py-1.5 rounded text-xs font-bold shadow transition-colors",
                totalOOBCount === 0
                  ? "bg-primary text-primary-foreground hover:bg-primary/90 cursor-pointer"
                  : "bg-muted text-muted-foreground opacity-50 cursor-not-allowed border border-border"
              )}
            >
              {totalOOBCount > 0
                ? `Fix Start Times (${totalOOBCount} OOB)`
                : "Apply Changes"}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
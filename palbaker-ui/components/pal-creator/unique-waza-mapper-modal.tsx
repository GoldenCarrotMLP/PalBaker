"use client"
import { useState, useEffect, useCallback } from "react"
import { PalCreatorAPI, ModManagerAPI } from "@/lib/data-service"
import { CreatorPal, CustomAnimationEntry } from "@/lib/mock-data"
import { Loader2, X, AlertTriangle, Bell, CheckCircle2, XCircle, RefreshCw, Wand2 } from "lucide-react"
import { validateMontageNotifies } from "@/lib/action-rules"
import { EditNotifiesModal } from "@/components/mod-manager/mod-card-expanded/edit-notifies-modal"
import { SearchableSelect } from "@/components/ui/searchable-select"
import { cn } from "@/lib/utils"

interface Props {
  pal: CreatorPal
  wazaId: string
  onClose: () => void
  onConfirm: () => void
  onChangeMove?: () => void
}

export function UniqueWazaMapperModal({ pal, wazaId, onClose, onConfirm, onChangeMove }: Props) {
  const [loading, setLoading] = useState(true)
  const [deps, setDeps] = useState<{ montage_asset: string; clean_track: string }[]>([])
  const [availableSeqs, setAvailableSeqs] = useState<string[]>([])
  const [animsData, setAnimsData] = useState<Record<string, CustomAnimationEntry>>({})
  const [error, setError] = useState<string | null>(null)
  const [activeNotifyKey, setActiveNotifyKey] = useState<string | null>(null)
  const [autofillingTrack, setAutofillingTrack] = useState<string | null>(null)
  const [autofillingAll, setAutofillingAll] = useState(false)

  const basePal = pal.TemplateID || pal.CharacterID
  const modName = pal.CharacterID

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const blendName = `${modName}.blend`

      // 1. Fetch waza dependencies safely (with persistent cache on backend)
      let wazaRes: { deps: any[]; available_sequences: string[] } = { deps: [], available_sequences: [] }
      try {
        wazaRes = await PalCreatorAPI.getWazaDeps(wazaId, modName)
      } catch (e: any) {
        console.warn("Failed to query waza dependencies:", e)
      }
      setDeps(wazaRes.deps || [])

      // 2. Fetch sidecar safely (does NOT abort waza stages if sidecar has a minor issue)
      let anims: Record<string, CustomAnimationEntry> = {}
      try {
        const sidecarRes = await ModManagerAPI.dynamicPalsSidecar(basePal, modName, blendName)
        anims = sidecarRes?.data?.custom_animations?.anims || {}
      } catch (e: any) {
        console.warn("Failed to load sidecar metadata:", e)
      }
      setAnimsData(anims)

      // 3. Populate available sequences combining disk scan + sidecar
      const seqs = new Set<string>()
      ;(wazaRes.available_sequences || []).forEach((s) => seqs.add(s))
      Object.values(anims).forEach((anim) => {
        if (anim.sequence_asset) seqs.add(anim.sequence_asset)
        if (anim.nla_track_name) seqs.add(`AS_${modName}_${anim.nla_track_name}`)
      })
      setAvailableSeqs(Array.from(seqs).sort())
    } catch (err: any) {
      setError(err.message || String(err))
    } finally {
      setLoading(false)
    }
  }, [wazaId, basePal, modName])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleAutofillStage = async (cleanTrack: string, montageKey: string) => {
    try {
      setAutofillingTrack(cleanTrack)
      const data = await PalCreatorAPI.autofillWazaStage(wazaId, cleanTrack, modName)
      if (!data) return

      const bestSeq = availableSeqs.find(
        (s) => s.toLowerCase() === data.suggested_sequence.toLowerCase() ||
               s.toLowerCase().includes(cleanTrack.toLowerCase())
      ) || data.suggested_sequence || availableSeqs[0] || ""

      const targetKey = `AM_${modName}_${cleanTrack}`
      const existing = animsData[targetKey] || animsData[montageKey] || {}

      const payload: CustomAnimationEntry = {
        ...existing,
        category: "UniqueAttack",
        enum_key: `EPalWazaID::${wazaId}`,
        display_name: `Unique: ${cleanTrack.replace(/_/g, ' ')}`,
        montage_asset: targetKey,
        sequence_asset: bestSeq,
        nla_track_name: cleanTrack,
        in_nla: true,
        is_modified: true,
        sequence_notifies: data.sequence_notifies || [],
        montage_notifies: data.montage_notifies || [],
        notifies: [...(data.sequence_notifies || []), ...(data.montage_notifies || [])],
        duration: data.required_duration || existing.duration || 0,
        frame_count: data.required_frames || existing.frame_count || 0
      }

      await ModManagerAPI.editAnimation(basePal, modName, targetKey, payload)
      setAnimsData((prev) => ({ ...prev, [targetKey]: payload }))
    } catch (err: any) {
      setError(`Autofill failed for ${cleanTrack}: ${err.message || err}`)
    } finally {
      setAutofillingTrack(null)
    }
  }

  const handleAutofillAll = async () => {
    try {
      setAutofillingAll(true)
      for (const d of deps) {
        await handleAutofillStage(d.clean_track, d.montage_asset)
      }
    } finally {
      setAutofillingAll(false)
    }
  }

  const handleAssignSequence = async (cleanTrack: string, montageKey: string, seqAsset: string) => {
    const targetKey = `AM_${modName}_${cleanTrack}`
    const existing = animsData[targetKey] || animsData[montageKey] || {}
    
    const seqEntry = animsData[seqAsset] || Object.values(animsData).find((a) => a.sequence_asset === seqAsset)
    const payload: CustomAnimationEntry = {
      ...existing,
      category: "UniqueAttack",
      enum_key: `EPalWazaID::${wazaId}`,
      display_name: `Unique: ${cleanTrack.replace(/_/g, ' ')}`,
      montage_asset: targetKey,
      sequence_asset: seqAsset,
      nla_track_name: cleanTrack,
      in_nla: true,
      is_modified: true,
      notifies: existing.notifies || [],
      sequence_notifies: existing.sequence_notifies || [],
      montage_notifies: existing.montage_notifies || [],
      duration: seqEntry?.duration || existing.duration || 0,
      frame_count: seqEntry?.frame_count || existing.frame_count || 0
    }

    try {
      await ModManagerAPI.editAnimation(basePal, modName, targetKey, payload)
      setAnimsData((prev) => ({ ...prev, [targetKey]: payload }))
    } catch (err: any) {
      setError(err.message || String(err))
    }
  }

  const getAnimEntry = (cleanTrack: string) => {
    const key1 = `AM_${modName}_${cleanTrack}`
    const keySeq = `AS_${modName}_${cleanTrack}`
    if (animsData[key1]) return animsData[key1]
    if (animsData[keySeq]) return animsData[keySeq]
    return Object.values(animsData).find(
      (a) => a.nla_track_name?.toLowerCase() === cleanTrack.toLowerCase() ||
             a.montage_asset?.toLowerCase() === key1.toLowerCase() ||
             a.sequence_asset?.toLowerCase() === keySeq.toLowerCase()
    )
  }

  return (
    <div className="fixed inset-0 z-[120] flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-fade-in">
      <div className="bg-card border border-border rounded-xl shadow-2xl w-full max-w-2xl flex flex-col overflow-hidden max-h-[85vh]">
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-border bg-muted/20 shrink-0">
          <div className="flex flex-col">
            <span className="text-[10px] font-mono text-primary font-bold uppercase tracking-wider">
              Unique Attack Stage Customizer
            </span>
            <h3 className="font-bold text-sm text-foreground">{wazaId.replace(/_/g, ' ')}</h3>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground cursor-pointer">
            <X className="size-4" />
          </button>
        </div>

        <div className="p-5 flex flex-col gap-4 overflow-y-auto flex-1">
          <div className="flex items-center justify-between text-xs text-muted-foreground bg-muted/30 p-2.5 rounded-lg border border-border/50">
            <span>
              This attack has <strong>{deps.length}</strong> animation stage{deps.length !== 1 ? 's' : ''}. Assign each montage to an exported sequence and configure its hitboxes.
            </span>
            <div className="flex items-center gap-2 shrink-0 ml-3">
              <button
                type="button"
                onClick={handleAutofillAll}
                disabled={autofillingAll || deps.length === 0}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-primary/15 border border-primary/40 text-primary hover:bg-primary/25 text-xs font-bold transition-colors cursor-pointer disabled:opacity-50 shadow-xs"
                title="Automatically scrape and apply default hitboxes, particles, and sequence tracks for all stages"
              >
                {autofillingAll ? <Loader2 className="size-3 animate-spin" /> : <Wand2 className="size-3" />}
                <span>Autofix All</span>
              </button>
              {onChangeMove && (
                <button
                  onClick={onChangeMove}
                  className="text-muted-foreground hover:text-foreground underline text-xs cursor-pointer"
                >
                  Change Move
                </button>
              )}
            </div>
          </div>

          {error && (
            <div className="p-3 border border-status-error/40 bg-status-error/10 text-status-error text-xs rounded">
              <AlertTriangle className="size-4 inline mr-2" />
              {error}
            </div>
          )}

          {loading ? (
            <div className="flex flex-col items-center justify-center h-48 gap-3 text-muted-foreground">
              <Loader2 className="size-6 animate-spin text-primary" />
              <span className="text-xs font-mono">Scraping blueprint montages...</span>
            </div>
          ) : deps.length === 0 ? (
            <div className="p-6 border border-dashed border-border rounded text-center text-xs text-muted-foreground italic flex flex-col gap-2">
              <span>No multi-stage montages required for this move.</span>
              <span className="text-[11px] opacity-70">You can safely click confirm to add it to your learnset.</span>
            </div>
          ) : (
            <div className="flex flex-col gap-2.5">
              {availableSeqs.length === 0 && (
                <div className="p-3 border border-status-warning/40 bg-status-warning/10 text-status-warning text-xs rounded flex flex-col gap-1.5">
                  <strong>⚠️ No Animations Dumped</strong>
                  <span>PalBaker could not find any <code>AS_</code> sequences in your workspace. Click <strong>Dump & Map Animations</strong> in the Mod Manager to generate your sequences!</span>
                </div>
              )}
              {deps.map((d) => {
                const entry = getAnimEntry(d.clean_track)
                const seqNotifies = entry?.sequence_notifies ?? (entry?.notifies?.filter((n) => n.Source === "sequence") || [])
                const montNotifies = entry?.montage_notifies ?? (entry?.notifies?.filter((n) => n.Source === "montage") || [])
                const allNotifies = [...seqNotifies, ...montNotifies]
                const check = validateMontageNotifies(d.clean_track, allNotifies)
                const isMapped = Boolean(entry && entry.sequence_asset)
                const targetMontageKey = `AM_${modName}_${d.clean_track}`

                // Timing verification
                const animDur = typeof entry?.duration === "number" && entry.duration > 0 ? entry.duration : 0
                const maxNotifyTime = allNotifies.length > 0 ? Math.max(...allNotifies.map((n) => Number(n.Time || 0))) : 0
                const oobNotifies = animDur > 0 ? allNotifies.filter((n) => Number(n.Time) > animDur + 0.0001) : []
                const isOOB = animDur > 0 ? oobNotifies.length > 0 : false
                const isMissingDuration = animDur === 0 && maxNotifyTime > 0

                return (
                  <div
                    key={d.montage_asset}
                    className={cn(
                      "flex flex-col gap-2 p-3 border rounded-lg transition-colors text-xs",
                      isOOB
                        ? "border-status-error/60 bg-status-error/10"
                        : !check.isValid
                        ? "border-status-error/40 bg-status-error/5"
                        : isMapped
                        ? "border-border/60 bg-muted/20"
                        : "border-status-warning/40 bg-status-warning/5"
                    )}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        {isMapped ? (
                          <CheckCircle2 className="size-4 text-status-success shrink-0" />
                        ) : (
                          <XCircle className="size-4 text-muted-foreground shrink-0" />
                        )}
                        <div className="flex flex-col min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-bold text-sm text-foreground truncate">
                              {d.clean_track.replace(/_/g, ' ')}
                            </span>
                            {isOOB && (
                              <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-status-error text-white uppercase font-mono shrink-0 animate-pulse">
                                Timeline Too Short ({animDur.toFixed(2)}s &lt; {maxNotifyTime.toFixed(2)}s)
                              </span>
                            )}
                            {isMissingDuration && (
                              <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-status-warning text-white uppercase font-mono shrink-0" title="Animation has not been synced from Blender yet. Events require at least this duration.">
                                No Duration Recorded (Needs {maxNotifyTime.toFixed(2)}s)
                              </span>
                            )}
                          </div>
                          <span className="text-[10px] text-muted-foreground font-mono truncate">
                            {targetMontageKey} {animDur > 0 ? `[Duration: ${animDur.toFixed(3)}s]` : ""}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          type="button"
                          onClick={() => handleAutofillStage(d.clean_track, d.montage_asset)}
                          disabled={autofillingTrack === d.clean_track}
                          className="flex items-center gap-1 px-2 py-1.5 rounded-md border border-primary/30 bg-primary/10 text-primary hover:bg-primary/20 transition-colors cursor-pointer text-[10px] font-bold tracking-wider uppercase"
                          title="Import default vanilla notifies, hitboxes, and sequence from original Pal"
                        >
                          {autofillingTrack === d.clean_track ? (
                            <Loader2 className="size-3 animate-spin" />
                          ) : (
                            <Wand2 className="size-3" />
                          )}
                          <span>Autofix</span>
                        </button>
                        {!check.isValid && (
                          <span title={`Missing required notifies: ${check.missingRequired.map((r) => r.Key).join(', ')}`}>
                            <AlertTriangle className="size-3.5 text-status-error animate-pulse" />
                          </span>
                        )}
                        <button
                          type="button"
                          onClick={() => setActiveNotifyKey(targetMontageKey)}
                          className={cn(
                            "flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border transition-colors cursor-pointer text-[10px] font-mono",
                            !check.isValid
                              ? "border-status-error/50 text-status-error hover:bg-status-error/20"
                              : "border-border hover:border-primary text-muted-foreground hover:text-foreground bg-muted/30"
                          )}
                          title="Configure Sequence (AS_) and Montage (AM_) Notifies"
                        >
                          <Bell className={cn("size-3", !check.isValid ? "text-status-error" : "text-primary")} />
                          <span className="text-cyan-400 font-bold">AS:{seqNotifies.length}</span>
                          <span className="opacity-40">|</span>
                          <span className="text-purple-400 font-bold">AM:{montNotifies.length}</span>
                        </button>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 pt-1 border-t border-border/30">
                      <span className="text-[10px] uppercase font-bold text-muted-foreground shrink-0">
                        Assigned Sequence:
                      </span>
                      <div className="flex-1 min-w-0">
                        <SearchableSelect
                          value={entry?.sequence_asset || ""}
                          onChange={(val) => handleAssignSequence(d.clean_track, d.montage_asset, val)}
                          options={availableSeqs.map((s) => ({ value: s, label: s }))}
                          placeholder="-- Search Animation Sequence (AS_) --"
                          emptyText="No matching animation sequences found."
                        />
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        <div className="flex justify-between items-center mt-2 border-t border-border pt-3.5 px-5 pb-4 bg-muted/10 shrink-0">
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground cursor-pointer transition-colors"
          >
            <RefreshCw className={cn("size-3", loading && "animate-spin")} /> Refresh
          </button>
          <div className="flex gap-2.5">
            <button
              onClick={onClose}
              className="px-3.5 py-1.5 rounded text-xs font-semibold border border-border hover:bg-muted/50 cursor-pointer"
            >
              Cancel
            </button>
            <button
              onClick={onConfirm}
              className="px-4 py-1.5 rounded text-xs font-bold bg-primary text-primary-foreground hover:bg-primary/90 shadow cursor-pointer transition-colors"
            >
              Done
            </button>
          </div>
        </div>
      </div>

      {activeNotifyKey && (
        <EditNotifiesModal
          basePal={basePal}
          modName={modName}
          animKey={activeNotifyKey}
          anim={
            animsData[activeNotifyKey] ||
            Object.values(animsData).find(
              (a) =>
                a.montage_asset?.toLowerCase() === activeNotifyKey.toLowerCase() ||
                a.sequence_asset?.toLowerCase() === activeNotifyKey.toLowerCase() ||
                a.nla_track_name?.toLowerCase() === activeNotifyKey.replace(`AM_${modName}_`, '').toLowerCase()
            ) || {
              category: "UniqueAttack",
              enum_key: `EPalWazaID::${wazaId}`,
              display_name: `Unique: ${activeNotifyKey.replace(`AM_${modName}_`, '').replace(/_/g, ' ')}`,
              montage_asset: activeNotifyKey,
              sequence_asset: `AS_${modName}_${activeNotifyKey.replace(`AM_${modName}_`, '')}`,
              nla_track_name: activeNotifyKey.replace(`AM_${modName}_`, ''),
              in_nla: true,
              is_modified: true,
              sequence_notifies: [],
              montage_notifies: [],
            }
          }
          allAnims={animsData}
          onClose={() => setActiveNotifyKey(null)}
          onSaved={loadData}
          onNotify={() => {}}
          onSaveEntry={async (patch) => {
            const current = animsData[activeNotifyKey] || {}
            const merged = { ...current, ...patch }
            await ModManagerAPI.editAnimation(basePal, modName, activeNotifyKey, merged)
            setAnimsData((prev) => ({ ...prev, [activeNotifyKey]: merged as any }))
          }}
        />
      )}
    </div>
  )
}

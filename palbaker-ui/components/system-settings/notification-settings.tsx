"use client"

import { useEffect, useState } from "react"
import {
  NotificationsAPI,
  NOTIFY_GROUP_LABELS,
  type NotificationPrefs,
  type NotifyGroup,
} from "@/lib/data-service"

const GROUP_HINTS: Record<NotifyGroup, string> = {
  cook: "Cook (compile only)",
  cook_pack: "Cook & Pack, Recursive Cook & Pack, Full Pipeline",
  pack: "Pack (package only)",
}

function Toggle({ checked, onChange, disabled }: { checked: boolean; onChange: (v: boolean) => void; disabled?: boolean }) {
  return (
    <label className={`shrink-0 ${disabled ? "opacity-40 cursor-not-allowed" : "cursor-pointer"}`}>
      <div className="relative w-11 h-6">
        <input
          type="checkbox"
          checked={checked}
          disabled={disabled}
          onChange={(e) => onChange(e.target.checked)}
          className="sr-only peer"
        />
        <div className="w-11 h-6 bg-muted border border-border peer-checked:bg-status-success rounded-full transition-colors" />
        <div className="absolute top-0.5 left-0.5 size-5 bg-white rounded-full shadow transition-transform peer-checked:translate-x-5" />
      </div>
    </label>
  )
}

function Row({ title, hint, children }: { title: string; hint: string; children: React.ReactNode }) {
  return (
    <div className="bg-muted/40 rounded-md border border-border p-4 flex items-center justify-between gap-4">
      <div>
        <div className="text-foreground text-sm font-semibold">{title}</div>
        <div className="text-muted-foreground text-xs mt-1 leading-relaxed">{hint}</div>
      </div>
      {children}
    </div>
  )
}

export function NotificationSettings({ onError }: { onError?: (msg: string) => void }) {
  const [prefs, setPrefs] = useState<NotificationPrefs>(NotificationsAPI.getCachedPrefs())

  useEffect(() => {
    const unsub = NotificationsAPI.subscribe(setPrefs)
    NotificationsAPI.loadPrefs(true).then(setPrefs)
    return () => { unsub() }
  }, [])

  async function update(next: NotificationPrefs) {
    setPrefs(next)
    try {
      await NotificationsAPI.savePrefs(next)
    } catch (err: unknown) {
      onError?.(err instanceof Error ? err.message : String(err))
    }
  }

  const setGroup = (g: NotifyGroup, v: boolean) => update({ ...prefs, groups: { ...prefs.groups, [g]: v } })

  return (
    <section className="bg-card rounded-md border border-border p-5 flex flex-col gap-4">
      <div className="flex items-center gap-2 mb-1">
        <span className="size-4 text-primary">🔔</span>
        <h2 className="text-foreground font-bold text-sm uppercase tracking-widest">Notifications</h2>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="flex flex-col gap-3">
          <div className="text-muted-foreground text-xs uppercase tracking-widest">Notify when these jobs finish</div>
          {(Object.keys(NOTIFY_GROUP_LABELS) as NotifyGroup[]).map((g) => (
            <Row key={g} title={NOTIFY_GROUP_LABELS[g].toUpperCase()} hint={GROUP_HINTS[g]}>
              <Toggle checked={prefs.groups[g]} onChange={(v) => setGroup(g, v)} />
            </Row>
          ))}
          <Row title="ALSO NOTIFY ON FAILURE" hint="Show a notification when one of these jobs fails">
            <Toggle checked={prefs.notifyOnFailure} onChange={(v) => update({ ...prefs, notifyOnFailure: v })} />
          </Row>
        </div>

        <div className="flex flex-col gap-3">
          <div className="text-muted-foreground text-xs uppercase tracking-widest">How to notify</div>
          <Row title="WINDOWS POPUP" hint="Jobs that finish close together are merged into one popup">
            <Toggle checked={prefs.popup} onChange={(v) => update({ ...prefs, popup: v })} />
          </Row>
          <Row title="ONLY WHEN IN BACKGROUND" hint="Skip the popup while the PalBaker window is focused">
            <Toggle
              checked={prefs.onlyWhenUnfocused}
              disabled={!prefs.popup}
              onChange={(v) => update({ ...prefs, onlyWhenUnfocused: v })}
            />
          </Row>
          <Row title="SOUND" hint="Play the bell once per notification">
            <Toggle checked={prefs.sound} onChange={(v) => update({ ...prefs, sound: v })} />
          </Row>
          <div className={`bg-muted/40 rounded-md border border-border p-4 flex items-center gap-4 ${prefs.sound ? "" : "opacity-40"}`}>
            <div className="text-foreground text-sm font-semibold shrink-0">VOLUME</div>
            <input
              type="range"
              min={0}
              max={100}
              value={prefs.volume}
              disabled={!prefs.sound}
              onChange={(e) => setPrefs({ ...prefs, volume: Number(e.target.value) })}
              onPointerUp={() => update(prefs)}
              onKeyUp={() => update(prefs)}
              className="flex-1 accent-primary"
            />
            <span className="text-muted-foreground text-xs w-8 text-right">{prefs.volume}%</span>
            <button
              type="button"
              disabled={!prefs.sound}
              onClick={() => NotificationsAPI.playChime(prefs.volume)}
              className="text-xs px-3 py-1 rounded-md border border-border hover:bg-muted disabled:cursor-not-allowed"
            >
              Test
            </button>
          </div>
          <button
            type="button"
            onClick={() => NotificationsAPI.showPopup("PalBaker notifications are on", "You'll get a popup like this when a Cook, Cook & Pack or Pack job finishes.")}
            disabled={!prefs.popup}
            className="self-start text-xs px-3 py-1.5 rounded-md border border-border hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Send test popup
          </button>
        </div>
      </div>
    </section>
  )
}

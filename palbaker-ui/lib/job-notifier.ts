// lib/job-notifier.ts
/**
 * Collects finished Cook / Cook & Pack / Pack jobs and announces them as ONE popup + ONE chime.
 * Jobs that finish within MERGE_WINDOW_MS of each other are merged, so a queue of
 * several jobs never stacks several notifications.
 */
import { NotificationsAPI, NOTIFY_GROUP_LABELS, getNotifyGroup, type NotifyGroup } from "./data-service"

const MERGE_WINDOW_MS = 1500 // wait this long after the last finished job before notifying
const MAX_WAIT_MS = 10000 // never hold a notification longer than this

interface FinishedJob {
  modName: string
  group: NotifyGroup
  ok: boolean
  error?: string
}

let pending: FinishedJob[] = []
let timer: ReturnType<typeof setTimeout> | null = null
let firstPendingAt = 0

// Load saved prefs once so the first finished job already respects them
if (typeof window !== "undefined") void NotificationsAPI.loadPrefs()

export function notifyJobFinished(actionKey: string, modName: string, ok: boolean, error?: string): void {
  const group = getNotifyGroup(actionKey)
  if (!group) return

  const prefs = NotificationsAPI.getCachedPrefs()
  if (!prefs.groups[group]) return
  if (!ok && !prefs.notifyOnFailure) return

  pending.push({ modName, group, ok, error })
  if (pending.length === 1) firstPendingAt = Date.now()

  if (timer) clearTimeout(timer)
  const wait = Math.max(0, Math.min(MERGE_WINDOW_MS, firstPendingAt + MAX_WAIT_MS - Date.now()))
  timer = setTimeout(flush, wait)
}

function firstLine(text?: string): string {
  const line = (text || "").split(/\r?\n/).find((l) => l.trim()) || "Unknown error"
  return line.length > 120 ? line.slice(0, 117) + "..." : line
}

function flush(): void {
  timer = null
  const jobs = pending
  pending = []
  if (jobs.length === 0) return

  const prefs = NotificationsAPI.getCachedPrefs()
  if (prefs.sound) NotificationsAPI.playChime(prefs.volume)

  if (!prefs.popup) return
  if (prefs.onlyWhenUnfocused && typeof document !== "undefined" && document.hasFocus()) return

  let title: string
  let body: string

  if (jobs.length === 1) {
    const j = jobs[0]
    const label = NOTIFY_GROUP_LABELS[j.group]
    title = j.ok ? `${label} finished` : `${label} failed`
    body = j.ok ? `${j.modName} is ready.` : `${j.modName}: ${firstLine(j.error)}`
  } else {
    const failed = jobs.filter((j) => !j.ok).length
    title = failed
      ? `${jobs.length} jobs finished, ${failed} failed`
      : `${jobs.length} jobs finished`
    const lines = jobs.slice(0, 4).map((j) => `${j.ok ? "✓" : "✗"} ${j.modName} (${NOTIFY_GROUP_LABELS[j.group]})`)
    if (jobs.length > 4) lines.push(`+${jobs.length - 4} more`)
    body = lines.join("\n")
  }

  void NotificationsAPI.showPopup(title, body)
}

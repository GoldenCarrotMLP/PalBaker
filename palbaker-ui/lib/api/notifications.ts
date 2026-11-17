// lib/api/notifications.ts
/**
 * Job-completion notifications: Windows popups (tauri-plugin-notification), the bell sound,
 * and the user's notification preferences (persisted in manager_settings.json as one JSON string).
 */
import { invoke } from "@tauri-apps/api/core"
import { isPermissionGranted, requestPermission, sendNotification } from "@tauri-apps/plugin-notification"
import { USE_LIVE_DATA } from "./core"

export type NotifyGroup = "cook" | "cook_pack" | "pack"

export const NOTIFY_GROUP_LABELS: Record<NotifyGroup, string> = {
  cook: "Cook",
  cook_pack: "Cook & Pack",
  pack: "Pack",
}

/** Which notification group a queue action belongs to (null = never notifies). */
export function getNotifyGroup(actionKey: string): NotifyGroup | null {
  switch (actionKey.replace(/-/g, "_")) {
    case "cook_only":
      return "cook"
    case "cook":
    case "recursive_cook":
    case "full":
      return "cook_pack"
    case "pack":
    case "pack_only":
      return "pack"
    default:
      return null
  }
}

export interface NotificationPrefs {
  groups: Record<NotifyGroup, boolean>
  popup: boolean
  sound: boolean
  volume: number // 0..100
  notifyOnFailure: boolean
  onlyWhenUnfocused: boolean
}

export const DEFAULT_NOTIFICATION_PREFS: NotificationPrefs = {
  groups: { cook: true, cook_pack: true, pack: true },
  popup: true,
  sound: true,
  volume: 70,
  notifyOnFailure: true,
  onlyWhenUnfocused: false,
}

const PREFS_KEY = "notification_prefs"

let cachedPrefs: NotificationPrefs = DEFAULT_NOTIFICATION_PREFS
let loadPromise: Promise<NotificationPrefs> | null = null
const listeners = new Set<(p: NotificationPrefs) => void>()

function parsePrefs(config: Record<string, unknown> | undefined): NotificationPrefs {
  const base: NotificationPrefs = {
    ...DEFAULT_NOTIFICATION_PREFS,
    groups: { ...DEFAULT_NOTIFICATION_PREFS.groups },
    // Carry over the old backend toggles if the new key was never saved
    popup: config?.notification_popup !== false && config?.notification_popup !== "False",
    sound: config?.notification_sound !== false && config?.notification_sound !== "False",
  }
  const raw = config?.[PREFS_KEY]
  if (!raw) return base
  try {
    const parsed = (typeof raw === "string" ? JSON.parse(raw) : raw) as Partial<NotificationPrefs>
    return { ...base, ...parsed, groups: { ...base.groups, ...(parsed.groups || {}) } }
  } catch {
    return base
  }
}

export const NotificationsAPI = {
  getCachedPrefs(): NotificationPrefs {
    return cachedPrefs
  },

  async loadPrefs(force = false): Promise<NotificationPrefs> {
    if (!USE_LIVE_DATA) return cachedPrefs
    if (!loadPromise || force) {
      loadPromise = invoke<{ data?: Record<string, unknown> }>("get_config")
        .then((res) => {
          cachedPrefs = parsePrefs(res?.data)
          listeners.forEach((l) => l(cachedPrefs))
          return cachedPrefs
        })
        .catch(() => cachedPrefs)
    }
    return loadPromise
  },

  async savePrefs(prefs: NotificationPrefs): Promise<void> {
    cachedPrefs = prefs
    listeners.forEach((l) => l(prefs))
    if (USE_LIVE_DATA) {
      await invoke("set_config", { key: PREFS_KEY, value: JSON.stringify(prefs) })
    }
  },

  subscribe(listener: (p: NotificationPrefs) => void): () => void {
    listeners.add(listener)
    return () => listeners.delete(listener)
  },

  playChime(volume: number = cachedPrefs.volume): void {
    try {
      const audio = new Audio("/sounds/bell.mp3")
      audio.volume = Math.min(1, Math.max(0, volume / 100))
      void audio.play().catch(() => {})
    } catch {
      // Audio unavailable (e.g. during static export)
    }
  },

  async showPopup(title: string, body: string): Promise<void> {
    if (!USE_LIVE_DATA) {
      console.info(`[notification] ${title}: ${body}`)
      return
    }
    try {
      let granted = await isPermissionGranted()
      if (!granted) granted = (await requestPermission()) === "granted"
      if (granted) sendNotification({ title, body })
    } catch (err) {
      console.error("Desktop notification failed:", err)
    }
  },
}

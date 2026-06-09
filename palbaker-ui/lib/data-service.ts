/**
 * Data Service Layer
 *
 * Abstraction over mock vs live data. Switch between mock and live by changing
 * the USE_LIVE_DATA flag or environment variable.
 *
 * All page components import from here, so switching is a single point change.
 */

import { mockModList, mockSpawnerCache, mockCreatorList, mockEnvStatus } from "./mock-data"
import type { ModItem, CreatorItem, EnvStatusType } from "./mock-data"

const USE_LIVE_DATA = process.env.NEXT_PUBLIC_USE_LIVE_DATA === "true"

/**
 * Module Manager API
 */
export const ModManagerAPI = {
  /**
   * Get all mods in workspace
   * Live: calls `tauri:manager:list` or Python CLI via IPC
   */
  async list(): Promise<ModItem[]> {
    if (USE_LIVE_DATA) {
      // TODO: Implement Tauri invoke or fetch to Python server
      // return await invoke("manager_list")
      throw new Error("Live data not yet configured")
    }
    return mockModList
  },

  /**
   * Get single mod details
   */
  async get(modId: string): Promise<ModItem | null> {
    const mods = await this.list()
    return mods.find((m) => m.id === modId) || null
  },
}

/**
 * Pal Creator API
 */
export const PalCreatorAPI = {
  /**
   * Get list of all creator Pals
   * Live: calls `tauri:creator:list` or Python CLI
   */
  async list(): Promise<CreatorItem[]> {
    if (USE_LIVE_DATA) {
      // TODO: Implement live fetch
      throw new Error("Live data not yet configured")
    }
    return mockCreatorList
  },

  /**
   * Get spawner cache (location names → spawn IDs)
   * Live: fetches from `pythoncli/deps/monster_spawners_cache.json` or Python endpoint
   */
  async getSpawners(): Promise<Record<string, string>> {
    if (USE_LIVE_DATA) {
      // TODO: Implement live fetch
      throw new Error("Live data not yet configured")
    }
    return mockSpawnerCache
  },

  /**
   * Create or update a Pal
   */
  async save(pal: CreatorItem): Promise<CreatorItem> {
    if (USE_LIVE_DATA) {
      // TODO: Implement tauri:creator:save or Python POST
      throw new Error("Live data not yet configured")
    }
    // In mock mode, just return the pal as-is (no persistence)
    return pal
  },
}

/**
 * System Settings API
 */
export const SystemSettingsAPI = {
  /**
   * Get environment status (UE5, Blender, etc.)
   */
  async getEnvStatus(): Promise<EnvStatusType> {
    if (USE_LIVE_DATA) {
      // TODO: Implement tauri:env:status
      throw new Error("Live data not yet configured")
    }
    return mockEnvStatus
  },

  /**
   * Update environment path
   */
  async updatePath(key: string, value: string): Promise<void> {
    if (USE_LIVE_DATA) {
      // TODO: Implement tauri:env:set-path or Python API
      throw new Error("Live data not yet configured")
    }
    // In mock mode, just succeed silently
  },
}

/**
 * Console/Build API
 */
export const BuildConsoleAPI = {
  /**
   * Get live logs stream (subscribe to updates)
   * Live: sets up Tauri event listener or WebSocket to Python server
   */
  subscribe(callback: (log: string) => void): () => void {
    if (USE_LIVE_DATA) {
      // TODO: Implement tauri:listen("console_log") or WebSocket
      throw new Error("Live data not yet configured")
    }
    // In mock mode, return no-op unsubscribe
    return () => {}
  },
}

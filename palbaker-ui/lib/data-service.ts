/**
 * Data Service Layer
 *
 * Abstraction over mock vs live data. Automatically detects environment:
 * - pnpm dev: Uses mock data (TAURI_MODE not set)
 * - pnpm tauri dev: Uses live data from Python CLI (TAURI_MODE=true)
 *
 * All page components import from here, so switching is automatic.
 */

import { mockModList, mockSpawnerCache, mockCreatorList, mockEnvStatus, mockConfig } from "./mock-data"
import type { ModItem, CreatorItem, EnvStatusType } from "./mock-data"

import { invoke } from "@tauri-apps/api/core"
import { listen } from "@tauri-apps/api/event"

// Automatically true when running "pnpm tauri dev" (TAURI_MODE env var set in tauri.conf.json)
// False when running "pnpm dev" (regular Next.js dev)
const USE_LIVE_DATA = typeof window !== "undefined" && (window as any).__TAURI_INTERNALS__ !== undefined;

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
      try {
        const response = await invoke<{ status: string; data: ModItem[] }>("manager_list")
        return response.data || []
      } catch (err) {
        console.error("manager_list failed, falling back to mock:", err)
        return mockModList
      }
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

  async runAction(modName: string, action: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try {
        return await invoke("run_mod_action", { modName, action })
      } catch (err) {
        console.error("run_mod_action failed:", err)
        throw err;
      }
    }
    return { status: "success", message: `Mocked action '${action}' completed.` }
  },

  async audioSet(modName: string, cryName: string, path: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try {
        return await invoke("audio_set", { modName, cryName, path })
      } catch (err) {
        console.error("audio_set failed:", err)
        throw err;
      }
    }
    return { status: "success", message: `Mocked audio '${cryName}' override set.` }
  },

  async audioClear(modName: string, cryName: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try {
        return await invoke("audio_clear", { modName, cryName })
      } catch (err) {
        console.error("audio_clear failed:", err)
        throw err;
      }
    }
    return { status: "success", message: `Mocked audio '${cryName}' override cleared.` }
  },

  async audioPlay(modName: string, cryName: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try {
        return await invoke("audio_play", { modName, cryName })
      } catch (err) {
        console.error("audio_play failed:", err)
        throw err;
      }
    }
    return { status: "success", message: `Mocked audio '${cryName}' played.` }
  },

  async altermaticToggle(modName: string, enabled: boolean): Promise<any> {
    if (USE_LIVE_DATA) {
      try {
        return await invoke("altermatic_toggle", { modName, enabled })
      } catch (err) {
        console.error("altermatic_toggle failed:", err)
        throw err;
      }
    }
    return { status: "success", message: `Mocked Altermatic toggle saved.` }
  },

  async altermaticMetadata(modName: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try {
        return await invoke("altermatic_metadata", { modName })
      } catch (err) {
        console.error("altermatic_metadata failed:", err)
        throw err;
      }
    }
    return {
      status: "success",
      has_base_blend: true,
      blend_files: ["base", `${modName}_Variant1.blend`],
      available_materials: ["M_Anubis_body.uasset", "M_Anubis_hair.uasset"],
      category: "Monster"
    }
  },

  async altermaticAdd(modName: string, label: string, custom: boolean, source: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try {
        return await invoke("altermatic_add", { modName, label, custom, source })
      } catch (err) {
        console.error("altermatic_add failed:", err)
        throw err;
      }
    }
    return { status: "success", message: `Mocked variant '${label}' added.` }
  },

  async altermaticDelete(modName: string, index: number): Promise<any> {
    if (USE_LIVE_DATA) {
      try {
        return await invoke("altermatic_delete", { modName, index })
      } catch (err) {
        console.error("altermatic_delete failed:", err)
        throw err;
      }
    }
    return { status: "success", message: `Mocked variant at index ${index} deleted.` }
  },

  async altermaticSave(index: number, data: any): Promise<any> {
    if (USE_LIVE_DATA) {
      try {
        return await invoke("altermatic_save", { index, data: JSON.stringify(data) })
      } catch (err) {
        console.error("altermatic_save failed:", err)
        throw err;
      }
    }
    return { status: "success", message: `Mocked variant saved.` }
  },

  async altermaticOpenBlend(modName: string, blendName: string, category: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try {
        return await invoke("altermatic_open_blend", { modName, blendName, category })
      } catch (err) {
        console.error("altermatic_open_blend failed:", err)
        throw err;
      }
    }
    return { status: "success", message: `Mocked open blend for ${blendName}.` }
  },

  async altermaticSidecar(modName: string, blendName: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try {
        return await invoke("altermatic_sidecar", { modName, blendName })
      } catch (err) {
        console.error("altermatic_sidecar failed:", err)
        throw err;
      }
    }
    return {
      status: "success",
      data: {
        materials: {
          "mi_body": "M_Anubis_body",
          "mi_hair": "M_Anubis_hair"
        }
      }
    }
  },

  async getAltermaticCaches(): Promise<any> {
    if (USE_LIVE_DATA) {
      try {
        const response = await invoke<any>("get_spawners")
        return response.data || {}
      } catch (err) {
        console.error("getAltermaticCaches failed:", err)
        return {}
      }
    }
    return {}
  },

  async setModIcon(modName: string, path: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try {
        return await invoke("set_mod_icon", { modName, path })
      } catch (err) {
        console.error("set_mod_icon failed:", err)
        throw err;
      }
    }
    return { status: "success", message: `Mocked icon set.` }
  },

  async saveModIconBytes(modName: string, filename: string, bytes: number[]): Promise<any> {
    if (USE_LIVE_DATA) {
      try {
        return await invoke("save_mod_icon_bytes", { modName, filename, bytes })
      } catch (err) {
        console.error("save_mod_icon_bytes failed:", err)
        throw err;
      }
    }
    return { status: "success", message: "Mocked icon bytes saved." }
  },

  async saveModAudioBytes(modName: string, cryName: string, filename: string, bytes: number[]): Promise<any> {
    if (USE_LIVE_DATA) {
      try {
        return await invoke("save_mod_audio_bytes", { modName, cryName, filename, bytes })
      } catch (err) {
        console.error("save_mod_audio_bytes failed:", err)
        throw err;
      }
    }
    return { status: "success", message: `Mocked audio '${cryName}' bytes saved.` }
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
      try {
        const response = await invoke<{ status: string; data: CreatorItem[] }>("creator_list")
        return response.data || []
      } catch (err) {
        console.error("creator_list failed, falling back to mock:", err)
        return mockCreatorList
      }
    }
    return mockCreatorList
  },

  /**
   * Get spawner cache (location names → spawn IDs)
   * Live: fetches from `pythoncli/deps/monster_spawners_cache.json` or Python endpoint
   */
  async getSpawners(): Promise<Record<string, string>> {
    if (USE_LIVE_DATA) {
      try {
        const response = await invoke<{ status: string; spawner_locations?: Record<string, string>; data?: any }>("get_spawners")
        // The get-caches CLI action returns spawner_locations as key
        return response.spawner_locations || mockSpawnerCache
      } catch (err) {
        console.error("get_spawners failed, falling back to mock:", err)
        return mockSpawnerCache
      }
    }
    return mockSpawnerCache
  },

  /**
   * Create or update a Pal
   */
  async save(pal: CreatorItem, isNew: boolean = false): Promise<CreatorItem> {
    if (USE_LIVE_DATA) {
      try {
        const response = await invoke<{ status: string; data: CreatorItem }>("creator_save", {
          id: pal.CharacterID,
          data: JSON.stringify(pal),
          isNew: isNew,
          templateId: pal.TemplateID || "Anubis",
        })
        return response.data
      } catch (err) {
        console.error("creator_save failed:", err)
        throw err;
      }
    }
    return pal
  },

  /**
   * Delete a custom standalone Pal
   */
  async delete(id: string): Promise<void> {
    if (USE_LIVE_DATA) {
      try {
        await invoke("creator_delete", { id })
      } catch (err) {
        console.error("creator_delete failed:", err)
        throw err;
      }
    }
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
      try {
        return await invoke<EnvStatusType>("env_status")
      } catch (err) {
        console.error("env_status failed, falling back to mock:", err)
        return mockEnvStatus
      }
    }
    return mockEnvStatus
  },

  /**
   * Get dynamic dynamic application version mapped to git commits
   */
  async getAppVersion(): Promise<string> {
    if (USE_LIVE_DATA) {
      try {
        return await invoke<string>("get_app_version")
      } catch (err) {
        console.error("get_app_version failed, falling back to mock:", err)
        return "v2.4.0-experimental"
      }
    }
    return "v2.4.0-experimental"
  },

  /**
   * Get application configuration from backend (Live Settings)
   */
  async getConfig(): Promise<any> {
    if (USE_LIVE_DATA) {
      try {
        const response = await invoke<any>("get_config")
        return response.data || mockConfig
      } catch (err) {
        console.error("get_config failed, falling back to mock:", err)
        return mockConfig
      }
    }
    return mockConfig
  },

  /**
   * Update configuration setting in backend
   */
  async setConfig(key: string, value: string): Promise<void> {
    if (USE_LIVE_DATA) {
      try {
        await invoke("set_config", { key, value })
      } catch (err) {
        console.error("set_config failed:", err)
        throw err
      }
    }
  },

  /**
   * Update environment path
   */
  async updatePath(key: string, value: string): Promise<void> {
    if (USE_LIVE_DATA) {
      try {
        await invoke("set_config", { key, value })
      } catch (err) {
        console.error("updatePath failed:", err)
        throw err
      }
    }
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
  subscribe(callback: (log: { time: string; level: "SUCCESS" | "INFO" | "ERROR" | "WARNING"; msg: string }) => void): () => void {
    if (USE_LIVE_DATA) {
      const unsubPromise = listen<{ level: string; msg: string }>("console_log", (event) => {
        const time = new Date().toLocaleTimeString("en-US", { hour12: false })
        const level = event.payload.level as "SUCCESS" | "INFO" | "ERROR" | "WARNING"
        callback({
          time,
          level,
          msg: event.payload.msg,
        })
      })

      return () => {
        unsubPromise.then((unsubFn) => unsubFn())
      }
    }
    // In mock mode, return no-op unsubscribe
    return () => {}
  },
}

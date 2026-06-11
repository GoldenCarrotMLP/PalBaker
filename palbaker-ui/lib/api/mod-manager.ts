// lib/api/mod-manager.ts
import { invoke } from "@tauri-apps/api/core"
import { USE_LIVE_DATA, IS_DEV, handleBackendError } from "./core"
import { mockModList, type ModItem } from "../mock-data"

export const ModManagerAPI = {
  async list(): Promise<ModItem[]> {
    if (USE_LIVE_DATA) {
      try {
        const response = await invoke<{ status: string; data: ModItem[] }>("manager_list")
        return response.data || []
      } catch (err) {
        console.error("manager_list failed:", err)
        handleBackendError(err)
      }
    }
    return IS_DEV ? mockModList : []
  },

  async get(modId: string): Promise<ModItem | null> {
    const mods = await this.list()
    return mods.find((m) => m.id === modId) || null
  },

  async runAction(modName: string, action: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("run_mod_action", { modName, action }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked action '${action}' completed.` }
  },

  async audioSet(modName: string, cryName: string, path: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("audio_set", { modName, cryName, path }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked audio '${cryName}' override set.` }
  },

  async audioClear(modName: string, cryName: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("audio_clear", { modName, cryName }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked audio '${cryName}' override cleared.` }
  },

  async audioPlay(modName: string, cryName: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("audio_play", { modName, cryName }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked audio '${cryName}' played.` }
  },

  async altermaticToggle(modName: string, enabled: boolean): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("altermatic_toggle", { modName, enabled }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked Altermatic toggle saved.` }
  },

  async altermaticMetadata(modName: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("altermatic_metadata", { modName }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", has_base_blend: true, blend_files: ["base"], available_materials: [], category: "Monster" }
  },

  async altermaticAdd(modName: string, label: string, custom: boolean, source: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("altermatic_add", { modName, label, custom, source }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked variant '${label}' added.` }
  },

  async altermaticDelete(modName: string, index: number): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("altermatic_delete", { modName, index }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked variant deleted.` }
  },

  async altermaticSave(index: number, data: any): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("altermatic_save", { index, data: JSON.stringify(data) }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked variant saved.` }
  },

  async altermaticOpenBlend(modName: string, blendName: string, category: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("altermatic_open_blend", { modName, blendName, category }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked open blend for ${blendName}.` }
  },

  async altermaticSidecar(modName: string, blendName: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("altermatic_sidecar", { modName, blendName }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", data: { materials: {} } }
  },

  async getAltermaticCaches(): Promise<any> {
    if (USE_LIVE_DATA) {
      try {
        const response = await invoke<any>("get_spawners")
        return response.data || {}
      } catch (err) { handleBackendError(err) }
    }
    return {}
  },

  async setModIcon(modName: string, path: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("set_mod_icon", { modName, path }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked icon set.` }
  },

  async saveModIconBytes(modName: string, filename: string, bytes: number[]): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("save_mod_icon_bytes", { modName, filename, bytes }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: "Mocked icon bytes saved." }
  },

  async saveModAudioBytes(modName: string, cryName: string, filename: string, bytes: number[]): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("save_mod_audio_bytes", { modName, cryName, filename, bytes }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked audio bytes saved.` }
  }
}
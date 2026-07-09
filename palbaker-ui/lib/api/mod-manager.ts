// lib/api/mod-manager.ts
import { invoke } from "@tauri-apps/api/core"
import { USE_LIVE_DATA, IS_DEV, handleBackendError } from "./core"
import { mockModList, type ModItem } from "../mock-data"

export const ModManagerAPI = {
  // Append this method inside the ModManagerAPI dictionary wrapper:
  async setVanillaReplacer(basePal: string, variantName: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try { 
        return await invoke("set_vanilla_replacer", { basePal, variantName });
      } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Vanilla Replacer configured.` }
  },
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

  async runAction(basePal: string, modName: string, action: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try { 
        const res: any = await invoke("run_mod_action", { basePal, modName, action });
        if (res && res.status === "error") {
          throw res;
        }
        return res;
      } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked action '${action}' completed.` }
  },

  async audioSet(basePal: string, modName: string, cryName: string, path: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("audio_set", { basePal, modName, cryName, path }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked audio '${cryName}' override set.` }
  },

  async audioClear(basePal: string, modName: string, cryName: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("audio_clear", { basePal, modName, cryName }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked audio '${cryName}' override cleared.` }
  },

  async audioPlay(basePal: string, modName: string, cryName: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("audio_play", { basePal, modName, cryName }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked audio '${cryName}' played.` }
  },

  async altermaticToggle(basePal: string, modName: string, enabled: boolean): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("altermatic_toggle", { basePal, modName, enabled }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked Altermatic toggle saved.` }
  },

  async altermaticMetadata(basePal: string, modName: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("altermatic_metadata", { basePal, modName }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", has_base_blend: true, blend_files: ["base"], available_materials: [], category: "Monster" }
  },

  async altermaticAdd(basePal: string, modName: string, label: string, custom: boolean, source: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("altermatic_add", { basePal, modName, label, custom, source }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked variant '${label}' added.` }
  },

  async altermaticDelete(basePal: string, modName: string, index: number): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("altermatic_delete", { basePal, modName, index }) } 
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

  async altermaticOpenBlend(basePal: string, modName: string, blendName: string, category: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("altermatic_open_blend", { basePal, modName, blendName, category }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked open blend for ${blendName}.` }
  },

  async altermaticSidecar(basePal: string, modName: string, blendName: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("altermatic_sidecar", { basePal, modName, blendName }) } 
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

  async setModIcon(basePal: string, modName: string, path: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("set_mod_icon", { basePal, modName, path }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked icon set.` }
  },

  async saveModIconBytes(basePal: string, modName: string, filename: string, bytes: number[]): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("save_mod_icon_bytes", { basePal, modName, filename, bytes }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: "Mocked icon bytes saved." }
  },

  async setModPreserveMaterials(basePal: string, modName: string, enabled: boolean): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("set_mod_preserve_materials", { basePal, modName, enabled }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked set preserve materials.` }
  },

  async saveModAudioBytes(basePal: string, modName: string, cryName: string, filename: string, bytes: number[]): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("save_mod_audio_bytes", { basePal, modName, cryName, filename, bytes }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked audio bytes saved.` }
  }
}
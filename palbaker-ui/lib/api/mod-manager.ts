// palbaker-ui/lib/api/mod-manager.ts
import { invoke } from "@tauri-apps/api/core"
import { USE_LIVE_DATA, IS_DEV, handleBackendError } from "./core"
import { mockModList, type ModItem } from "../mock-data"

export const ModManagerAPI = {
  async setModBlacklist(basePal: string, modName: string, blacklistArray: string[]): Promise<any> {
    if (USE_LIVE_DATA) {
      try { 
        return await invoke("set_mod_blacklist", { basePal, modName, blacklistStr: JSON.stringify(blacklistArray) });
      } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked blacklist updated.` }
  },

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

  async dynamicPalsToggle(basePal: string, modName: string, enabled: boolean): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("dynamic_pals_toggle", { basePal, modName, enabled }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked Dynamic Pals toggle saved.` }
  },

  async dynamicPalsMetadata(basePal: string, modName: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("dynamic_pals_metadata", { basePal, modName }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", has_base_blend: true, blend_files: ["base"], available_materials: [], category: "Monster" }
  },

  async dynamicPalsAdd(basePal: string, modName: string, label: string, custom: boolean, source: string, animTarget: string = ""): Promise<any> {
    if (USE_LIVE_DATA) {
      try { 
        return await invoke("dynamic_pals_add", { basePal, modName, label, custom, source, animTarget }) 
      } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked variant '${label}' added.` }

  },

  async dynamicPalsDelete(basePal: string, modName: string, index: number): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("dynamic_pals_delete", { basePal, modName, index }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked variant deleted.` }
  },

  async dynamicPalsSave(index: number, data: any): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("dynamic_pals_save", { index, data: JSON.stringify(data) }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked variant saved.` }
  },

  async dynamicPalsOpenBlend(basePal: string, modName: string, blend_name: string, category: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("dynamic_pals_open_blend", { basePal, modName, blendName: blend_name, category }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked open blend for ${blend_name}.` }
  },

  async dynamicPalsSidecar(basePal: string, modName: string, blend_name: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("dynamic_pals_sidecar", { basePal, modName, blendName: blend_name }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", data: { materials: {} } }
  },

  async getDynamicPalsCaches(): Promise<any> {
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

  async setModPushSetting(basePal: string, modName: string, key: "materials" | "textures" | "animbp", enabled: boolean): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("set_mod_push_setting", { basePal, modName, key, enabled }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked push setting ${key} updated.` }
  },

  async setModPreserveMaterials(basePal: string, modName: string, enabled: boolean): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("set_mod_preserve_materials", { basePal, modName, enabled }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked set preserve materials.` }
  },

  async saveModAudioBytes(basePal: string, modName: string,  cryName: string, filename: string, bytes: number[]): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("save_mod_audio_bytes", { basePal, modName, cryName, filename, bytes }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked audio bytes saved.` }
  }
}
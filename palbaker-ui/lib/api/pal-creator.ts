// lib/api/pal-creator.ts
import { invoke } from "@tauri-apps/api/core"
import { USE_LIVE_DATA, IS_DEV, handleBackendError } from "./core"
import { mockCreatorList, mockSpawnerCache, type CreatorItem } from "../mock-data"

export const PalCreatorAPI = {
  async autofillWazaStage(wazaId: string, track: string, palId: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try {
        const response = await invoke<{ status: string; data: any }>("creator_autofill_waza", { wazaId, track, palId });
        return response.data || null;
      } catch (err) { handleBackendError(err) }
    }
    return null;
  },

  async getWazaDeps(wazaId: string, palId?: string): Promise<{ deps: any[]; available_sequences: string[] }> {
    if (USE_LIVE_DATA) {
      try {
        const response = await invoke<{ status: string; data: any }>("creator_waza_deps", { wazaId, palId });
        if (Array.isArray(response.data)) {
          return { deps: response.data, available_sequences: [] };
        }
        return {
          deps: response.data?.deps || [],
          available_sequences: response.data?.available_sequences || []
        };
      } catch (err) { handleBackendError(err) }
    }
    return { deps: [], available_sequences: [] };
  },

  async list(): Promise<CreatorItem[]> {
    if (USE_LIVE_DATA) {
      try {
        const response = await invoke<{ status: string; data: CreatorItem[] }>("creator_list")
        return response.data || []
      } catch (err) { handleBackendError(err) }
    }
    return IS_DEV ? mockCreatorList : []
  },

  async getSpawners(): Promise<Record<string, string>> {
    if (USE_LIVE_DATA) {
      try {
        const response = await invoke<{ spawner_locations?: Record<string, string>; data?: any }>("get_spawners")
        return response.spawner_locations || (IS_DEV ? mockSpawnerCache : {})
      } catch (err) { handleBackendError(err) }
    }
    return IS_DEV ? mockSpawnerCache : {}
  },

  async add(id: string, templateId: string): Promise<CreatorItem> {
    if (USE_LIVE_DATA) {
      try {
        const response = await invoke<{ status: string; data: CreatorItem }>("creator_add", { id, templateId });
        if (response && response.status === "error") throw response;
        return response.data;
      } catch (err) { handleBackendError(err) }
    }
    return { CharacterID: id, TemplateID: templateId, Name: id, Description: "", ElementType1: "EPalElementType::Normal", BaseHP: 100, BaseAtk: 100, BaseDef: 100, BaseWorkSpeed: 70 } as CreatorItem;
  },

  async save(pal: CreatorItem): Promise<CreatorItem> {
    if (USE_LIVE_DATA) {
      try {
        const response = await invoke<{ status: string; data: CreatorItem; missing_dependencies?: any[] }>("creator_save", {
          id: pal.CharacterID,
          data: JSON.stringify(pal)
        });
        if (response && response.status === "error") throw response;
        const result = response.data || pal;
        if (response.missing_dependencies) {
          result.missing_dependencies = response.missing_dependencies;
        }
        return result;
      } catch (err) { handleBackendError(err) }
    }
    return pal;
  },

  async delete(id: string): Promise<void> {
    if (USE_LIVE_DATA) {
      try { await invoke("creator_delete", { id }) } 
      catch (err) { handleBackendError(err) }
    }
  },

  async refreshBP(id: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try { 
        const res: any = await invoke("creator_refresh_bp", { id });
        if (res && res.status === "error") throw res;
        return res;
      } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked blueprint refresh.` };
  }
}
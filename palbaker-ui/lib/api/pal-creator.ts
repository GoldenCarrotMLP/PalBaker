// lib/api/pal-creator.ts
import { invoke } from "@tauri-apps/api/core"
import { USE_LIVE_DATA, IS_DEV, handleBackendError } from "./core"
import { mockCreatorList, mockSpawnerCache, type CreatorItem } from "../mock-data"

export const PalCreatorAPI = {
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
        const response = await invoke<{ status: string; data: CreatorItem }>("creator_save", {
          id: pal.CharacterID,
          data: JSON.stringify(pal)
        });
        if (response && response.status === "error") throw response;
        return response.data;
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
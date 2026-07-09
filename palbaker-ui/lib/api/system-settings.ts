// lib/api/system-settings.ts
import { invoke } from "@tauri-apps/api/core"
import { USE_LIVE_DATA, IS_DEV, handleBackendError } from "./core"
import { mockEnvStatus, mockConfig, type EnvStatusType } from "../mock-data"

export const SystemSettingsAPI = {
  async getEnvStatus(): Promise<EnvStatusType> {
    if (USE_LIVE_DATA) {
      try { return await invoke<EnvStatusType>("env_status") } 
      catch (err) { handleBackendError(err) }
    }
    return IS_DEV ? mockEnvStatus : { ue4ss: { status: "Not Installed" }, palschema: { status: "Not Installed" } } as EnvStatusType
  },

  async getAppVersion(): Promise<string> {
    if (USE_LIVE_DATA) {
      try { return await invoke<string>("get_app_version") } 
      catch (err) { return "v2.4.0-experimental" }
    }
    return "v2.4.0-experimental"
  },

  async getConfig(): Promise<any> {
    if (USE_LIVE_DATA) {
      try {
        const response = await invoke<any>("get_config")
        return response.data || mockConfig
      } catch (err) { return mockConfig }
    }
    return mockConfig
  },

  async setConfig(key: string, value: string): Promise<void> {
    if (USE_LIVE_DATA) {
      try { await invoke("set_config", { key, value }) } 
      catch (err) { handleBackendError(err) }
    }
  },

  async manageUe4ss(action: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("ue4ss_manage", { action }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked UE4SS action: ${action}` }
  },

async managePalSchema(action: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("palschema_manage", { action }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked PalSchema action: ${action}` }
  },

    async manageCppPlugin(action: string): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("cpp_plugin_manage", { action }) } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: `Mocked C++ Plugin action: ${action}` }
  },
  async buildDb(): Promise<any> {
    if (USE_LIVE_DATA) {
      try { 
        const res: any = await invoke("manager_build_db");
        if (res && res.status === "error") throw res;
        return res;
      } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: "Mocked build-db completed." };
  },

  async verifyEnv(): Promise<any> {
    if (USE_LIVE_DATA) {
      try { 
        const res: any = await invoke("env_verify");
        if (res && res.status === "error") throw res;
        return res;
      } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: "Mocked verify-env completed." };
  },

  async enableRemoteExec(): Promise<any> {
    if (USE_LIVE_DATA) {
      try { 
        const res: any = await invoke("env_enable_remote_exec");
        if (res && res.status === "error") throw res;
        return res;
      } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: "Mocked enable-remote-exec completed." };
  },

  async autodetect(): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("env_autodetect") } 
      catch (err) { handleBackendError(err) }
    }
    return { ue_root: "C:\\Program Files\\Epic Games\\UE_5.1", palworld_exe: "C:\\Steam\\Palworld.exe" }
  },

  async injectAssets(): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("env_inject_assets") } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: "Mocked inject-assets completed." }
  },

  async extractIcons(): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("env_extract_icons") } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: "Mocked extract-icons completed." }
  },

  async pickPath(options: { directory: boolean; filters?: { name: string; extensions: string[] }[] }): Promise<any> {
    if (USE_LIVE_DATA) {
      try {
        const { open } = await import("@tauri-apps/plugin-dialog")
        const selected = await open({ multiple: false, directory: options.directory, filters: options.filters })
        if (selected) {
          const path = Array.isArray(selected) ? selected[0] : selected
          return { status: "success", path }
        }
        return { status: "cancelled", path: "" }
      } catch (err) { handleBackendError(err) }
    }
    return { status: "success", path: "C:\\Mocked\\Path" }
  }
}
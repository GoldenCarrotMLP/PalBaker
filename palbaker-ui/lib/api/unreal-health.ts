// lib/api/unreal-health.ts
import { invoke } from "@tauri-apps/api/core"
import { USE_LIVE_DATA, IS_DEV, handleBackendError } from "./core"

export interface UnrealHealthStatus {
  unreal_running: boolean
  ini_enabled: boolean
  connection_active: boolean
  plugin_loaded: boolean
  diagnostic_code: "FULLY_CONNECTED" | "MISSING_HELPER_PLUGIN" | "NEEDS_RESTART_OR_FIREWALL" | "REMOTE_EXEC_DISABLED" | "UNREAL_CLOSED"
  message: string
}

export const UnrealHealthAPI = {
  async ping(): Promise<UnrealHealthStatus> {
    if (USE_LIVE_DATA) {
      try { return await invoke<UnrealHealthStatus>("unreal_ping") } 
      catch (err) {
        return IS_DEV ? { unreal_running: true, ini_enabled: true, connection_active: true, plugin_loaded: true, diagnostic_code: "FULLY_CONNECTED", message: "Mocked." } : { unreal_running: false, ini_enabled: false, connection_active: false, plugin_loaded: false, diagnostic_code: "UNREAL_CLOSED", message: "Could not connect to Unreal Editor." }
      }
    }
    return IS_DEV ? { unreal_running: true, ini_enabled: true, connection_active: true, plugin_loaded: true, diagnostic_code: "FULLY_CONNECTED", message: "Mocked offline connection active." } : { unreal_running: false, ini_enabled: false, connection_active: false, plugin_loaded: false, diagnostic_code: "UNREAL_CLOSED", message: "Could not connect to Unreal Editor." }
  },

  async launchUnreal(): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("env_launch_unreal") } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: "Mocked launch Unreal Editor." }
  },

  async restartUnreal(): Promise<any> {
    if (USE_LIVE_DATA) {
      try { return await invoke("env_restart_unreal") } 
      catch (err) { handleBackendError(err) }
    }
    return { status: "success", message: "Mocked restart Unreal Editor." }
  }


}
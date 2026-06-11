// lib/api/build-console.ts
import { listen } from "@tauri-apps/api/event"
import { USE_LIVE_DATA } from "./core"

export const BuildConsoleAPI = {
  subscribe(callback: (log: { time: string; level: "SUCCESS" | "INFO" | "ERROR" | "WARNING"; msg: string }) => void): () => void {
    if (USE_LIVE_DATA) {
      const unsubPromise = listen<{ level: string; msg: string }>("console_log", (event) => {
        const time = new Date().toLocaleTimeString("en-US", { hour12: false })
        const level = event.payload.level as "SUCCESS" | "INFO" | "ERROR" | "WARNING"
        callback({ time, level, msg: event.payload.msg })
      })
      return () => { unsubPromise.then((unsubFn) => unsubFn()) }
    }
    return () => {}
  }
}
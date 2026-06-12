import { check, type Update } from '@tauri-apps/plugin-updater'
import { relaunch } from '@tauri-apps/plugin-process'
import { USE_LIVE_DATA } from './core'

export const UpdaterAPI = {
  async checkForUpdates(): Promise<Update | null> {
    if (!USE_LIVE_DATA) return null;
    try {
      return await check();
    } catch (err) {
      console.error("Update check failed:", err);
      return null;
    }
  },
  
  async downloadAndInstall(update: Update, onProgress: (downloaded: number, total: number) => void) {
    let downloaded = 0;
    let contentLength = 0;
    
    await update.downloadAndInstall((event) => {
      if (event.event === 'Started') {
        contentLength = event.data.contentLength || 0;
      } else if (event.event === 'Progress') {
        downloaded += event.data.chunkLength;
        onProgress(downloaded, contentLength);
      }
    });
    
    await relaunch();
  }
}
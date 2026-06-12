"use client"

import { useState } from "react"
import { UpdaterAPI } from "@/lib/data-service"
import { Loader2, DownloadCloud } from "lucide-react"

export function UpdateModal({ update, onClose }: { update: any, onClose: () => void }) {
  const [downloading, setDownloading] = useState(false)
  const [progress, setProgress] = useState({ downloaded: 0, total: 1 })

  const handleInstall = async () => {
    setDownloading(true)
    try {
      await UpdaterAPI.downloadAndInstall(update, (downloaded, total) => {
        setProgress({ downloaded, total: total > 0 ? total : 1 })
      })
    } catch (e) {
      console.error("Failed to install update:", e)
      setDownloading(false)
    }
  }

  const percentage = Math.round((progress.downloaded / progress.total) * 100)

  return (
    <div className="fixed inset-0 z-[999] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
      <div className="bg-card border-2 border-primary/30 rounded-xl max-w-md w-full shadow-2xl p-6 relative flex flex-col items-center text-center gap-4">
        <div className="size-16 rounded-full bg-primary/10 flex items-center justify-center text-primary">
          <DownloadCloud className="size-8" />
        </div>
        
        <h3 className="text-foreground font-extrabold text-lg uppercase tracking-wider">
          New Update Available!
        </h3>
        
        <p className="text-muted-foreground text-sm leading-relaxed">
          Version <span className="text-primary font-bold">{update.version}</span> is ready to be installed! 
          Would you like me to patch PalBaker in the background and restart it for you? ;3
        </p>

        {downloading ? (
          <div className="w-full flex flex-col gap-2 mt-4">
            <div className="flex justify-between text-xs font-mono text-muted-foreground">
              <span>Downloading...</span>
              <span>{percentage}%</span>
            </div>
            <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
              <div 
                className="h-full bg-primary transition-all duration-300" 
                style={{ width: `${percentage}%` }}
              />
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-2.5 w-full mt-2">
            <button
              onClick={handleInstall}
              className="w-full py-2.5 rounded bg-primary text-primary-foreground font-bold text-xs uppercase tracking-wider hover:bg-primary/90 transition-colors shadow flex items-center justify-center gap-2 cursor-pointer"
            >
              Install & Restart
            </button>
            <button
              onClick={onClose}
              className="w-full py-2 border border-border rounded text-muted-foreground hover:text-foreground text-xs font-semibold hover:bg-accent transition-colors cursor-pointer"
            >
              Skip for now
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
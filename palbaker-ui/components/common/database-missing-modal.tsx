"use client"

import { useState } from "react"
import { SystemSettingsAPI } from "@/lib/data-service"
import { Database, Loader2, X, AlertTriangle } from "lucide-react"

interface Props {
  onClose: () => void
  onSuccess?: () => void
}

export function DatabaseMissingModal({ onClose, onSuccess }: Props) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleBuild = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await SystemSettingsAPI.buildDb()
      if (res && res.status === "success") {
        if (onSuccess) onSuccess()
        onClose()
      } else {
        setError(res.message || "Failed to compile localization database.")
      }
    } catch (e: any) {
      console.error(e)
      setError(e.message || String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[110] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="bg-card border border-border rounded-lg shadow-2xl w-full max-w-md flex flex-col p-6 gap-4 animate-in zoom-in-95 duration-200">
        
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-primary">
            <Database className="size-5" />
            <h3 className="font-bold text-lg text-foreground">Pal Database Setup</h3>
          </div>
          {!loading && (
            <button onClick={onClose} className="text-muted-foreground hover:text-foreground cursor-pointer">
              <X className="size-5" />
            </button>
          )}
        </div>

        <p className="text-sm text-foreground/80 leading-relaxed">
          The local Pal database mapping (<code className="text-xs bg-muted px-1 py-0.5 rounded font-mono text-primary">pal_names_map.json</code>) is missing or incomplete. 
          <br /><br />
          PalBaker can automatically extract the latest English localization files directly from your game archives and compile the skills and spawners caches.
        </p>

        {error && (
          <div className="bg-status-error/10 border border-status-error/30 rounded p-3 flex gap-2 items-start text-xs text-status-error">
            <AlertTriangle className="size-4 shrink-0 mt-0.5" />
            <div className="flex-1 whitespace-pre-wrap break-words">{error}</div>
          </div>
        )}

        <div className="flex justify-end gap-3 mt-4 border-t border-border pt-4">
          {!loading && (
            <button 
              onClick={onClose} 
              className="h-9 px-4 rounded text-sm font-semibold border border-input hover:bg-muted/50 cursor-pointer"
            >
              Skip / Cancel
            </button>
          )}
          <button 
            disabled={loading}
            onClick={handleBuild} 
            className="h-9 px-4 rounded text-sm font-semibold bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 cursor-pointer flex items-center gap-2 shadow"
          >
            {loading ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Extracting Game Paks...
              </>
            ) : (
              "Build Database"
            )}
          </button>
        </div>

      </div>
    </div>
  )
}
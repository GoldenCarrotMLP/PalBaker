"use client"

import { useState, useEffect } from "react"
import { UnrealHealthAPI, SystemSettingsAPI } from "@/lib/data-service"
import { AlertTriangle, Terminal, X, ChevronDown, ChevronUp, Loader2, Play, Settings, RefreshCw, Plug } from "lucide-react"
import { cn } from "@/lib/utils"
import { useNav } from "@/lib/nav-context"

interface Props {
  errorText: string
  onClose: () => void
}

export function DiagnosticsModal({ errorText, onClose }: Props) {
  const [showDetails, setShowDetails] = useState(false)
  const [health, setHealth] = useState<any>(null)
  const [config, setConfig] = useState<any>(null)
  const [loadingHealth, setLoadingHealth] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const { setPage } = useNav()

  useEffect(() => {
    async function checkHealth() {
      try {
        const [h, cfg] = await Promise.all([
          UnrealHealthAPI.ping(),
          SystemSettingsAPI.getConfig()
        ])
        setHealth(h)
        setConfig(cfg)
      } catch (e) {
        console.error("Diagnostic verification failed", e)
      } finally {
        setLoadingHealth(false)
      }
    }
    checkHealth()
  }, [])

  const handleLaunch = async () => {
    setActionLoading(true)
    try {
      await UnrealHealthAPI.launchUnreal()
      onClose()
    } catch (e) {
      console.error(e)
    } finally {
      setActionLoading(false)
    }
  }

  const handleRestart = async () => {
    setActionLoading(true)
    try {
      await UnrealHealthAPI.restartUnreal()
      onClose()
    } catch (e) {
      console.error(e)
    } finally {
      setActionLoading(false)
    }
  }

  const handleEnableRemote = async () => {
    setActionLoading(true)
    try {
      await SystemSettingsAPI.enableRemoteExec()
      // Re-ping to update state dynamically
      const res = await UnrealHealthAPI.ping()
      setHealth(res)
    } catch (e) {
      console.error(e)
    } finally {
      setActionLoading(false)
    }
  }

  // --- NEW INTEGRITY SELF-HEALING ACTIONS ---
  const handleInstallPlugin = async () => {
    setActionLoading(true)
    try {
      // The backend 'install' action safely handles both copying binaries and injecting master assets
      await SystemSettingsAPI.managePalSchema("install")
      onClose()
    } catch (e) {
      console.error(e)
    } finally {
      setActionLoading(false)
    }
  }

  const handleInjectAssets = async () => {
    setActionLoading(true)
    try {
      await SystemSettingsAPI.injectAssets()
      onClose()
    } catch (e) {
      console.error(e)
    } finally {
      setActionLoading(false)
    }
  }

  const isUnrealRunning = health?.unreal_running === true
  const isIniEnabled = health?.ini_enabled === true

  const isConfigured = Boolean(
    config?.fmodel_output &&
    config?.ue_root &&
    config?.uproject &&
    config?.blender &&
    config?.palworld_exe
  )

  // Context-Aware Error Detection
  const isMissingPlugin = errorText.includes("missing or outdated in your Unreal project") || errorText.includes("PalBaker C++ Editor Helper Plugin")
  const isMissingAssets = errorText.includes("missing crucial master materials")
  const isConnectionError = !isMissingPlugin && !isMissingAssets

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-card border border-border rounded-lg shadow-2xl w-full max-w-lg flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-status-error/10">
          <div className="flex items-center gap-2 text-status-error">
            <AlertTriangle className="size-5" />
            <span className="font-bold text-sm tracking-wide">ACTION REQUIRED</span>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors cursor-pointer">
            <X className="size-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 flex flex-col gap-4">
          <p className="text-sm text-foreground leading-relaxed font-medium">
            {errorText}
          </p>

          <div className="bg-muted/30 border border-border rounded-md flex flex-col">
            <button 
              onClick={() => { setShowDetails(!showDetails) }}
              className="flex items-center justify-between px-3 py-2 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
            >
              <div className="flex items-center gap-2">
                <Terminal className="size-3.5" />
                Raw Error Output
              </div>
              {showDetails ? <ChevronUp className="size-3.5" /> : <ChevronDown className="size-3.5" />}
            </button>
            {showDetails && (
              <div className="px-3 pb-3 pt-1 text-[10px] font-mono text-muted-foreground whitespace-pre-wrap break-words border-t border-border/50">
                {errorText}
              </div>
            )}
          </div>
          
          {loadingHealth ? (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="size-3.5 animate-spin" />
              Scanning environment status...
            </div>
          ) : (
            <div className="flex flex-col gap-2 mt-2">
              <span className="text-xs font-bold text-muted-foreground uppercase tracking-widest">Recommended Actions</span>
              <div className="flex flex-col gap-2">
                
                {/* 1. Only show system-level fixes if paths are fully set up */}
                {isConfigured && (
                  <>
                    {/* Plugin Installation Fallback */}
                    {isMissingPlugin && (
                      <button 
                        onClick={handleInstallPlugin}
                        disabled={actionLoading}
                        className="flex items-center gap-3 px-4 py-2.5 bg-primary/10 hover:bg-primary/20 border border-primary/30 rounded-md text-primary text-sm font-medium transition-colors cursor-pointer disabled:opacity-50"
                      >
                        {actionLoading ? <Loader2 className="size-4 animate-spin" /> : <span className="text-lg">🔌</span>}
                        {actionLoading ? "Installing... (This may take a minute)" : "Install Helper Plugin & Assets"}
                      </button>
                    )}

                    {/* Master Assets Injection Fallback */}
                    {isMissingAssets && (
                      <button 
                        onClick={handleInjectAssets}
                        disabled={actionLoading}
                        className="flex items-center gap-3 px-4 py-2.5 bg-status-success/10 hover:bg-status-success/20 border border-status-success/30 rounded-md text-status-success text-sm font-medium transition-colors cursor-pointer disabled:opacity-50"
                      >
                        {actionLoading ? <Loader2 className="size-4 animate-spin" /> : <span className="text-lg">📦</span>}
                        {actionLoading ? "Injecting..." : "Inject Master Assets"}
                      </button>
                    )}

                    {/* Unreal Editor Connection Fallbacks */}
                    {isConnectionError && (
                      <>
                        {!isIniEnabled && (
                          <button 
                            onClick={handleEnableRemote}
                            disabled={actionLoading}
                            className="flex items-center gap-3 px-4 py-2.5 bg-primary/10 hover:bg-primary/20 border border-primary/30 rounded-md text-primary text-sm font-medium transition-colors cursor-pointer disabled:opacity-50"
                          >
                            {actionLoading ? <Loader2 className="size-4 animate-spin" /> : <span className="text-lg">🔌</span>}
                            {actionLoading ? "Configuring..." : "Enable Remote Execution"}
                          </button>
                        )}

                        {!isUnrealRunning && (
                          <button 
                            onClick={handleLaunch}
                            disabled={actionLoading}
                            className="flex items-center gap-3 px-4 py-2.5 bg-status-success/10 hover:bg-status-success/20 border border-status-success/30 rounded-md text-status-success text-sm font-medium transition-colors cursor-pointer disabled:opacity-50"
                          >
                            {actionLoading ? <Loader2 className="size-4 animate-spin" /> : <span className="text-lg">🚀</span>}
                            {actionLoading ? "Launching..." : "Launch Unreal Editor"}
                          </button>
                        )}

                        {isUnrealRunning && isIniEnabled && (
                          <button 
                            onClick={handleRestart}
                            disabled={actionLoading}
                            className="flex items-center gap-3 px-4 py-2.5 bg-status-warning/10 hover:bg-status-warning/20 border border-status-warning/30 rounded-md text-status-warning text-sm font-medium transition-colors cursor-pointer disabled:opacity-50"
                          >
                            {actionLoading ? <Loader2 className="size-4 animate-spin" /> : <RefreshCw className="size-4" />}
                            {actionLoading ? "Restarting..." : "Restart Unreal Editor"}
                          </button>
                        )}
                      </>
                    )}
                  </>
                )}

                {/* Always show settings link fallback */}
                <button 
                  onClick={() => { setPage("system-settings"); onClose(); }}
                  disabled={actionLoading}
                  className="flex items-center gap-3 px-4 py-2.5 bg-muted hover:bg-muted/80 border border-border rounded-md text-foreground text-sm font-medium transition-colors cursor-pointer disabled:opacity-50"
                >
                  <span className="text-lg">⚙️</span>
                  {isConfigured ? "Go to Settings" : "Configure Settings Paths"}
                </button>

              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
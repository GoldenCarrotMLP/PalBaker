"use client"

import { useState, useEffect } from "react"
import { UnrealHealthAPI, SystemSettingsAPI } from "@/lib/data-service"
import { AlertTriangle, Terminal, X, ChevronDown, ChevronUp, Loader2, RefreshCw, Copy, Check } from "lucide-react"
import { useNav } from "@/lib/nav-context"
import { parseBackendError, type DiagnosticReport } from "@/lib/error-parser"

type Remediation = DiagnosticReport["remediations"][number]

const REMEDIATION_STYLES: Record<Remediation["style"], string> = {
  primary: "bg-primary/10 hover:bg-primary/20 border-primary/30 text-primary",
  secondary: "bg-muted hover:bg-muted/80 border-border text-foreground",
  warning: "bg-status-warning/10 hover:bg-status-warning/20 border-status-warning/30 text-status-warning",
  danger: "bg-status-error/10 hover:bg-status-error/20 border-status-error/30 text-status-error",
}

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
  const [copiedFolder, setCopiedFolder] = useState(false)
  const [remediationResult, setRemediationResult] = useState<{ ok: boolean; text: string } | null>(null)
  const { setPage } = useNav()

  // 1. Resolve friendly diagnostic mapping variables natively using your parser
  let report = null
  try {
     const parsedTest = JSON.parse(errorText)
     if (parsedTest && parsedTest.friendlyMsg) {
         report = parsedTest
     } else {
         report = parseBackendError(errorText)
     }
  } catch (e) {
     report = parseBackendError(errorText)
  }

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
      const res = await UnrealHealthAPI.ping()
      setHealth(res)
    } catch (e) {
      console.error(e)
    } finally {
      setActionLoading(false)
    }
  }

  const handleInstallPlugin = async () => {
    setActionLoading(true)
    try {
      await SystemSettingsAPI.manageCppPlugin("install")
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

  const isMissingPlugin = errorText.includes("missing or outdated in your Unreal project") || errorText.includes("PalBaker C++ Editor Helper Plugin")
  const isMissingAssets = errorText.includes("missing crucial master materials")
  // Editor launch/restart buttons only help when the editor is the problem (or the cause is unknown)
  const isConnectionError = !isMissingPlugin && !isMissingAssets && (report.category === "UNREAL_CONNECTIVITY" || report.category === "GENERAL_ERROR")

  // The editor buttons above already cover launch/remote-exec, and Settings is always offered below
  const HANDLED_ELSEWHERE: Remediation["actionKey"][] = ["launch_unreal", "enable_remote_exec", "go_to_settings"]
  const extraRemediations = (report.remediations as Remediation[] ?? []).filter(r => !HANDLED_ELSEWHERE.includes(r.actionKey))

  const runRemediation = async (actionKey: Remediation["actionKey"]) => {
    if (actionKey === "close_modal") {
      onClose()
      return
    }
    setActionLoading(true)
    setRemediationResult(null)
    try {
      if (actionKey === "close_game") {
        const res = await SystemSettingsAPI.closeGame()
        setRemediationResult({ ok: true, text: `${res?.message || "Palworld closed."} You can run the action again now.` })
      } else if (actionKey === "autodetect_paths") {
        const results = await SystemSettingsAPI.autodetect()
        const found: string[] = []
        if (results?.ue_root) { await SystemSettingsAPI.setConfig("ue_root", results.ue_root); found.push("Unreal Engine") }
        if (results?.palworld_exe) { await SystemSettingsAPI.setConfig("palworld_exe", results.palworld_exe); found.push("Palworld") }
        if (results?.blender_versions?.length > 0) { await SystemSettingsAPI.setConfig("blender", results.blender_versions[0]); found.push("Blender") }
        setRemediationResult(found.length > 0
          ? { ok: true, text: `Detected and saved: ${found.join(", ")}. Check the rest in Settings, then try again.` }
          : { ok: false, text: "Nothing could be detected automatically. Set the paths by hand in Settings." })
      } else if (actionKey === "rebuild_db") {
        await SystemSettingsAPI.buildDb()
        setRemediationResult({ ok: true, text: "Database rebuilt from the game files. Try the action again." })
      } else if (actionKey === "open_vs_installer") {
        const { openUrl } = await import("@tauri-apps/plugin-opener")
        await openUrl("https://visualstudio.microsoft.com/visual-cpp-build-tools/")
      }
    } catch (e) {
      setRemediationResult({ ok: false, text: e instanceof Error ? e.message : String(e) })
    } finally {
      setActionLoading(false)
    }
  }

  const handleCopyFolder = async () => {
    if (!report.folder) return
    try {
      await navigator.clipboard.writeText(report.folder)
      setCopiedFolder(true)
      setTimeout(() => setCopiedFolder(false), 1500)
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-fade-in">
      <div className="bg-card border border-border rounded-lg shadow-2xl w-full max-w-lg flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-status-error/10">
          <div className="flex items-center gap-2 text-status-error">
            <AlertTriangle className="size-5" />
            <span className="font-bold text-sm tracking-wide uppercase">{report.title}</span>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors cursor-pointer">
            <X className="size-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 flex flex-col gap-4">
          <p className="text-sm text-foreground leading-relaxed font-medium whitespace-pre-line break-words max-h-80 overflow-y-auto">
            {report.friendlyMsg}
          </p>

          {report.detail && (
            <div className="flex flex-col gap-1">
              <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">PalBaker reported</span>
              <div className="bg-muted/30 border border-border rounded-md px-3 py-2 text-xs font-mono text-foreground whitespace-pre-wrap break-words max-h-32 overflow-y-auto select-text">
                {report.detail}
              </div>
            </div>
          )}

          {report.folder && (
            <div className="flex items-start gap-2 bg-muted/30 border border-border rounded-md px-3 py-2">
              <span className="flex-1 text-xs font-mono text-foreground break-all select-all">{report.folder}</span>
              <button
                onClick={handleCopyFolder}
                className="shrink-0 flex items-center gap-1 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
              >
                {copiedFolder ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
                {copiedFolder ? "Copied" : "Copy path"}
              </button>
            </div>
          )}

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
              <div className="px-3 pb-3 pt-1 text-[10px] font-mono text-muted-foreground whitespace-pre-wrap break-words border-t border-border/50 max-h-32 overflow-y-auto">
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

                {/* Fixes suggested by the parsed diagnostic report */}
                {extraRemediations.filter(r => r.actionKey !== "close_modal").map(r => (
                  <button
                    key={r.actionKey}
                    onClick={() => { runRemediation(r.actionKey) }}
                    disabled={actionLoading}
                    className={`flex items-center gap-3 px-4 py-2.5 border rounded-md text-sm font-medium transition-colors cursor-pointer disabled:opacity-50 ${REMEDIATION_STYLES[r.style]}`}
                  >
                    {actionLoading && <Loader2 className="size-4 animate-spin" />}
                    {r.label}
                  </button>
                ))}

                {remediationResult && (
                  <p className={`text-xs leading-relaxed ${remediationResult.ok ? "text-status-success" : "text-status-error"}`}>
                    {remediationResult.text}
                  </p>
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

                {extraRemediations.filter(r => r.actionKey === "close_modal").map(r => (
                  <button
                    key={r.label}
                    onClick={onClose}
                    className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                  >
                    {r.label}
                  </button>
                ))}

              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
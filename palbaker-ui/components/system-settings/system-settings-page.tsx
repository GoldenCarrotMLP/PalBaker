"use client"

import { useState, useEffect } from "react"
import { mockConfig, mockEnvStatus } from "@/lib/mock-data"
import { SystemSettingsAPI } from "@/lib/data-service"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { Folder, RefreshCw, CheckCircle, Database } from "lucide-react"
import { cn } from "@/lib/utils"
import { DiagnosticsModal } from "@/components/common/diagnostics-modal"
import { useNotifications } from "../mod-manager/mod-card-expanded/use-notifications"
import { NotificationToast } from "../mod-manager/mod-card-expanded/notification-toast"
import { DatabaseMissingModal } from "@/components/common/database-missing-modal"

// Importing setup wizards modals
import { PluginInstallModal } from "./setup-wizards/PluginInstallModal"
import { AssetInjectModal } from "./setup-wizards/AssetInjectModal"
import { ConfigFixModal } from "./setup-wizards/ConfigFixModal"

const PIPELINE_ITEMS = [
  { key: "blender_rpc", label: "BLENDER RPC" },
  { key: "ue_live_link", label: "UE LIVE LINK" },
  { key: "asset_watcher", label: "ASSET WATCHER" },
  { key: "build_queue", label: "BUILD QUEUE" },
] as const

type PipelineKey = typeof PIPELINE_ITEMS[number]["key"]

const PIPELINE_COLORS: Record<string, string> = {
  CONNECTED: "text-status-success",
  STANDBY:   "text-status-warning",
  RUNNING:   "text-primary",
  IDLE:      "text-muted-foreground",
}

export function SystemSettingsPage() {
  const [config, setConfig] = useState(mockConfig)
  const [envStatus, setEnvStatus] = useState<any>(mockEnvStatus)
  const [showMappedNames, setShowMappedNames] = useState(true)
  const [diagnosticError, setDiagnosticError] = useState<string | null>(null)
  const { notifications, showNotification, dismissNotification } = useNotifications()

  // Setup Wizards States
  const [activeWizard, setActiveWizard] = useState<"plugin" | "asset" | "config" | null>(null)
  const [verificationResult, setVerificationResult] = useState<any>(null)
  const [showDbModal, setShowDbModal] = useState(false)

  useEffect(() => {
    async function loadEnvStatusAndConfig() {
      try {
        const status = await SystemSettingsAPI.getEnvStatus()
        setEnvStatus(status)

        const liveConfig = await SystemSettingsAPI.getConfig()
        setConfig({
          workspace: liveConfig.workspace || "",
          ue_root: liveConfig.ue_root || "",
          uproject_path: liveConfig.uproject || "",
          blender_exe: liveConfig.blender || "",
          palworld_exe: liveConfig.palworld_exe || "",
          fmodel_output: liveConfig.fmodel_output || "",
        })
        setShowMappedNames(liveConfig.show_mapped !== false)
      } catch (err: any) {
        console.error("Failed to load env status or config:", err)
        setDiagnosticError(String(err.message || err))
      }
    }
    loadEnvStatusAndConfig()
  }, [])

  async function updateConfig(key: keyof typeof mockConfig, value: string) {
    setConfig((c) => ({ ...c, [key]: value }))
    try {
      const backendKey =
        key === "uproject_path" ? "uproject" :
        key === "blender_exe" ? "blender" :
        key;
      await SystemSettingsAPI.setConfig(backendKey, value)
    } catch (err: any) {
      console.error("Failed to update config key:", err)
      setDiagnosticError(String(err.message || err))
    }
  }

  async function handleShowMappedToggle(checked: boolean) {
    setShowMappedNames(checked)
    try {
      await SystemSettingsAPI.setConfig("show_mapped", checked ? "True" : "False")
    } catch (err: any) {
      console.error("Failed to update show_mapped setting:", err)
      setDiagnosticError(String(err.message || err))
    }
  }

  // Sequential Wizard Verification Flow
  async function runVerificationFlow() {
    try {
      showNotification("Starting system and prerequisite verification flow... 🦊", "info", "Prerequisites")
      const result = await SystemSettingsAPI.verifyEnv()
      const reqs = result.data || {}
      setVerificationResult(reqs)

      // 1. Intercept flow and guide them to setup missing database first!
      if (reqs.needs_db_build) {
        setShowDbModal(true)
      } else if (reqs.needs_plugin_sync) {
        setActiveWizard("plugin")
      } else if (reqs.missing_assets && reqs.missing_assets.length > 0) {
        setActiveWizard("asset")
      } else if (reqs.needs_remote_exec_enable || reqs.needs_cooking_setup) {
        setActiveWizard("config")
      } else {
        // Refresh local integration state
        const updated = await SystemSettingsAPI.getEnvStatus()
        setEnvStatus(updated)
        showNotification("All systems fully verified! Your workspace, helper plugins, and configs are 100% ready! 🦊✨", "success", "Verification Clean")
      }
    } catch (err: any) {
      console.error("Verification failed:", err)
      setDiagnosticError(String(err.message || err))
    }
  }

  // Remediations handlers
  async function handleInstallPlugin() {
    try {
      showNotification("Compiling and installing C++ editor helper plugin... ⚙️", "info", "Compiling")
      await SystemSettingsAPI.managePalSchema("install")
      showNotification("C++ plugin installed and compiled successfully! Proceeding with next check...", "success", "Installation Done")
      await runVerificationFlow()
    } catch (err: any) {
      console.error("Plugin installation failed:", err)
      setDiagnosticError(String(err.message || err))
    }
  }

  async function handleInjectAssets() {
    try {
      showNotification("Injecting required material assets and templates into project Content... 📦", "info", "Injecting")
      await SystemSettingsAPI.injectAssets()
      showNotification("Prerequisite material assets injected successfully! Proceeding with next check...", "success", "Assets Loaded")
      await runVerificationFlow()
    } catch (err: any) {
      console.error("Asset injection failed:", err)
      setDiagnosticError(String(err.message || err))
    }
  }

  async function handleFixConfig() {
    try {
      showNotification("Configuring Python Remote Execution settings in DefaultEngine.ini... ⚙️", "info", "Configuring")
      await SystemSettingsAPI.enableRemoteExec()
      showNotification("Project configuration patched successfully! All systems set.", "success", "Config Patched")
      await runVerificationFlow()
    } catch (err: any) {
      console.error("Config fix failed:", err)
      setDiagnosticError(String(err.message || err))
    }
  }

  async function handleAutodetect() {
    try {
      const results = await SystemSettingsAPI.autodetect()
      if (results.ue_root) {
        await updateConfig("ue_root", results.ue_root)
      }
      if (results.palworld_exe) {
        await updateConfig("palworld_exe", results.palworld_exe)
      }
      const liveConfig = await SystemSettingsAPI.getConfig()
      setConfig({
        workspace: liveConfig.workspace || "",
        ue_root: liveConfig.ue_root || "",
        uproject_path: liveConfig.uproject || "",
        blender_exe: liveConfig.blender || "",
        palworld_exe: liveConfig.palworld_exe || "",
        fmodel_output: liveConfig.fmodel_output || "",
      })
      showNotification("Auto-detection finished and matching paths were automatically pre-filled! 🦊", "success", "Auto-Detection")
    } catch (err: any) {
      console.error("Autodetect failed:", err)
      setDiagnosticError(String(err.message || err))
    }
  }

  return (
    <div className="flex flex-col gap-6 max-w-5xl">
      {/* Project Environment Paths */}
      <section className="bg-card rounded-md border border-border p-6">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-3">
            <Folder className="size-4 text-primary" />
            <h2 className="text-foreground font-bold text-sm uppercase tracking-widest">Project Environment Paths</h2>
          </div>
          <button
            onClick={handleAutodetect}
            className="flex items-center gap-1.5 text-xs text-primary hover:text-primary/80 transition-colors border border-primary/20 rounded px-2.5 py-1 hover:bg-primary/5 cursor-pointer font-semibold uppercase tracking-wider"
          >
            Auto-detect Paths
          </button>
        </div>

        <div className="grid grid-cols-2 gap-x-8 gap-y-5">
          <PathField
            label="WORKSPACE ROOT (FMODEL OUTPUT)"
            value={config.fmodel_output}
            onChange={(v) => updateConfig("fmodel_output", v)}
            onPick={async () => {
              const res = await SystemSettingsAPI.pickPath({ directory: true })
              if (res && res.status === "success" && res.path) {
                updateConfig("fmodel_output", res.path)
              }
            }}
            wide
          />
          <PathField
            label="UNREAL ENGINE ROOT"
            value={config.ue_root}
            onChange={(v) => updateConfig("ue_root", v)}
            onPick={async () => {
              const res = await SystemSettingsAPI.pickPath({ directory: true })
              if (res && res.status === "success" && res.path) {
                updateConfig("ue_root", res.path)
              }
            }}
          />
          <PathField
            label=".UPROJECT FILE PATH"
            value={config.uproject_path}
            onChange={(v) => updateConfig("uproject_path", v)}
            iconVariant="file"
            onPick={async () => {
              const res = await SystemSettingsAPI.pickPath({
                directory: false,
                filters: [{ name: "UProject Files", extensions: ["uproject"] }]
              })
              if (res && res.status === "success" && res.path) {
                updateConfig("uproject_path", res.path)
              }
            }}
          />
          <PathField
            label="BLENDER EXECUTABLE"
            value={config.blender_exe}
            onChange={(v) => updateConfig("blender_exe", v)}
            onPick={async () => {
              const res = await SystemSettingsAPI.pickPath({
                directory: false,
                filters: [{ name: "Blender Executable", extensions: ["exe"] }]
              })
              if (res && res.status === "success" && res.path) {
                updateConfig("blender_exe", res.path)
              }
            }}
          />
          <PathField
            label="PALWORLD.EXE PATH"
            value={config.palworld_exe}
            onChange={(v) => updateConfig("palworld_exe", v)}
            onPick={async () => {
              const res = await SystemSettingsAPI.pickPath({
                directory: false,
                filters: [{ name: "Palworld Executable", extensions: ["exe"] }]
              })
              if (res && res.status === "success" && res.path) {
                updateConfig("palworld_exe", res.path)
              }
            }}
            wide
          />
        </div>
      </section>

      <div className="grid grid-cols-[1fr_1.5fr] gap-4">
        {/* Preferences */}
        <section className="bg-card rounded-md border border-border p-5 flex flex-col gap-4">
          <div className="flex items-center gap-2 mb-1">
            <span className="size-4 text-primary">⊙</span>
            <h2 className="text-foreground font-bold text-sm uppercase tracking-widest">Preferences</h2>
          </div>

          <div className="bg-muted/40 rounded-md border border-border p-4 flex items-start justify-between gap-4">
            <div>
              <div className="text-foreground text-sm font-semibold">SHOW MAPPED NAMES</div>
              <div className="text-muted-foreground text-xs mt-1 leading-relaxed">
                Display human-readable asset aliases instead of raw internal IDs
              </div>
            </div>
            <label className="shrink-0 cursor-pointer">
              <div className="relative w-11 h-6">
                <input
                  type="checkbox"
                  checked={showMappedNames}
                  onChange={(e) => handleShowMappedToggle(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-muted border border-border peer-checked:bg-status-success rounded-full transition-colors" />
                <div className="absolute top-0.5 left-0.5 size-5 bg-white rounded-full shadow transition-transform peer-checked:translate-x-5" />
              </div>
            </label>
          </div>
        </section>

        {/* Essential Binaries */}
        <section className="bg-card rounded-md border border-border p-5 flex flex-col gap-3">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-primary text-base">⚙</span>
            <h2 className="text-foreground font-bold text-sm uppercase tracking-widest">Essential Binaries</h2>
          </div>

          {/* UE4SS */}
          <BinaryCard
            name="UE4SS"
            status={
              envStatus.ue4ss?.status === "Installed"
                ? `INSTALLED (${envStatus.ue4ss?.branch || "Unknown"})`
                : envStatus.ue4ss?.status === "Not Installed"
                ? "NOT INSTALLED"
                : "STATUS UNKNOWN"
            }
            statusClass={
              envStatus.ue4ss?.status === "Installed"
                ? "bg-status-success/15 text-status-success border-status-success/30"
                : "bg-status-warning/15 text-status-warning border-status-warning/30"
            }
            description="The essential C++ modding tool for Unreal Engine games. Required for script loading and hooking."
            accentColor={
              envStatus.ue4ss?.status === "Installed"
                ? "border-l-status-success"
                : "border-l-status-warning"
            }
            actions={
              envStatus.ue4ss?.status === "Installed"
                ? envStatus.ue4ss?.branch === "Palworld-Experimental"
                  ? [
                      { label: "Uninstall", actionKey: "uninstall", variant: "ghost" },
                      { label: "Repair", actionKey: "repair", variant: "ghost" },
                      { label: "Switch to Latest-Experimental", actionKey: "install-latest", variant: "warning" },
                    ]
                  : [
                      { label: "Uninstall", actionKey: "uninstall", variant: "ghost" },
                      { label: "Repair", actionKey: "repair", variant: "ghost" },
                      { label: "Switch to Palworld-Experimental", actionKey: "install-palworld", variant: "warning" },
                    ]
                : [
                    { label: "Install Palworld-Experimental", actionKey: "install-palworld", variant: "primary" },
                    { label: "Install Latest-Experimental", actionKey: "install-latest", variant: "primary" },
                  ]
            }
            onAction={async (actionKey) => {
              try {
                await SystemSettingsAPI.manageUe4ss(actionKey)
                const updated = await SystemSettingsAPI.getEnvStatus()
                setEnvStatus(updated)
              } catch (err: any) {
                console.error("UE4SS action failed:", err)
                setDiagnosticError(String(err.message || err))
              }
            }}
            repoBranch={envStatus.ue4ss?.branch}
          />

          {/* PalSchema Plugin */}
          <BinaryCard
            name="PalSchema Plugin"
            status={
              envStatus.palschema?.status === "Installed"
                ? "INSTALLED & ACTIVE"
                : envStatus.palschema?.status === "Not Installed"
                ? "NOT INSTALLED"
                : "STATUS UNKNOWN"
            }
            statusClass={
              envStatus.palschema?.status === "Installed"
                ? "bg-status-success/15 text-status-success border-status-success/30"
                : "bg-status-warning/15 text-status-warning border-status-warning/30"
            }
            description="Data structure mapping for the latest Palworld version (v0.2.1.0). Controls asset serialization."
            accentColor={
              envStatus.palschema?.status === "Installed"
                ? "border-l-status-success"
                : "border-l-status-warning"
            }
            actions={
              envStatus.palschema?.status === "Installed"
                ? [
                    { label: "Uninstall", actionKey: "uninstall", variant: "ghost" },
                    { label: "Repair", actionKey: "install", variant: "ghost" },
                  ]
                : [
                    { label: "INSTALL", actionKey: "install", variant: "primary" },
                  ]
            }
            onAction={async (actionKey) => {
              try {
                await SystemSettingsAPI.managePalSchema(actionKey)
                const updated = await SystemSettingsAPI.getEnvStatus()
                setEnvStatus(updated)
              } catch (err: any) {
                console.error("PalSchema action failed:", err)
                setDiagnosticError(String(err.message || err))
              }
            }}
            repoBranch="PalSchema"
          />
        </section>
      </div>

      {/* Pipeline Health Monitor */}
      <section className="bg-card rounded-md border border-border p-5">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-foreground font-bold text-sm uppercase tracking-widest">Pipeline Health Monitor</h2>
            <p className="text-muted-foreground text-xs mt-1">Current connection states and diagnostic tools</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setShowDbModal(true)}
              className="flex items-center gap-1.5 text-xs text-primary hover:text-primary-foreground hover:bg-primary font-semibold border border-primary/20 rounded px-3 py-1.5 transition-all cursor-pointer"
            >
              <Database className="size-3.5" />
              Rebuild Game Database
            </button>
            <button
              onClick={runVerificationFlow}
              className="flex items-center gap-1.5 text-xs text-primary hover:text-primary-foreground hover:bg-primary font-semibold border border-primary/20 rounded px-3 py-1.5 transition-all cursor-pointer"
            >
              <CheckCircle className="size-3.5" />
              Verify Environment Prerequisites
            </button>
          </div>
        </div>

        <div className="grid grid-cols-4 gap-3">
          {PIPELINE_ITEMS.map(({ key, label }) => {
            const status = (envStatus.pipeline && envStatus.pipeline[key as PipelineKey]) || "IDLE"
            return (
              <div key={key} className="bg-muted/40 rounded border border-border p-4">
                <div className="text-muted-foreground text-xs font-semibold uppercase tracking-wider mb-2">{label}</div>
                <div className={cn("text-sm font-bold flex items-center gap-1.5", PIPELINE_COLORS[status] ?? "text-muted-foreground")}>
                  <span className={cn("size-1.5 rounded-full inline-block", {
                    "bg-status-success": status === "CONNECTED" || status === "RUNNING",
                    "bg-status-warning": status === "STANDBY",
                    "bg-muted-foreground": status === "IDLE",
                  })} />
                  {status}
                </div>
              </div>
            )
          })}
        </div>
      </section>

      {/* Diagnostics Modal Render */}
      {diagnosticError && (
        <DiagnosticsModal
          errorText={diagnosticError}
          onClose={() => setDiagnosticError(null)}
        />
      )}

      {/* Setup Wizards Sequential Modals */}
      <PluginInstallModal
        isOpen={activeWizard === "plugin"}
        onClose={() => setActiveWizard(null)}
        onConfirm={handleInstallPlugin}
      />

      <AssetInjectModal
        isOpen={activeWizard === "asset"}
        onClose={() => setActiveWizard(null)}
        onConfirm={handleInjectAssets}
      />

      <ConfigFixModal
        isOpen={activeWizard === "config"}
        onClose={() => setActiveWizard(null)}
        onConfirm={handleFixConfig}
      />

      {showDbModal && (
        <DatabaseMissingModal
          onClose={() => setShowDbModal(false)}
          onSuccess={() => {
            showNotification("Game database rebuilt successfully! 🦊✨", "success", "Database Rebuilt")
          }}
        />
      )}

      <NotificationToast notifications={notifications} onDismiss={dismissNotification} />
    </div>
  )
}

/* ── Sub-components ── */

function PathField({
  label,
  value,
  onChange,
  iconVariant = "folder",
  wide = false,
  onPick,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  iconVariant?: "folder" | "file"
  wide?: boolean
  onPick?: () => void
}) {
  return (
    <div className={cn("flex flex-col gap-1.5", wide && "col-span-2")}>
      <label className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">{label}</label>
      <div className="flex items-center gap-0">
        <input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="flex-1 bg-muted/50 border border-border border-r-0 rounded-l px-3 py-2 text-sm text-foreground font-mono placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
        />
        <button
          onClick={onPick}
          className="px-3 py-2 bg-muted border border-border rounded-r hover:bg-accent transition-colors"
        >
          <Folder className="size-4 text-muted-foreground" />
        </button>
      </div>
    </div>
  )
}

function BinaryCard({
  name,
  status: initialStatus,
  statusClass: initialStatusClass,
  description,
  accentColor: initialAccentColor,
  actions: initialActions,
  onAction,
  repoBranch,
}: {
  name: string
  status: string
  statusClass: string
  description: string
  accentColor: string
  actions: { label: string; actionKey: string; variant: "ghost" | "primary" | "warning"; disabled?: boolean }[]
  onAction?: (actionKey: string) => void
  repoBranch?: string
}) {
  const [latestVersion, setLatestVersion] = useState<string | null>(null)
  const [isLoadingRelease, setIsLoadingRelease] = useState(false)

  // Dynamically resolve creator, sourceUrl, and repoPath based on branch
  let creator = "UE4SS Team"
  let sourceUrl = "https://github.com/UE4SS-RE/RE-UE4SS"
  let repoPath = "UE4SS-RE/RE-UE4SS"

  if (name === "PalSchema Plugin") {
    creator = "Okaetsu / Palworld Modding Community"
    sourceUrl = "https://github.com/Okaetsu/RE-UE4SS"
    repoPath = "Okaetsu/PalSchema"
  } else if (name === "UE4SS") {
    if (repoBranch === "Palworld-Experimental") {
      creator = "Okaetsu"
      sourceUrl = "https://github.com/Okaetsu/RE-UE4SS"
      repoPath = "Okaetsu/RE-UE4SS"
    } else {
      creator = "UE4SS Team"
      sourceUrl = "https://github.com/UE4SS-RE/RE-UE4SS"
      repoPath = "UE4SS-RE/RE-UE4SS"
    }
  }

  // Determine current/latest release mismatch variants
  let currentVersion = "3.0.1"
  if (name === "PalSchema Plugin") {
    currentVersion = "0.5.2"
  } else if (name === "UE4SS") {
    if (repoBranch === "Palworld-Experimental") {
      currentVersion = "experimental-palworld"
    } else {
      currentVersion = "3.0.1"
    }
  }

  const isOutdated = latestVersion && currentVersion !== latestVersion

  const status = isOutdated ? "UPDATE AVAILABLE" : initialStatus
  const statusClass = isOutdated 
    ? "bg-status-warning/15 text-status-warning border-status-warning/30" 
    : initialStatusClass
  const accentColor = isOutdated ? "border-l-status-warning" : initialAccentColor

  // Filter actions dynamically depending on installed state
  const actions = initialActions.map((a) => {
    const isInstalled = initialStatus.startsWith("INSTALLED") || initialStatus.includes("ACTIVE");
    if (isOutdated && isInstalled && (a.actionKey === "repair" || a.actionKey === "install")) {
      return { ...a, label: "UPDATE", variant: "primary" as const }
    }
    return a
  })

  useEffect(() => {
    if (!repoPath) return
    async function fetchLatestRelease() {
      setIsLoadingRelease(true)
      try {
        const res = await fetch(`https://api.github.com/repos/${repoPath}/releases/latest`)
        if (res.ok) {
          const data = await res.json()
          if (data && data.tag_name) {
            const tag = data.tag_name.replace(/^v/, "")
            setLatestVersion(tag)
          }
        }
      } catch (err) {
        console.error("Failed to check latest release from GitHub:", err)
      } finally {
        setIsLoadingRelease(false)
      }
    }
    fetchLatestRelease()
  }, [repoPath])

  const actionClasses = {
    ghost: "border border-border bg-transparent text-foreground hover:bg-accent",
    primary: "bg-primary text-primary-foreground hover:bg-primary/80",
    warning: "bg-status-warning text-white hover:bg-status-warning/80",
  }

  return (
    <div className={cn("flex items-center gap-4 bg-muted/30 rounded border-l-2 border border-border px-4 py-3", accentColor)}>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-foreground text-sm font-semibold">{name}</span>
          <Badge
            variant="outline"
            className={cn("text-xs font-bold border px-2 py-0", statusClass)}
          >
            {status}
          </Badge>
          {latestVersion && (
            <Badge
              variant="secondary"
              className="text-[10px] font-semibold border px-1.5 py-0 bg-primary/10 text-primary border-primary/20"
            >
              {isLoadingRelease ? "v..." : `Latest: v${latestVersion}`}
            </Badge>
          )}
        </div>
        <p className="text-muted-foreground text-xs leading-relaxed">{description}</p>
        
        {/* Creator, Source & Releases Info */}
        {(creator || sourceUrl) && (
          <div className="flex items-center gap-2 mt-1.5 text-[11px] text-muted-foreground">
            {creator && (
              <span>
                Creator: <span className="text-foreground/80 font-medium">{creator}</span>
              </span>
            )}
            {creator && sourceUrl && <span className="opacity-50">•</span>}
            {sourceUrl && (
              <a
                href={sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline font-medium"
              >
                Source / Credits
              </a>
            )}
          </div>
        )}
      </div>
      <div className="flex items-center gap-2 shrink-0 flex-wrap max-w-[280px] justify-end">
        {actions.map((a) => (
          <button
            key={a.actionKey}
            onClick={() => !a.disabled && onAction?.(a.actionKey)}
            disabled={a.disabled}
            className={cn(
              "px-3 py-1.5 rounded text-xs font-semibold transition-colors whitespace-nowrap",
              a.disabled ? "opacity-50 cursor-not-allowed bg-muted text-muted-foreground border border-border" : actionClasses[a.variant]
            )}
          >
            {a.label}
          </button>
        ))}
      </div>
    </div>
  )
}
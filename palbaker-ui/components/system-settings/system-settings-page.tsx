"use client"

import { useState, useEffect } from "react"
import { mockConfig, mockEnvStatus } from "@/lib/mock-data"
import { SystemSettingsAPI } from "@/lib/data-service"
import { DiagnosticsModal } from "@/components/common/diagnostics-modal"
import { useNotifications } from "../mod-manager/mod-card-expanded/use-notifications"
import { NotificationToast } from "../mod-manager/mod-card-expanded/notification-toast"
import { DatabaseMissingModal } from "@/components/common/database-missing-modal"
import { useNav } from "@/lib/nav-context"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"

// Sections
import { EnvironmentPaths } from "./environment-paths"
import { Preferences } from "./preferences"
import { EssentialBinaries } from "./essential-binaries"
import { PipelineHealth } from "./pipeline-health"
import { ThemeEditor } from "./theme-editor"

// Wizards
import { PluginInstallModal } from "./setup-wizards/PluginInstallModal"
import { AssetInjectModal } from "./setup-wizards/AssetInjectModal"
import { ConfigFixModal } from "./setup-wizards/ConfigFixModal"
import { IconExtractModal } from "./setup-wizards/IconExtractModal"

export function SystemSettingsPage() {
  const [config, setConfig] = useState<any>(mockConfig)
  const [envStatus, setEnvStatus] = useState<any>(mockEnvStatus)
  const [showMappedNames, setShowMappedNames] = useState(true)
  const [diagnosticError, setDiagnosticError] = useState<string | null>(null)
  
  // Safe local states replacing the NavContext fetch
  const [skippedWizards, setSkippedWizards] = useState<string[]>([])
  
  const { notifications, showNotification, dismissNotification } = useNotifications()
  const { invalidateCache } = useNav() as any

  const [activeWizard, setActiveWizard] = useState<"plugin" | "asset" | "config" | "icon" | null>(null)
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
        setDiagnosticError(String(err.message || err))
      }
    }
    loadEnvStatusAndConfig()
  }, [])

  async function updateConfig(key: string, value: string) {
    setConfig((c: any) => ({ ...c, [key]: value }))
    try {
      const backendKey = key === "uproject_path" ? "uproject" : key === "blender_exe" ? "blender" : key;
      await SystemSettingsAPI.setConfig(backendKey, value)
      invalidateCache()
    } catch (err: any) {
      setDiagnosticError(String(err.message || err))
    }
  }

  async function handleShowMappedToggle(checked: boolean) {
    setShowMappedNames(checked)
    try {
      await SystemSettingsAPI.setConfig("show_mapped", checked ? "True" : "False")
      invalidateCache()
    } catch (err: any) {
      setDiagnosticError(String(err.message || err))
    }
  }

  async function handleAutodetect() {
    try {
      const results = await SystemSettingsAPI.autodetect()
      if (results.ue_root) await updateConfig("ue_root", results.ue_root)
      if (results.palworld_exe) await updateConfig("palworld_exe", results.palworld_exe)
      if (results.blender_versions && results.blender_versions.length > 0) await updateConfig("blender_exe", results.blender_versions[0])
      
      const liveConfig = await SystemSettingsAPI.getConfig()
      setConfig({
        workspace: liveConfig.workspace || "",
        ue_root: liveConfig.ue_root || "",
        uproject_path: liveConfig.uproject || "",
        blender_exe: liveConfig.blender || "",
        palworld_exe: liveConfig.palworld_exe || "",
        fmodel_output: liveConfig.fmodel_output || "",
      })
      showNotification("Auto-detection finished! 🦊", "success")
      invalidateCache()
    } catch (err: any) {
      setDiagnosticError(String(err.message || err))
    }
  }

  async function runVerificationFlow(ignoredWizards: string[] = skippedWizards) {
    try {
      showNotification("Starting system verification flow... 🦊", "info")
      const result = await SystemSettingsAPI.verifyEnv()
      const reqs = result.data || {}
      setVerificationResult(reqs)

      if (reqs.needs_db_build && !ignoredWizards.includes("db")) {
        setShowDbModal(true); setActiveWizard(null)
      } else if (reqs.needs_plugin_sync && !ignoredWizards.includes("plugin")) {
        setActiveWizard("plugin"); setShowDbModal(false)
      } else if (reqs.missing_assets && reqs.missing_assets.length > 0 && !ignoredWizards.includes("asset")) {
        setActiveWizard("asset"); setShowDbModal(false)
      } else if (reqs.needs_icon_extraction && !ignoredWizards.includes("icon")) {
        setActiveWizard("icon"); setShowDbModal(false)
      } else if ((reqs.needs_remote_exec_enable || reqs.needs_cooking_setup) && !ignoredWizards.includes("config")) {
        setActiveWizard("config"); setShowDbModal(false)
      } else {
        setShowDbModal(false); setActiveWizard(null); setSkippedWizards([])
        const updated = await SystemSettingsAPI.getEnvStatus()
        setEnvStatus(updated)
        showNotification("All systems fully verified! 🦊✨", "success")
      }
    } catch (err: any) {
      setDiagnosticError(String(err.message || err))
    }
  }

  const skip = (key: string) => {
    const nextSkipped = [...skippedWizards, key]
    setSkippedWizards(nextSkipped)
    if (key === "db") setShowDbModal(false)
    else setActiveWizard(null)
    runVerificationFlow(nextSkipped)
  }

  const executeWizardAction = async (apiCall: () => Promise<any>, successMsg: string) => {
    try {
      await apiCall()
      showNotification(successMsg, "success")
      await runVerificationFlow()
    } catch (err: any) {
      setDiagnosticError(String(err.message || err))
    }
  }

  return (
    <div className="flex flex-col gap-6 max-w-5xl">
      <Tabs defaultValue="general">
        <TabsList variant="line" className="mb-4">
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="plugins">Plugins</TabsTrigger>
          <TabsTrigger value="themes">Themes</TabsTrigger>
        </TabsList>

        <TabsContent value="general" className="flex flex-col gap-6">
          <EnvironmentPaths config={config} updateConfig={updateConfig} onAutodetect={handleAutodetect} />
          <Preferences 
            showMappedNames={showMappedNames} 
            onToggleMapped={handleShowMappedToggle} 
          />
        </TabsContent>

        <TabsContent value="plugins" className="flex flex-col gap-6">
          <EssentialBinaries 
            envStatus={envStatus} 
            onActionUe4ss={async (action: string) => {
              try { await SystemSettingsAPI.manageUe4ss(action); setEnvStatus(await SystemSettingsAPI.getEnvStatus()) }
              catch (err: any) { setDiagnosticError(String(err.message || err)) }
            }} 
            onActionPalschema={async (action: string) => {
              try { await SystemSettingsAPI.managePalSchema(action); setEnvStatus(await SystemSettingsAPI.getEnvStatus()) }
              catch (err: any) { setDiagnosticError(String(err.message || err)) }
            }} 
          />
          <PipelineHealth 
            envStatus={envStatus} 
            onRebuildDb={() => setShowDbModal(true)} 
            onVerify={() => { setSkippedWizards([]); runVerificationFlow([]) }} 
          />
        </TabsContent>

        <TabsContent value="themes">
          <ThemeEditor />
        </TabsContent>
      </Tabs>

      {diagnosticError && <DiagnosticsModal errorText={diagnosticError} onClose={() => setDiagnosticError(null)} />}
      <PluginInstallModal 
        isOpen={activeWizard === "plugin"} 
        isOutdated={verificationResult?.plugin_outdated} 
        needsCompile={verificationResult?.needs_compile} 
        onClose={() => skip("plugin")} 
        onConfirm={() => executeWizardAction(() => SystemSettingsAPI.manageCppPlugin("install"), "C++ plugin installed!")} 
      />
      <AssetInjectModal isOpen={activeWizard === "asset"} onClose={() => skip("asset")} onConfirm={() => executeWizardAction(() => SystemSettingsAPI.injectAssets(), "Assets injected!")} />
      <ConfigFixModal isOpen={activeWizard === "config"} needsRemoteExec={verificationResult?.needs_remote_exec_enable} needsCooking={verificationResult?.needs_cooking_setup} onClose={() => skip("config")} onConfirm={() => executeWizardAction(() => SystemSettingsAPI.enableRemoteExec(), "Config patched!")} />
      <IconExtractModal isOpen={activeWizard === "icon"} onClose={() => skip("icon")} onConfirm={() => executeWizardAction(() => SystemSettingsAPI.extractIcons(), "Icons extracted!")} />
      {showDbModal && <DatabaseMissingModal missingFiles={verificationResult?.missing_db_files} onClose={() => skip("db")} onSuccess={() => { showNotification("Database rebuilt!", "success"); runVerificationFlow(skippedWizards) }} />}
      <NotificationToast notifications={notifications} onDismiss={dismissNotification} />
    </div>
  )
}
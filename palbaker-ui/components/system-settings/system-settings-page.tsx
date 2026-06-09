"use client"

import { useState, useEffect } from "react"
import { mockConfig, mockEnvStatus } from "@/lib/mock-data"
import { SystemSettingsAPI } from "@/lib/data-service"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { Folder, RefreshCw } from "lucide-react"
import { cn } from "@/lib/utils"

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
      } catch (err) {
        console.error("Failed to load env status or config:", err)
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
    } catch (err) {
      console.error("Failed to update config key:", err)
    }
  }

  async function handleShowMappedToggle(checked: boolean) {
    setShowMappedNames(checked)
    try {
      await SystemSettingsAPI.setConfig("show_mapped", checked ? "True" : "False")
    } catch (err) {
      console.error("Failed to update show_mapped setting:", err)
    }
  }

  return (
    <div className="flex flex-col gap-6 max-w-5xl">
      {/* Project Environment Paths */}
      <section className="bg-card rounded-md border border-border p-6">
        <div className="flex items-center gap-3 mb-5">
          <Folder className="size-4 text-primary" />
          <h2 className="text-foreground font-bold text-sm uppercase tracking-widest">Project Environment Paths</h2>
        </div>

        <div className="grid grid-cols-2 gap-x-8 gap-y-5">
          <PathField
            label="WORKSPACE ROOT (FMODEL OUTPUT)"
            value={config.fmodel_output}
            onChange={(v) => updateConfig("fmodel_output", v)}
          />
          <PathField
            label="STANDALONE EXPORT DIR"
            value={config.workspace}
            onChange={(v) => updateConfig("workspace", v)}
          />
          <PathField
            label="UNREAL ENGINE ROOT"
            value={config.ue_root}
            onChange={(v) => updateConfig("ue_root", v)}
          />
          <PathField
            label=".UPROJECT FILE PATH"
            value={config.uproject_path}
            onChange={(v) => updateConfig("uproject_path", v)}
            iconVariant="file"
          />
          <PathField
            label="BLENDER EXECUTABLE"
            value={config.blender_exe}
            onChange={(v) => updateConfig("blender_exe", v)}
          />
          <PathField
            label="PALWORLD.EXE PATH"
            value={config.palworld_exe}
            onChange={(v) => updateConfig("palworld_exe", v)}
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
            {/* Toggle */}
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
            name="UE4SS (v2.5.2)"
            status="INSTALLED & ACTIVE"
            statusClass="bg-status-success/15 text-status-success border-status-success/30"
            description="The essential C++ modding tool for Unreal Engine games. Required for script loading and hooking."
            accentColor="border-l-status-success"
            actions={[
              { label: "Uninstall", variant: "ghost" },
              { label: "Repair", variant: "ghost" },
              { label: "INSTALL", variant: "primary" },
            ]}
          />

          {/* PalSchema Plugin */}
          <BinaryCard
            name="PalSchema Plugin"
            status="UPDATE AVAILABLE"
            statusClass="bg-status-warning/15 text-status-warning border-status-warning/30"
            description="Data structure mapping for the latest Palworld version (v0.2.1.0). Controls asset serialization."
            accentColor="border-l-status-warning"
            actions={[
              { label: "Uninstall", variant: "ghost" },
              { label: "INSTALL / UPDATE", variant: "warning" },
            ]}
          />
        </section>
      </div>

      {/* Pipeline Health Monitor */}
      <section className="bg-card rounded-md border border-border p-5">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-foreground font-bold text-sm uppercase tracking-widest">Pipeline Health Monitor</h2>
            <p className="text-muted-foreground text-xs mt-1">Current connection states for all background workers</p>
          </div>
          <button className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors">
            <RefreshCw className="size-3.5" />
            Force Re-scan
          </button>
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
}: {
  label: string
  value: string
  onChange: (v: string) => void
  iconVariant?: "folder" | "file"
  wide?: boolean
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
        <button className="px-3 py-2 bg-muted border border-border rounded-r hover:bg-accent transition-colors">
          <Folder className="size-4 text-muted-foreground" />
        </button>
      </div>
    </div>
  )
}

function BinaryCard({
  name,
  status,
  statusClass,
  description,
  accentColor,
  actions,
}: {
  name: string
  status: string
  statusClass: string
  description: string
  accentColor: string
  actions: { label: string; variant: "ghost" | "primary" | "warning" }[]
}) {
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
        </div>
        <p className="text-muted-foreground text-xs leading-relaxed">{description}</p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {actions.map((a) => (
          <button
            key={a.label}
            className={cn("px-3 py-1.5 rounded text-xs font-semibold transition-colors whitespace-nowrap", actionClasses[a.variant])}
          >
            {a.label}
          </button>
        ))}
      </div>
    </div>
  )
}

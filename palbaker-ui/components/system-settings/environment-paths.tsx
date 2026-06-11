"use client"

import { Folder } from "lucide-react"
import { PathField } from "./path-field"
import { SystemSettingsAPI } from "@/lib/data-service"

interface Props {
  config: any
  updateConfig: (key: string, value: string) => void
  onAutodetect: () => void
}

export function EnvironmentPaths({ config, updateConfig, onAutodetect }: Props) {
  return (
    <section className="bg-card rounded-md border border-border p-6">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <Folder className="size-4 text-primary" />
          <h2 className="text-foreground font-bold text-sm uppercase tracking-widest">Project Environment Paths</h2>
        </div>
        <button
          onClick={onAutodetect}
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
            if (res && res.status === "success" && res.path) updateConfig("fmodel_output", res.path)
          }}
          wide
        />
        <PathField
          label="UNREAL ENGINE ROOT"
          value={config.ue_root}
          onChange={(v) => updateConfig("ue_root", v)}
          onPick={async () => {
            const res = await SystemSettingsAPI.pickPath({ directory: true })
            if (res && res.status === "success" && res.path) updateConfig("ue_root", res.path)
          }}
        />
        <PathField
          label=".UPROJECT FILE PATH"
          value={config.uproject_path}
          onChange={(v) => updateConfig("uproject_path", v)}
          iconVariant="file"
          onPick={async () => {
            const res = await SystemSettingsAPI.pickPath({ directory: false, filters: [{ name: "UProject Files", extensions: ["uproject"] }] })
            if (res && res.status === "success" && res.path) updateConfig("uproject_path", res.path)
          }}
        />
        <PathField
          label="BLENDER EXECUTABLE"
          value={config.blender_exe}
          onChange={(v) => updateConfig("blender_exe", v)}
          onPick={async () => {
            const res = await SystemSettingsAPI.pickPath({ directory: false, filters: [{ name: "Blender Executable", extensions: ["exe"] }] })
            if (res && res.status === "success" && res.path) updateConfig("blender_exe", res.path)
          }}
        />
        <PathField
          label="PALWORLD.EXE PATH"
          value={config.palworld_exe}
          onChange={(v) => updateConfig("palworld_exe", v)}
          onPick={async () => {
            const res = await SystemSettingsAPI.pickPath({ directory: false, filters: [{ name: "Palworld Executable", extensions: ["exe"] }] })
            if (res && res.status === "success" && res.path) updateConfig("palworld_exe", res.path)
          }}
          wide
        />
      </div>
    </section>
  )
}
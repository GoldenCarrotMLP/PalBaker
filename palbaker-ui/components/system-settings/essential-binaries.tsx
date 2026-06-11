"use client"

import { BinaryCard } from "./binary-card"

interface Props {
  envStatus: any
  onActionUe4ss: (action: string) => void
  onActionPalschema: (action: string) => void
}

export function EssentialBinaries({ envStatus, onActionUe4ss, onActionPalschema }: Props) {
  return (
    <section className="bg-card rounded-md border border-border p-5 flex flex-col gap-3">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-primary text-base">⚙</span>
        <h2 className="text-foreground font-bold text-sm uppercase tracking-widest">Essential Binaries</h2>
      </div>

      <BinaryCard
        name="UE4SS"
        status={envStatus.ue4ss?.status === "Installed" ? `INSTALLED (${envStatus.ue4ss?.branch || "Unknown"})` : envStatus.ue4ss?.status === "Not Installed" ? "NOT INSTALLED" : "STATUS UNKNOWN"}
        statusClass={envStatus.ue4ss?.status === "Installed" ? "bg-status-success/15 text-status-success border-status-success/30" : "bg-status-warning/15 text-status-warning border-status-warning/30"}
        description="The essential C++ modding tool for Unreal Engine games. Required for script loading and hooking."
        accentColor={envStatus.ue4ss?.status === "Installed" ? "border-l-status-success" : "border-l-status-warning"}
        actions={
          envStatus.ue4ss?.status === "Installed"
            ? envStatus.ue4ss?.branch === "Palworld-Experimental"
              ? [{ label: "Uninstall", actionKey: "uninstall", variant: "ghost" }, { label: "Repair", actionKey: "repair", variant: "ghost" }, { label: "Switch to Latest-Experimental", actionKey: "install-latest", variant: "warning" }]
              : [{ label: "Uninstall", actionKey: "uninstall", variant: "ghost" }, { label: "Repair", actionKey: "repair", variant: "ghost" }, { label: "Switch to Palworld-Experimental", actionKey: "install-palworld", variant: "warning" }]
            : [{ label: "Install Palworld-Experimental", actionKey: "install-palworld", variant: "primary" }, { label: "Install Latest-Experimental", actionKey: "install-latest", variant: "primary" }]
        }
        onAction={onActionUe4ss}
        repoBranch={envStatus.ue4ss?.branch}
      />

      <BinaryCard
        name="PalSchema Plugin"
        status={envStatus.palschema?.status === "Installed" ? "INSTALLED & ACTIVE" : envStatus.palschema?.status === "Not Installed" ? "NOT INSTALLED" : "STATUS UNKNOWN"}
        statusClass={envStatus.palschema?.status === "Installed" ? "bg-status-success/15 text-status-success border-status-success/30" : "bg-status-warning/15 text-status-warning border-status-warning/30"}
        description="Data structure mapping for the latest Palworld version (v0.2.1.0). Controls asset serialization."
        accentColor={envStatus.palschema?.status === "Installed" ? "border-l-status-success" : "border-l-status-warning"}
        actions={
          envStatus.palschema?.status === "Installed"
            ? [{ label: "Uninstall", actionKey: "uninstall", variant: "ghost" }, { label: "Repair", actionKey: "install", variant: "ghost" }]
            : [{ label: "INSTALL", actionKey: "install", variant: "primary" }]
        }
        onAction={onActionPalschema}
        repoBranch="PalSchema"
      />
    </section>
  )
}
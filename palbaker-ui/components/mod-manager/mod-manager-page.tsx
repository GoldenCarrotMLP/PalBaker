"use client"

import { useState } from "react"
import { mockModList, type ModItem } from "@/lib/mock-data"
import { ModCard } from "@/components/mod-manager/mod-card"

export function ModManagerPage() {
  const [mods] = useState<ModItem[]>(mockModList)
  const [expandedId, setExpandedId] = useState<string | null>("anubis_model_v4")

  function toggleExpand(id: string) {
    setExpandedId((prev) => (prev === id ? null : id))
  }

  // When the real CLI bridge is connected this will dispatch to the Python server.
  // For now it logs the intended action so interactive testing is possible.
  function handleAction(mod: ModItem, action: string) {
    console.log("[v0] mod action:", mod.name, action)
  }

  return (
    <div className="flex flex-col gap-3">
      {mods.map((mod) => (
        <ModCard
          key={mod.id}
          mod={mod}
          expanded={expandedId === mod.id}
          onToggle={() => toggleExpand(mod.id)}
          onAction={handleAction}
        />
      ))}
    </div>
  )
}

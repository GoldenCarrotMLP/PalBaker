"use client"

import { useState } from "react"
import { mockModList, type ModItem } from "@/lib/mock-data"
import { ModCard } from "@/components/mod-manager/mod-card"

export function ModManagerPage() {
  const [mods, setMods] = useState<ModItem[]>(mockModList)
  const [expandedId, setExpandedId] = useState<string | null>("anubis_model_v4")

  function toggleExpand(id: string) {
    setExpandedId((prev) => (prev === id ? null : id))
  }

  return (
    <div className="flex flex-col gap-3">
      {mods.map((mod) => (
        <ModCard
          key={mod.id}
          mod={mod}
          expanded={expandedId === mod.id}
          onToggle={() => toggleExpand(mod.id)}
        />
      ))}
    </div>
  )
}

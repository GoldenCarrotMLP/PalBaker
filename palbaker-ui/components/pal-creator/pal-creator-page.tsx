"use client"

import { useState, useEffect } from "react"
import { Plus } from "lucide-react"
import { PalCreatorAPI } from "@/lib/data-service"
import { type CreatorPal, type ActiveSkill } from "@/lib/mock-data"
import { PalListRow } from "./pal-list-row"
import { SearchSelectorDialog } from "./search-selector-dialog"

// Default shape for a freshly created Pal before any edits
function makeNewPal(): CreatorPal {
  return {
    CharacterID: `NewPal_${Date.now()}`,
    TemplateID: "Anubis",
    Name: "",
    Description: "",
    ElementType1: "EPalElementType::Normal",
    ElementType2: "EPalElementType::None",
    BaseHP: 100,
    BaseAtk: 50,
    BaseDef: 50,
    BaseWorkSpeed: 100,
    WorkSuitabilities: {
      WorkSuitability_EmitFlame: 0,
      WorkSuitability_Watering: 0,
      WorkSuitability_Seeding: 0,
      WorkSuitability_GenerateElectricity: 0,
      WorkSuitability_Handcraft: 0,
      WorkSuitability_Collection: 0,
      WorkSuitability_Deforest: 0,
      WorkSuitability_Mining: 0,
      WorkSuitability_OilExtraction: 0,
      WorkSuitability_ProductMedicine: 0,
      WorkSuitability_Cool: 0,
      WorkSuitability_Transport: 0,
      WorkSuitability_MonsterFarm: 0,
    },
    Learnset: [],
    SpawnLocationID: "",
    SpawnMinLevel: 1,
    SpawnMaxLevel: 50,
    SpawnMinGroup: 1,
    SpawnMaxGroup: 1,
    ZukanIndex: 1,
    ZukanIndexSuffix: "",
  }
}

type DialogState = {
  title: string
  dataset: Record<string, ActiveSkill | string>
  onSelect: (id: string, label: string) => void
  palElements?: string[]
} | null

export function PalCreatorPage() {
  const [pals,       setPals]       = useState<CreatorPal[]>([])
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [loading,    setLoading]    = useState(true)
  const [dialog,     setDialog]     = useState<DialogState>(null)

  useEffect(() => {
    async function loadPals() {
      try {
        setLoading(true)
        const data = await PalCreatorAPI.list()
        setPals(data as unknown as CreatorPal[])
      } catch (err) {
        console.error("Failed to load custom Pals:", err)
      } finally {
        setLoading(false)
      }
    }
    loadPals()
  }, [])

  function updatePal(id: string, patch: Partial<CreatorPal>) {
    setPals((list) => list.map((p) => (p.CharacterID === id ? { ...p, ...patch } : p)))
  }

  function savePal(oldId: string, saved: CreatorPal) {
    setPals((list) => list.map((p) => (p.CharacterID === oldId ? saved : p)))
  }

  function deletePal(id: string) {
    setPals((list) => list.filter((p) => p.CharacterID !== id))
  }

  function addPal() {
    const pal = makeNewPal()
    setPals((list) => [...list, pal])
    setExpandedId(pal.CharacterID)
  }

  if (loading) {
    return <p className="text-muted-foreground text-xs italic">Loading Pal definitions...</p>
  }

  return (
    <>
      {dialog && (
        <SearchSelectorDialog
          title={dialog.title}
          dataset={dialog.dataset}
          palElements={dialog.palElements}
          onSelect={dialog.onSelect}
          onClose={() => setDialog(null)}
        />
      )}

      <div className="flex flex-col gap-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h2 className="text-muted-foreground text-xs font-bold uppercase tracking-widest">Pal Definitions</h2>
          <button
            onClick={addPal}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-primary text-primary text-xs font-semibold hover:bg-primary/10 transition-colors cursor-pointer"
          >
            <Plus className="size-3.5" />
            New Pal
          </button>
        </div>

        {/* Pal list */}
        {pals.length === 0 ? (
          <p className="text-muted-foreground text-xs italic border border-border rounded p-4">
            No custom Pals yet. Click &quot;New Pal&quot; to create one.
          </p>
        ) : (
          <div className="flex flex-col gap-0 border border-border rounded-md divide-y divide-border overflow-hidden">
            {pals.map((pal) => (
              <PalListRow
                key={pal.CharacterID}
                pal={pal}
                expanded={expandedId === pal.CharacterID}
                onToggle={() => setExpandedId(expandedId === pal.CharacterID ? null : pal.CharacterID)}
                onUpdate={(patch) => updatePal(pal.CharacterID, patch)}
                onOpenDialog={(title, dataset, onSelect, palElements) =>
                  setDialog({ title, dataset, onSelect, palElements })
                }
                onSave={savePal}
                onDelete={deletePal}
              />
            ))}
          </div>
        )}
      </div>
    </>
  )
}

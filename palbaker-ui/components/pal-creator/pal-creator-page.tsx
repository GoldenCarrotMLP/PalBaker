"use client"

import { useState, useEffect } from "react"
import { Plus } from "lucide-react"
import { PalCreatorAPI, ModManagerAPI } from "@/lib/data-service"
import { type CreatorPal, type ActiveSkill, mockPalTemplates } from "@/lib/mock-data"
import { PalListRow } from "./pal-list-row"
import { SearchSelectorDialog } from "./search-selector-dialog"
import { AddPalModal } from "./add-pal-modal"
import { ConfirmModal } from "@/components/common/confirm-modal"

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
  
  const [isAddOpen, setIsAddOpen] = useState(false)
  const [templates, setTemplates] = useState<string[]>([])
  const [palNames, setPalNames] = useState<Record<string, string>>({})
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)

  // Dynamic Dictionaries populated entirely by the Python Backend
  const [spawners, setSpawners] = useState<Record<string, string>>({})
  const [activeSkills, setActiveSkills] = useState<Record<string, ActiveSkill>>({})

  useEffect(() => {
    async function loadPalsAndCaches() {
      try {
        setLoading(true)
        const [data, caches] = await Promise.all([
          PalCreatorAPI.list(),
          ModManagerAPI.getAltermaticCaches()
        ])
        setPals(data as unknown as CreatorPal[])
        
        if (caches) {
          // Hydrate dynamic menus
          if (caches.monster_spawners) setSpawners(caches.monster_spawners)
          if (caches.active_skills) setActiveSkills(caches.active_skills)
          
          if (caches.templates) {
            const validTemplates = Object.keys(caches.templates)
              .filter(t => t && t !== "None")
              .sort((a, b) => {
                const nameA = (caches.pal_names?.[a] || a).toLowerCase()
                const nameB = (caches.pal_names?.[b] || b).toLowerCase()
                return nameA.localeCompare(nameB)
              })
            setTemplates(validTemplates)
            setPalNames(caches.pal_names || {})
          } else {
            setTemplates(mockPalTemplates)
          }
        }
      } catch (err) {
        console.error("Failed to load custom Pals or caches:", err)
        setTemplates(mockPalTemplates)
      } finally {
        setLoading(false)
      }
    }
    loadPalsAndCaches()
  }, [])

  function updatePal(id: string, patch: Partial<CreatorPal>) {
    setPals((list) => list.map((p) => (p.CharacterID === id ? { ...p, ...patch } : p)))
  }

  function savePal(oldId: string, saved: CreatorPal) {
    setPals((list) => list.map((p) => (p.CharacterID === oldId ? saved : p)))
  }

  async function handleAddConfirm(id: string, templateId: string) {
    setIsAddOpen(false)
    setLoading(true)
    try {
      const newPal = await PalCreatorAPI.add(id, templateId)
      setPals((prev) => [...prev, newPal])
      setExpandedId(newPal.CharacterID)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  async function executeDelete() {
    if (!deleteTarget) return
    const target = deleteTarget
    setDeleteTarget(null)
    setLoading(true)
    try {
      await PalCreatorAPI.delete(target)
      setPals((list) => list.filter((p) => p.CharacterID !== target))
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      {dialog && (
        <SearchSelectorDialog title={dialog.title} dataset={dialog.dataset} palElements={dialog.palElements} onSelect={dialog.onSelect} onClose={() => setDialog(null)} />
      )}
      
      {isAddOpen && (
        <AddPalModal templates={templates} palNames={palNames} onConfirm={handleAddConfirm} onCancel={() => setIsAddOpen(false)} />
      )}

      {deleteTarget && (
        <ConfirmModal 
          title="Confirm Deletion" 
          message={`Are you sure you want to permanently delete custom Pal '${deleteTarget}'?`}
          onConfirm={executeDelete} 
          onCancel={() => setDeleteTarget(null)} 
        />
      )}

      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 className="text-muted-foreground text-xs font-bold uppercase tracking-widest">Pal Definitions</h2>
          <button
            onClick={() => setIsAddOpen(true)}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-primary text-primary text-xs font-semibold hover:bg-primary/10 transition-colors cursor-pointer disabled:opacity-50"
          >
            <Plus className="size-3.5" />
            New Pal
          </button>
        </div>

        {loading ? (
          <p className="text-muted-foreground text-xs italic">Loading Pal definitions...</p>
        ) : pals.length === 0 ? (
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
                spawners={spawners}
                activeSkills={activeSkills}
                onToggle={() => setExpandedId(expandedId === pal.CharacterID ? null : pal.CharacterID)}
                onUpdate={(patch) => updatePal(pal.CharacterID, patch)}
                onOpenDialog={(title, dataset, onSelect, palElements) => setDialog({ title, dataset, onSelect, palElements })}
                onSave={savePal}
                onDelete={() => setDeleteTarget(pal.CharacterID)}
              />
            ))}
          </div>
        )}
      </div>
    </>
  )
}
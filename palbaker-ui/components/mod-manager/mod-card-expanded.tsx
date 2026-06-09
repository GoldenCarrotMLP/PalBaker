"use client"

import { useState, useRef, useEffect } from "react"
import { type ModItem, type AltermaticVariant } from "@/lib/mock-data"
import { Separator } from "@/components/ui/separator"
import { ImagePlus } from "lucide-react"
import { ModManagerAPI } from "@/lib/data-service"
import { convertFileSrc } from "@tauri-apps/api/core"
import { useNotifications } from "./mod-card-expanded/use-notifications"
import { NotificationToast } from "./mod-card-expanded/notification-toast"
import { CriesPanel } from "./mod-card-expanded/cries-panel"
import { AltermaticPanel } from "./mod-card-expanded/altermatic-panel"
import { AddVariantModal } from "./mod-card-expanded/add-variant-modal"
import { EditVariantModal } from "./mod-card-expanded/edit-variant-modal"

interface Props {
  mod: ModItem
  onRefresh: () => void
}

export function ModCardExpanded({ mod, onRefresh }: Props) {
  const { notifications, showNotification, dismissNotification } = useNotifications()
  const iconInputRef = useRef<HTMLInputElement>(null)

  const [altermaticEnabled, setAltermaticEnabled] = useState(mod.is_altermatic_active)
  const [isAddModalOpen,    setIsAddModalOpen]     = useState(false)
  const [editingVariant,    setEditingVariant]     = useState<AltermaticVariant | null>(null)
  const [editingIndex,      setEditingIndex]       = useState(-1)
  const [altermaticMetadata, setAltermaticMetadata] = useState<any>(null)
  const [traitsDb,          setTraitsDb]           = useState<Record<string, string>>({})

  useEffect(() => {
    if (!altermaticEnabled) return
    const load = async () => {
      try {
        const meta   = await ModManagerAPI.altermaticMetadata(mod.name)
        const caches = await ModManagerAPI.getAltermaticCaches()
        setAltermaticMetadata(meta)
        setTraitsDb(caches?.traits_db ?? caches?.passive_skills ?? {})
      } catch (err) {
        console.error("Failed to load Altermatic metadata:", err)
      }
    }
    load()
  }, [altermaticEnabled, mod.name])

  const handleIconChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const reader = new FileReader()
      reader.onload = async () => {
        const bytes = Array.from(new Uint8Array(reader.result as ArrayBuffer))
        await ModManagerAPI.saveModIconBytes(mod.name, file.name, bytes)
        showNotification("Custom Pal Icon updated successfully!", "success")
        onRefresh()
      }
      reader.readAsArrayBuffer(file)
    } catch (err) {
      showNotification(`Failed to save icon: ${err}`, "error", "Operation Failed")
    }
  }

  const handleOpenEdit = (variant: AltermaticVariant, index: number) => {
    setEditingVariant(variant)
    setEditingIndex(index)
  }

  return (
    <div className="border-t border-border px-5 py-5">
      <div className="flex gap-6 items-start">

        {/* Col 1: Custom Pal Icon */}
        <div className="flex flex-col gap-2 shrink-0">
          <span className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">
            Custom Pal Icon
          </span>
          <input
            type="file"
            ref={iconInputRef}
            onChange={handleIconChange}
            accept="image/png, image/dds"
            className="hidden"
          />
          <button
            onClick={() => iconInputRef.current?.click()}
            className="size-20 rounded border border-border bg-muted/50 flex flex-col items-center justify-center gap-1 hover:border-primary/50 transition-colors group cursor-pointer"
            title="Click to set custom Pal Icon"
          >
            {mod.has_icon ? (
              <div className="size-full rounded flex items-center justify-center bg-muted relative">
                {mod.icon_path && (
                  <img
                    src={
                      typeof window !== "undefined" && (window as any).__TAURI_INTERNALS__ !== undefined
                        ? convertFileSrc(mod.icon_path)
                        : mod.icon_path.startsWith("http") ? mod.icon_path : `https://asset.localhost/${mod.icon_path}`
                    }
                    alt="Custom Pal Icon"
                    className="size-full object-cover rounded"
                    onError={(e) => { e.currentTarget.style.display = "none" }}
                  />
                )}
                <span className="text-muted-foreground text-xs font-mono absolute">icon</span>
              </div>
            ) : (
              <ImagePlus className="size-6 text-muted-foreground group-hover:text-primary transition-colors" />
            )}
          </button>
          <span className="text-muted-foreground text-xs font-mono">64x64 PNG/DDS</span>
        </div>

        <Separator orientation="vertical" className="self-stretch opacity-50" />

        {/* Col 2: Cries Replacement */}
        <CriesPanel mod={mod} onRefresh={onRefresh} onNotify={showNotification} />

        <Separator orientation="vertical" className="self-stretch opacity-50" />

        {/* Col 3: Altermatic Variants */}
        <AltermaticPanel
          mod={mod}
          enabled={altermaticEnabled}
          onToggle={setAltermaticEnabled}
          onOpenAdd={() => setIsAddModalOpen(true)}
          onOpenEdit={handleOpenEdit}
          onNotify={showNotification}
          onRefresh={onRefresh}
        />

      </div>

      {/* Modals */}
      {isAddModalOpen && (
        <AddVariantModal
          modName={mod.name}
          localizedName={mod.localized_name}
          blendFiles={altermaticMetadata?.blend_files ?? []}
          onClose={() => setIsAddModalOpen(false)}
          onCreated={onRefresh}
          onNotify={showNotification}
        />
      )}

      {editingVariant && (
        <EditVariantModal
          modName={mod.name}
          variant={editingVariant}
          variantIndex={editingIndex}
          altermaticMetadata={altermaticMetadata}
          traitsDb={traitsDb}
          onClose={() => { setEditingVariant(null); setEditingIndex(-1) }}
          onSaved={onRefresh}
          onNotify={showNotification}
        />
      )}

      <NotificationToast notifications={notifications} onDismiss={dismissNotification} />
    </div>
  )
}

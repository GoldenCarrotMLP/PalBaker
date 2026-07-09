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

  // Derived state sync (prevents react-hooks/set-state-in-effect)
  const [prevPreserve, setPrevPreserve] = useState(mod.preserve_materials)
  const [preserveMaterials, setPreserveMaterials] = useState(mod.preserve_materials !== false)

  if (mod.preserve_materials !== prevPreserve) {
    setPrevPreserve(mod.preserve_materials)
    setPreserveMaterials(mod.preserve_materials !== false)
  }

  const [altermaticEnabled, setAltermaticEnabled] = useState(mod.is_altermatic_active)
  const [isAddModalOpen,    setIsAddModalOpen]     = useState(false)
  const [editingVariant,    setEditingVariant]     = useState<AltermaticVariant | null>(null)
  const [editingIndex,      setEditingIndex]       = useState(-1)
  const [altermaticMetadata, setAltermaticMetadata] = useState<Record<string, unknown> | null>(null)
  const [traitsDb,          setTraitsDb]           = useState<Record<string, string>>({})

  useEffect(() => {
    if (!altermaticEnabled || mod.is_variant) return
    const load = async () => {
      try {
        const meta = await ModManagerAPI.altermaticMetadata(mod.base_pal, mod.name)
        const caches = await ModManagerAPI.getAltermaticCaches()
        setAltermaticMetadata(meta as Record<string, unknown>)
        setTraitsDb(caches?.traits_db ?? caches?.passive_skills ?? {})
      } catch (err) {
        console.error("Failed to load Altermatic metadata:", err)
      }
    }
    load()
  }, [altermaticEnabled, mod.base_pal, mod.name, mod.is_variant])

  const handleIconChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const reader = new FileReader()
      reader.onload = async () => {
        const buffer = reader.result as ArrayBuffer
        const bytes = Array.from(new Uint8Array(buffer))
        await ModManagerAPI.saveModIconBytes(mod.base_pal, mod.name, file.name, bytes)
        showNotification("Custom Pal Icon updated successfully!", "success")
        onRefresh()
      }
      reader.readAsArrayBuffer(file)
    } catch (err) {
      showNotification(`Failed to save icon: ${err}`, "error", "Operation Failed")
    }
  }

  const handlePreserveToggle = async (val: boolean) => {
    try {
      setPreserveMaterials(val)
      await ModManagerAPI.setModPreserveMaterials(mod.base_pal, mod.name, val)
      showNotification(
        val 
          ? "Material preservation enabled! Custom Unreal shaders won't be overwritten. ;3"
          : "Material overwriting enabled. Baseline templates will be re-applied.",
        "success"
      )
      onRefresh()
    } catch (err) {
      showNotification(`Failed to toggle material preservation: ${err}`, "error", "Operation Failed")
    }
  }

  const handleOpenEdit = (variant: AltermaticVariant, index: number) => {
    setEditingVariant(variant)
    setEditingIndex(index)
  }

  return (
    <div className="border-t border-border px-5 py-5">
      <div className="flex gap-6 items-start">
        <div className="flex flex-col gap-4 shrink-0 w-[160px]">
          <div className="flex flex-col gap-2">
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
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img
                      src={
                        typeof window !== "undefined" && (window as unknown as { __TAURI_INTERNALS__?: unknown }).__TAURI_INTERNALS__ !== undefined
                          ? convertFileSrc(mod.icon_path)
                          : mod.icon_path.startsWith("http") ? mod.icon_path : `https://asset.localhost/${mod.icon_path}`
                      }
                      alt="Custom Pal Icon"
                      className="size-full object-cover rounded"
                      onError={(e) => { e.currentTarget.style.display = "none" }}
                    />
                  )}
                </div>
              ) : (
                <ImagePlus className="size-6 text-muted-foreground group-hover:text-primary transition-colors" />
              )}
            </button>
            <span className="text-muted-foreground text-[10px] font-mono leading-none">64x64 PNG/DDS</span>
          </div>

          <Separator className="opacity-30" />

          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between gap-1">
              <span className="text-muted-foreground text-[10px] font-bold uppercase tracking-wider">
                Preserve Shaders
              </span>
              <label className="relative inline-flex items-center cursor-pointer shrink-0">
                <input
                  type="checkbox"
                  checked={preserveMaterials}
                  onChange={(e) => handlePreserveToggle(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-8 h-4.5 bg-muted border border-border peer-checked:bg-primary rounded-full transition-colors" />
                <div className="absolute top-0.5 left-0.5 size-3.5 bg-white rounded-full shadow transition-transform peer-checked:translate-x-3.5" />
              </label>
            </div>
            <p className="text-[9px] text-muted-foreground leading-tight">
              Protects custom Unreal material graphs from being reset on push.
            </p>
          </div>
        </div>

        <Separator orientation="vertical" className="self-stretch opacity-50" />
        <CriesPanel mod={mod} onRefresh={onRefresh} onNotify={showNotification} />

        {!mod.is_variant && (
          <>
            <Separator orientation="vertical" className="self-stretch opacity-50" />
            <AltermaticPanel
              mod={mod}
              enabled={altermaticEnabled}
              onToggle={setAltermaticEnabled}
              onOpenAdd={() => setIsAddModalOpen(true)}
              onOpenEdit={handleOpenEdit}
              onNotify={showNotification}
              onRefresh={onRefresh}
            />
          </>
        )}
      </div>

      {isAddModalOpen && !mod.is_variant && (
        <AddVariantModal
          basePal={mod.base_pal}
          modName={mod.name}
          localizedName={mod.localized_name}
          blendFiles={(altermaticMetadata?.blend_files as string[]) ?? []}
          onClose={() => setIsAddModalOpen(false)}
          onCreated={onRefresh}
          onNotify={showNotification}
        />
      )}

      {editingVariant && !mod.is_variant && (
        <EditVariantModal
          basePal={mod.base_pal}
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
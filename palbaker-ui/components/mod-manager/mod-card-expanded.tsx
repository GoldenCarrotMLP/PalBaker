// palbaker-ui/components/mod-manager/mod-card-expanded.tsx
"use client"

import { useState, useRef, useEffect } from "react"
import { type ModItem, type DynamicPalVariant } from "@/lib/mock-data"
import { Separator } from "@/components/ui/separator"
import { ImagePlus, FileMinus } from "lucide-react"
import { ModManagerAPI } from "@/lib/data-service"
import { convertFileSrc } from "@tauri-apps/api/core"
import { useNotifications } from "./mod-card-expanded/use-notifications"
import { NotificationToast } from "./mod-card-expanded/notification-toast"
import { CriesPanel } from "./mod-card-expanded/cries-panel"
import { DynamicPalsPanel } from "./mod-card-expanded/dynamic-pals-panel"
import { AddVariantModal } from "./mod-card-expanded/add-variant-modal"
import { EditVariantModal } from "./mod-card-expanded/edit-variant-modal"
import { SelectivePushPanel } from "./mod-card-expanded/selective-push-panel"
import { BlacklistModal } from "./mod-card-expanded/blacklist-modal"

interface Props {
  mod: ModItem
  onRefresh: () => void
  onUpdateMod: (modKey: string, patch: Partial<ModItem>) => void
}

export function ModCardExpanded({ mod, onRefresh, onUpdateMod }: Props) {
  const { notifications, showNotification, dismissNotification } = useNotifications()
  const iconInputRef = useRef<HTMLInputElement>(null)

  // Derived state sync (prevents react-hooks/set-state-in-effect)
  const [prevPreserve, setPrevPreserve] = useState(mod.preserve_materials)
  const [preserveMaterials, setPreserveMaterials] = useState(mod.preserve_materials !== false)

  if (mod.preserve_materials !== prevPreserve) {
    setPrevPreserve(mod.preserve_materials)
    setPreserveMaterials(mod.preserve_materials !== false)
  }

  const [dynamicPalsEnabled, setDynamicPalsEnabled] = useState(mod.is_dynamic_pals_active)
  const [isAddModalOpen,    setIsAddModalOpen]     = useState(false)
  const [isBlacklistOpen,   setIsBlacklistOpen]    = useState(false)
  const [editingVariant,    setEditingVariant]     = useState<DynamicPalVariant | null>(null)
  const [editingIndex,      setEditingIndex]       = useState(-1)
  const [dynamicPalsMetadata, setDynamicPalsMetadata] = useState<Record<string, unknown> | null>(null)
  const [traitsDb,          setTraitsDb]           = useState<Record<string, string>>({})

  useEffect(() => {
    if (!dynamicPalsEnabled || mod.is_variant) return
    const load = async () => {
      try {
        const meta = await ModManagerAPI.dynamicPalsMetadata(mod.base_pal, mod.name)
        const caches = await ModManagerAPI.getDynamicPalsCaches()
        setDynamicPalsMetadata(meta as Record<string, unknown>)
        setTraitsDb(caches?.traits_db ?? caches?.passive_skills ?? {})
      } catch (err) {
        console.error("Failed to load Dynamic Pals metadata:", err)
      }
    }
    load()
  }, [dynamicPalsEnabled, mod.base_pal, mod.name, mod.is_variant])

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
        // Silent background refresh to pick up new thumbnail without screen flicker
        onRefresh()
      }
      reader.readAsArrayBuffer(file)
    } catch (err) {
      showNotification(`Failed to save icon: ${err}`, "error", "Operation Failed")
    }
  }

  const handlePreserveToggle = async (val: boolean) => {
    // 1. Instant local + parent in-memory update
    setPreserveMaterials(val)
    onUpdateMod(mod.id || mod.name, { preserve_materials: val })

    // 2. Persist to backend without tearing down view
    try {
      await ModManagerAPI.setModPreserveMaterials(mod.base_pal, mod.name, val)
      showNotification(
        val 
          ? "Material preservation enabled! Custom Unreal shaders won't be overwritten. ;3"
          : "Material overwriting enabled. Baseline templates will be re-applied.",
        "success"
      )
    } catch (err) {
      // Rollback on failure
      setPreserveMaterials(!val)
      onUpdateMod(mod.id || mod.name, { preserve_materials: !val })
      showNotification(`Failed to toggle material preservation: ${err}`, "error", "Operation Failed")
    }
  }

  const handleOpenEdit = (variant: DynamicPalVariant, index: number) => {
    setEditingVariant(variant)
    setEditingIndex(index)
  }

  return (
    <div className="border-t border-border px-5 py-5 relative">
      <div className="flex gap-6 items-start">
        {/* Left Column: Icon & Material Preservation Toggle */}
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
        
        {/* Middle Column: Vocal Cries */}
        <CriesPanel mod={mod} onRefresh={onRefresh} onNotify={showNotification} />

        <Separator orientation="vertical" className="self-stretch opacity-50" />

        {/* Right Column: Dynamic Pals Panel & Selective Push Panel */}
        <div className="flex flex-col gap-4 min-w-[240px] shrink-0">
          {!mod.is_variant && (
            <>
              <DynamicPalsPanel
                mod={mod}
                enabled={dynamicPalsEnabled}
                onToggle={setDynamicPalsEnabled}
                onOpenAdd={() => setIsAddModalOpen(true)}
                onOpenEdit={handleOpenEdit}
                onNotify={showNotification}
                onRefresh={onRefresh}
                onUpdateMod={onUpdateMod}
              />
              <Separator className="opacity-30" />
            </>
          )}

          <SelectivePushPanel
            mod={mod}
            onRefresh={onRefresh}
            onNotify={showNotification}
            onUpdateMod={onUpdateMod}
          />
        </div>
      </div>

      {/* Floating Blacklist Button */}
      <button 
        onClick={() => setIsBlacklistOpen(true)}
        title="Custom Packaging Blacklist"
        className="absolute bottom-4 right-4 p-2 bg-muted/30 hover:bg-muted/80 border border-border rounded-md text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
      >
        <FileMinus className="size-4" />
      </button>

      {isAddModalOpen && !mod.is_variant && (
        <AddVariantModal
          basePal={mod.base_pal}
          modName={mod.name}
          localizedName={mod.localized_name}
          blendFiles={(dynamicPalsMetadata?.blend_files as string[]) ?? []}
          allBlendFiles={dynamicPalsMetadata?.all_blend_files as Record<string, string[]>} // <-- ADD THIS LINE!
          onClose={() => setIsAddModalOpen(false)}
          onCreated={onRefresh}
          onNotify={showNotification}
        />
      )}

      {/* Edit Variant Modal */}
      {editingVariant && !mod.is_variant && (
        <EditVariantModal
          basePal={mod.base_pal}
          modName={mod.name}
          variant={editingVariant}
          variantIndex={editingIndex}
          dynamicPalsMetadata={dynamicPalsMetadata}
          traitsDb={traitsDb}
          onClose={() => { setEditingVariant(null); setEditingIndex(-1) }}
          onSaved={onRefresh}
          onNotify={showNotification}
        />
      )}

      {/* Blacklist Configuration Modal */}
      {isBlacklistOpen && (
        <BlacklistModal
          basePal={mod.base_pal}
          modName={mod.name}
          initialBlacklist={(mod as any).custom_blacklist || []}
          onClose={() => setIsBlacklistOpen(false)}
          onSaved={onRefresh}
          onNotify={showNotification}
        />
      )}

      <NotificationToast notifications={notifications} onDismiss={dismissNotification} />
    </div>
  )
}
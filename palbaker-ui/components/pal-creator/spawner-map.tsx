// palbaker-ui/components/pal-creator/spawner-map.tsx
"use client"

import { useEffect, useRef, useState } from "react"
import { type CreatorPal } from "@/lib/mock-data"
import { initTerrainWorker, useMapTerrain, getHeightAt } from "@/lib/terrain-height"
import { convertFileSrc } from "@tauri-apps/api/core"
import { Crosshair, Map as MapIcon, Trash2, MapPin } from "lucide-react"
import "leaflet/dist/leaflet.css"

interface Props {
  pal: CreatorPal
  onUpdate: (patch: Partial<CreatorPal>) => void
}

const MAPS = {
  world: {
    id: "world",
    label: "World Map",
    tilesDir: "https://custompalspawners.pages.dev/images/tiles/world",
    terrainDir: "https://pub-49e2b368af97475286966f3e6dba0761.r2.dev/CustomPalSpawnersTerrainV2/world",
    minZoom: 0,
    maxZoom: 7,
    maxNativeZoom: 5,
    tileSize: 256,
    waterLevel: -2102.62,
    bounds: [349400, 724400, -1099400, -724400],
  },
  tree: {
    id: "tree",
    label: "World Tree",
    tilesDir: "https://custompalspawners.pages.dev/images/tiles/tree",
    terrainDir: "https://pub-49e2b368af97475286966f3e6dba0761.r2.dev/CustomPalSpawnersTerrainV2/tree",
    minZoom: 0,
    maxZoom: 7,
    maxNativeZoom: 5,
    tileSize: 256,
    waterLevel: -2102.62,
    bounds: [689148.5, -476400, 347351.5, -818197],
  }
}

function worldFromLatLng(lat: number, lng: number, mapDef: any) {
  const [maxX, maxY, minX, minY] = mapDef.bounds;
  return [
    minX + ((lat + 256) / 256) * (maxX - minX),
    minY + (lng / 256) * (maxY - minY),
  ];
}

function latLngFromWorld(wx: number, wy: number, mapDef: any) {
  const [maxX, maxY, minX, minY] = mapDef.bounds;
  return [
    -256 + ((wx - minX) / (maxX - minX)) * 256,
    ((wy - minY) / (maxY - minY)) * 256
  ];
}

export function SpawnerMap({ pal, onUpdate }: Props) {
  const mapContainerRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<any>(null)
  const markersLayerRef = useRef<any>(null)
  
  const [isMapReady, setIsMapReady] = useState(false)
  
  const [activeMap, setActiveMap] = useState<keyof typeof MAPS>("world")
  const [spawnMode, setSpawnMode] = useState<"boss" | "normal">("boss")
  const [selectedPinIndex, setSelectedPinIndex] = useState<number | null>(null)
  const [coords, setCoords] = useState({ x: 0, y: 0, z: 0 })

  const latestPalRef = useRef(pal)
  const latestSpawnModeRef = useRef(spawnMode)
  
  useEffect(() => {
    latestPalRef.current = pal
  }, [pal])

  useEffect(() => {
    latestSpawnModeRef.current = spawnMode
  }, [spawnMode])

  useEffect(() => {
    setIsMapReady(false)
    initTerrainWorker()
    useMapTerrain(MAPS[activeMap].id, MAPS[activeMap].terrainDir, MAPS[activeMap].waterLevel)

    import("leaflet").then((L) => {
      if (!mapContainerRef.current) return

      const bounds = L.latLngBounds([[-256, 0], [0, 256]])

      if (!mapInstanceRef.current) {
        const map = L.map(mapContainerRef.current, {
          crs: L.CRS.Simple,
          zoomControl: false,
          attributionControl: false,
          maxBounds: bounds,
          maxBoundsViscosity: 0.65,
          scrollWheelZoom: true,
          doubleClickZoom: false,
        })
        
        L.control.zoom({ position: 'bottomright' }).addTo(map)
        markersLayerRef.current = L.layerGroup().addTo(map)
        mapInstanceRef.current = map

        let pendingCoords: [number, number] | null = null
        let animFrameId = 0

        map.on("mousemove", (e) => {
          pendingCoords = [e.latlng.lat, e.latlng.lng]
          if (!animFrameId) {
            animFrameId = requestAnimationFrame(() => {
              animFrameId = 0
              if (pendingCoords) {
                const [wx, wy] = worldFromLatLng(pendingCoords[0], pendingCoords[1], MAPS[activeMap])
                setCoords(c => ({ ...c, x: Math.round(wx), y: Math.round(wy) }))
                
                getHeightAt(wx, wy).then(z => {
                  if (z !== null) setCoords(c => ({ ...c, z: Math.round(z) }))
                })
              }
            })
          }
        })

        map.on("dblclick", async (e) => {
          const mode = latestSpawnModeRef.current
          const [wx, wy] = worldFromLatLng(e.latlng.lat, e.latlng.lng, MAPS[activeMap])
          const z = await getHeightAt(wx, wy) ?? MAPS[activeMap].waterLevel
          
          const currentSpawns = latestPalRef.current.FieldBossSpawns || []
          const newSpawn = {
            isBoss: mode === "boss",
            level: mode === "boss" ? 50 : 1,
            levelMax: mode === "boss" ? 50 : 5,
            amountMin: 1,
            amountMax: mode === "boss" ? 1 : 3,
            x: Math.round(wx * 1000) / 1000,
            y: Math.round(wy * 1000) / 1000,
            z: Math.round(z * 1000) / 1000,
            adds: []
          }
          
          const nextSpawns = [...currentSpawns, newSpawn]
          onUpdate({ FieldBossSpawns: nextSpawns })
          setSelectedPinIndex(nextSpawns.length - 1)
        })
      }

      const map = mapInstanceRef.current
      map.eachLayer((layer: any) => {
        if (layer instanceof L.TileLayer) map.removeLayer(layer)
      })

      L.tileLayer(`${MAPS[activeMap].tilesDir}/{z}/{x}/{y}.jpg`, {
        tileSize: MAPS[activeMap].tileSize,
        minZoom: MAPS[activeMap].minZoom,
        maxZoom: MAPS[activeMap].maxZoom,
        maxNativeZoom: MAPS[activeMap].maxNativeZoom,
        bounds,
        noWrap: true,
      }).addTo(map)

      map.setMinZoom(MAPS[activeMap].minZoom)
      map.setMaxZoom(MAPS[activeMap].maxZoom)
      const fit = map.getBoundsZoom(bounds, true)
      map.setMinZoom(Math.max(MAPS[activeMap].minZoom, fit))
      map.setView(bounds.getCenter(), Math.min(MAPS[activeMap].maxZoom, fit + 1.5), { animate: false })
      map.setMaxBounds(bounds)

      setTimeout(() => {
        if (mapInstanceRef.current) {
          mapInstanceRef.current.invalidateSize()
          setIsMapReady(true)
        }
      }, 50)
    })

    return () => {
      setIsMapReady(false)
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove()
        mapInstanceRef.current = null
        markersLayerRef.current = null
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeMap])

  useEffect(() => {
    if (!isMapReady || !mapInstanceRef.current || !markersLayerRef.current) return

    import("leaflet").then((L) => {
      const markersLayer = markersLayerRef.current
      markersLayer.clearLayers()

      const isLive = typeof window !== "undefined" && (window as any).__TAURI_INTERNALS__ !== undefined
      
      const spawns = pal.FieldBossSpawns || []
      spawns.forEach((spawn, idx) => {
        const isBoss = spawn.isBoss !== false
        
        const iconColor = isBoss ? "%23ef4444" : "%2306b6d4" 
        const ringClass = isBoss ? "border-status-error hover:ring-status-error" : "border-primary hover:ring-primary"
        
        const iconUrl = pal.resolved_icon_path 
          ? (isLive ? convertFileSrc(pal.resolved_icon_path) : `https://asset.localhost/${pal.resolved_icon_path}`)
          : `data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='48' height='48'><rect width='48' height='48' rx='24' fill='${iconColor}'/><text x='24' y='32' font-size='24' text-anchor='middle' fill='%23fff' font-family='sans-serif'>?</text></svg>`

        const customIcon = L.divIcon({
          html: `<div class="size-10 rounded-full border-2 ${ringClass} bg-card overflow-hidden shadow-lg hover:ring-2 transition-all flex items-center justify-center"><img src="${iconUrl}" class="w-full h-full object-cover" onerror="this.style.display='none'" /></div>`,
          className: "bg-transparent border-0",
          iconSize: [40, 40],
          iconAnchor: [20, 20],
        })

        const [lat, lng] = latLngFromWorld(spawn.x, spawn.y, MAPS[activeMap])
        const marker = L.marker([lat, lng], { icon: customIcon }).addTo(markersLayer)
        
        marker.on("click", (e) => {
          L.DomEvent.stopPropagation(e)
          setSelectedPinIndex(idx)
        })
      })
    })
  }, [isMapReady, pal.FieldBossSpawns, pal.resolved_icon_path, activeMap])

  const selectedSpawn = selectedPinIndex !== null && pal.FieldBossSpawns ? pal.FieldBossSpawns[selectedPinIndex] : null

  return (
    <div className="flex h-[550px] border border-border rounded-lg overflow-hidden relative">
      
      {/* MAP CANVAS CONTAINER
          - Overrides Leaflet's default white/grey background with PalBaker dark theme
          - Dark-styles the Leaflet zoom control widget
      */}
      <div 
        className="flex-1 relative z-0 !bg-background [&.leaflet-container]:!bg-background [&_.leaflet-tile-pane]:!bg-transparent [&_.leaflet-bar]:!border-border [&_.leaflet-bar_a]:!bg-card [&_.leaflet-bar_a]:!text-foreground [&_.leaflet-bar_a]:!border-border hover:[&_.leaflet-bar_a]:!bg-muted"
        style={{ backgroundColor: "var(--background)" }}
        ref={mapContainerRef}
      >
        
        {/* Floating Controls (Elevated to z-[1001] with event propagation stopped) */}
        <div 
          className="absolute top-4 left-4 z-[1001] flex flex-col gap-2 select-none"
          onPointerDown={(e) => e.stopPropagation()}
          onMouseDown={(e) => e.stopPropagation()}
          onClick={(e) => e.stopPropagation()}
          onDoubleClick={(e) => e.stopPropagation()}
        >
          <div className="bg-card/90 backdrop-blur-md border border-border rounded-md shadow p-1 flex">
            <button 
              type="button"
              onClick={() => setActiveMap("world")}
              className={`px-3 py-1.5 text-xs font-bold rounded cursor-pointer transition-colors ${activeMap === "world" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted"}`}
            >
              World Map
            </button>
            <button 
              type="button"
              onClick={() => setActiveMap("tree")}
              className={`px-3 py-1.5 text-xs font-bold rounded cursor-pointer transition-colors ${activeMap === "tree" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted"}`}
            >
              World Tree
            </button>
          </div>

          <div className="bg-card/90 backdrop-blur-md border border-border rounded-md shadow p-1 flex">
            <button 
              type="button"
              onClick={() => setSpawnMode("boss")}
              className={`px-3 py-1.5 text-xs font-bold rounded cursor-pointer transition-colors ${spawnMode === "boss" ? "bg-status-error text-white" : "text-muted-foreground hover:bg-muted"}`}
            >
              Boss Pin
            </button>
            <button 
              type="button"
              onClick={() => setSpawnMode("normal")}
              className={`px-3 py-1.5 text-xs font-bold rounded cursor-pointer transition-colors ${spawnMode === "normal" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted"}`}
            >
              Normal Pin
            </button>
          </div>
        </div>

        {/* Live Coordinate Readout (Elevated to z-[1001]) */}
        <div 
          className="absolute bottom-4 left-4 z-[1001] bg-card/90 backdrop-blur-md border border-border rounded-md shadow px-3 py-2 flex items-center gap-3 text-xs font-mono select-none"
          onPointerDown={(e) => e.stopPropagation()}
          onMouseDown={(e) => e.stopPropagation()}
        >
          <Crosshair className="size-3.5 text-primary" />
          <span className="text-muted-foreground">X:</span> <span className="text-foreground w-14">{coords.x}</span>
          <span className="text-muted-foreground">Y:</span> <span className="text-foreground w-14">{coords.y}</span>
          <span className="text-muted-foreground">Z:</span> <span className="text-foreground w-14">{coords.z}</span>
        </div>
      </div>

      {/* RIGHT SIDEBAR: SPAWN EDITOR */}
      <div className="w-80 bg-sidebar border-l border-border flex flex-col z-10">
        <div className="p-4 border-b border-border bg-muted/30 flex items-center gap-2">
          <MapIcon className="size-4 text-primary" />
          <span className="font-bold text-sm tracking-wide text-foreground">SPAWN EDITOR</span>
        </div>

        <div className="p-4 flex-1 overflow-y-auto">
          {!selectedSpawn ? (
            <div className="flex flex-col items-center justify-center h-full text-center gap-3 opacity-60 p-4">
              <MapPin className="size-8 text-muted-foreground" />
              <p className="text-xs text-muted-foreground leading-relaxed">
                Select a Pin Type on the left, then double-click anywhere on the map to drop a Spawner.<br/><br/>
                Or click an existing pin icon on the map to edit its properties.
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-5 animate-in fade-in slide-in-from-right-4 duration-200">
              
              <div className="flex items-center justify-between">
                <span className={`text-xs font-bold uppercase tracking-widest ${selectedSpawn.isBoss !== false ? "text-status-error" : "text-primary"}`}>
                  {selectedSpawn.isBoss !== false ? "Alpha Boss Pin" : "Normal Spawner"} #{selectedPinIndex! + 1}
                </span>
                <button 
                  type="button"
                  onClick={() => {
                    const next = [...pal.FieldBossSpawns!]
                    next.splice(selectedPinIndex!, 1)
                    onUpdate({ FieldBossSpawns: next })
                    setSelectedPinIndex(null)
                  }}
                  className="p-1.5 bg-status-error/10 text-status-error hover:bg-status-error hover:text-white rounded transition-colors cursor-pointer"
                  title="Delete Pin"
                >
                  <Trash2 className="size-3.5" />
                </button>
              </div>

              <div className="flex gap-2">
                <div className="flex flex-col gap-1.5 flex-1">
                  <label className="text-[10px] text-muted-foreground uppercase font-semibold">Level Min</label>
                  <input 
                    type="number" min={1} max={200}
                    value={selectedSpawn.level} 
                    onChange={(e) => {
                      const next = [...pal.FieldBossSpawns!]
                      next[selectedPinIndex!].level = parseInt(e.target.value) || 1
                      onUpdate({ FieldBossSpawns: next })
                    }}
                    className="flex h-9 w-full rounded border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                  />
                </div>
                {selectedSpawn.isBoss === false && (
                  <div className="flex flex-col gap-1.5 flex-1">
                    <label className="text-[10px] text-muted-foreground uppercase font-semibold">Level Max</label>
                    <input 
                      type="number" min={1} max={200}
                      value={selectedSpawn.levelMax ?? selectedSpawn.level} 
                      onChange={(e) => {
                        const next = [...pal.FieldBossSpawns!]
                        next[selectedPinIndex!].levelMax = parseInt(e.target.value) || 1
                        onUpdate({ FieldBossSpawns: next })
                      }}
                      className="flex h-9 w-full rounded border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                    />
                  </div>
                )}
              </div>

              {selectedSpawn.isBoss === false && (
                <div className="flex gap-2">
                  <div className="flex flex-col gap-1.5 flex-1">
                    <label className="text-[10px] text-muted-foreground uppercase font-semibold">Group Min</label>
                    <input 
                      type="number" min={1} max={10}
                      value={selectedSpawn.amountMin ?? 1} 
                      onChange={(e) => {
                        const next = [...pal.FieldBossSpawns!]
                        next[selectedPinIndex!].amountMin = parseInt(e.target.value) || 1
                        onUpdate({ FieldBossSpawns: next })
                      }}
                      className="flex h-9 w-full rounded border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                    />
                  </div>
                  <div className="flex flex-col gap-1.5 flex-1">
                    <label className="text-[10px] text-muted-foreground uppercase font-semibold">Group Max</label>
                    <input 
                      type="number" min={1} max={10}
                      value={selectedSpawn.amountMax ?? 3} 
                      onChange={(e) => {
                        const next = [...pal.FieldBossSpawns!]
                        next[selectedPinIndex!].amountMax = parseInt(e.target.value) || 1
                        onUpdate({ FieldBossSpawns: next })
                      }}
                      className="flex h-9 w-full rounded border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                    />
                  </div>
                </div>
              )}

              <div className="flex flex-col gap-2 border-t border-border/40 pt-4 mt-2">
                <label className="text-[10px] text-muted-foreground uppercase font-semibold">Coordinates (X, Y, Z)</label>
                {["x", "y", "z"].map((axis) => (
                  <div key={axis} className="flex items-center gap-2">
                    <span className="w-4 text-xs font-bold text-muted-foreground uppercase">{axis}</span>
                    <input 
                      type="number" step="0.001"
                      value={selectedSpawn[axis as keyof typeof selectedSpawn] as number} 
                      onChange={(e) => {
                        const next = [...pal.FieldBossSpawns!]
                        next[selectedPinIndex!][axis as "x"|"y"|"z"] = parseFloat(e.target.value) || 0
                        onUpdate({ FieldBossSpawns: next })
                      }}
                      className="flex h-8 flex-1 rounded border border-input bg-transparent px-3 py-1 text-xs font-mono shadow-sm"
                    />
                  </div>
                ))}
                <span className="text-[9px] text-muted-foreground leading-tight mt-1">
                  Z-Axis height was auto-calculated based on terrain. Adjust it manually if your Boss spawns under the floor.
                </span>
              </div>

            </div>
          )}
        </div>
      </div>

    </div>
  )
}
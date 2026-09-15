// palbaker-ui/lib/terrain-height.ts

let worker: Worker | null = null;
const pending = new Map<number, { resolve: (z: number | null) => void }>();
let nextId = 1;
let currentMapId = "";
let currentWaterLevel = 0;

export function initTerrainWorker() {
  if (worker || typeof window === "undefined") return;
  worker = new Worker("/scripts/TerrainHeightWorker.js");

  worker.addEventListener("message", (event) => {
    const message = event.data;
    const request = pending.get(message.id);
    if (!request) return;
    pending.delete(message.id);
    request.resolve(message.height);
  });
}

export function useMapTerrain(mapId: string, terrainDir: string, waterLevel: number) {
  if (!worker) initTerrainWorker();
  
  for (const request of pending.values()) request.resolve(null);
  pending.clear();
  
  currentMapId = mapId;
  currentWaterLevel = waterLevel;
  
  worker?.postMessage({ type: "use", mapId, terrainDir });
}

export function getHeightAt(x: number, y: number): Promise<number | null> {
  if (!worker) return Promise.resolve(null);
  
  const id = nextId++;
  return new Promise((resolve) => {
    pending.set(id, { resolve });
    worker!.postMessage({ 
      type: "height", 
      id, 
      mapId: currentMapId, 
      x: Number(x), 
      y: Number(y), 
      waterLevel: currentWaterLevel 
    });
  });
}
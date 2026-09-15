// palbaker-ui/public/scripts/TerrainHeightWorker.js
"use strict";

const CACHE_LIMIT = 64;
const OFFSET = 150;
let activeMap = "";
let generation = 0;
let terrainDir = "";
let gridStep = 100;
let tileSize = 50000;
let compressed = false;
let readyPromise = Promise.resolve();
const cache = new Map();
const loading = new Map();
let chunksByFile = new Map();

function remember(key, value) {
  cache.delete(key);
  cache.set(key, value);
  while (cache.size > CACHE_LIMIT) cache.delete(cache.keys().next().value);
}

async function use(mapId, remoteDir) {
  activeMap = mapId;
  terrainDir = remoteDir;
  loading.clear();
  chunksByFile = new Map();
  const token = ++generation;
  try {
    const response = await fetch(`${terrainDir}/manifest.json`);
    const value = response.ok ? await response.json() : null;
    if (token !== generation || !Array.isArray(value?.chunks)) return;
    gridStep = Number(value.gridStep) || 100;
    tileSize = Number(value.tileSize) || 50000;
    compressed = value.format === "xyz-int32-centi-le-gzip";
    chunksByFile = new Map(value.chunks.map(chunk => [chunk.file, chunk]));
  } catch (_) {
    chunksByFile = new Map();
  }
}

function chunkAtIndex(tileX, tileY) {
  const suffix = compressed ? ".bin.gz" : ".bin";
  const file = `c_${tileX}_${tileY}${suffix}`;
  return chunksByFile.get(file) || null;
}

function chunkAt(x, y) {
  return chunkAtIndex(Math.floor(x / tileSize), Math.floor(y / tileSize));
}

async function fetchChunk(chunk, mapId, token, key) {
  try {
    const response = await fetch(`${terrainDir}/${chunk.file}`);
    if (!response.ok) return null;
    const downloaded = await response.arrayBuffer();
    const decoded = compressed
      ? await new Response(new Blob([downloaded]).stream().pipeThrough(new DecompressionStream("gzip"))).arrayBuffer()
      : downloaded;
    const data = new Int32Array(decoded);
    if (token !== generation) return null;
    const parts = chunk.file.match(/^c_(-?\d+)_(-?\d+)\.bin(?:\.gz)?$/);
    if (!parts) return null;
    const step = gridStep;
    const side = Math.ceil(tileSize / step);
    const baseX = Number(parts[1]) * tileSize;
    const baseY = Number(parts[2]) * tileSize;
    const empty = -2147483648;
    const heights = new Int32Array(side * side);
    heights.fill(empty);
    for (let i = 0; i < data.length; i += 3) {
      const ix = Math.round((data[i] / 100 - baseX) / step);
      const iy = Math.round((data[i + 1] / 100 - baseY) / step);
      if (ix < 0 || ix >= side || iy < 0 || iy >= side) continue;
      const index = iy * side + ix;
      if (heights[index] === empty || data[i + 2] > heights[index]) heights[index] = data[i + 2];
    }
    const indexed = { baseX, baseY, empty, heights, side, step };
    remember(key, indexed);
    return indexed;
  } catch (_) {
    return null;
  }
}

function load(chunk, mapId, token) {
  const key = `${mapId}/${chunk.file}`;
  if (cache.has(key)) {
    const value = cache.get(key);
    remember(key, value);
    return Promise.resolve(value);
  }
  if (!loading.has(key)) {
    const promise = fetchChunk(chunk, mapId, token, key);
    loading.set(key, promise);
    promise.finally(() => {
      if (loading.get(key) === promise) loading.delete(key);
    });
  }
  return loading.get(key);
}

function prefetchNeighbors(x, y, mapId, token) {
  const centerX = Math.floor(x / tileSize);
  const centerY = Math.floor(y / tileSize);
  for (let offsetY = -1; offsetY <= 1; offsetY++) {
    for (let offsetX = -1; offsetX <= 1; offsetX++) {
      if (!offsetX && !offsetY) continue;
      const chunk = chunkAtIndex(centerX + offsetX, centerY + offsetY);
      if (chunk) load(chunk, mapId, token);
    }
  }
}

function estimate(indexed, x, y, waterLevel) {
  const { baseX, baseY, empty, heights, side, step } = indexed;
  const centerX = Math.round((x - baseX) / step);
  const centerY = Math.round((y - baseY) / step);
  const range = Math.max(3, Math.ceil(300 / step));
  const nearest = [];
  for (let iy = Math.max(0, centerY - range); iy <= Math.min(side - 1, centerY + range); iy++) {
    for (let ix = Math.max(0, centerX - range); ix <= Math.min(side - 1, centerX + range); ix++) {
      const rawZ = heights[iy * side + ix];
      if (rawZ === empty) continue;
      const dx = baseX + ix * step - x;
      const dy = baseY + iy * step - y;
      const distance = dx * dx + dy * dy;
      if (distance > 90000) continue;
      const point = { z: rawZ / 100, distance };
      let position = nearest.length;
      while (position > 0 && nearest[position - 1].distance > distance) position--;
      nearest.splice(position, 0, point);
      if (nearest.length > 12) nearest.pop();
    }
  }
  if (!nearest.length) return null;
  if (nearest[0].distance > step * step * 4) return waterLevel;
  if (nearest[0].z <= waterLevel + 50) return waterLevel;
  if (nearest[0].distance < 1) return nearest[0].z + OFFSET;
  let total = 0;
  let weights = 0;
  for (const point of nearest) {
    const weight = 1 / Math.max(point.distance, 1);
    total += point.z * weight;
    weights += weight;
  }
  return total / weights + OFFSET;
}

self.addEventListener("message", async event => {
  const message = event.data;
  if (message.type === "use") {
    readyPromise = use(message.mapId, message.terrainDir);
    await readyPromise;
    return;
  }
  if (message.type !== "height" || message.mapId !== activeMap) return;
  await readyPromise;
  if (message.mapId !== activeMap) return;
  const token = generation;
  const chunk = chunkAt(message.x, message.y);
  const pendingChunk = chunk ? load(chunk, message.mapId, token) : null;
  if (pendingChunk && gridStep >= 40) prefetchNeighbors(message.x, message.y, message.mapId, token);
  const indexed = pendingChunk ? await pendingChunk : null;
  const estimated = indexed ? estimate(indexed, message.x, message.y, message.waterLevel) : null;
  const height = !chunk ? message.waterLevel : indexed ? estimated ?? message.waterLevel : null;
  postMessage({ type: "height", id: message.id, height });
});
# API Reference

## Data Service (`lib/data-service.ts`)

The single abstraction layer for all data fetching. Use these APIs instead of importing mock data directly.

### `ModManagerAPI`

#### `list(): Promise<ModItem[]>`

Get all mods in the workspace.

**Live endpoint**: `manager list`

**Example**:
```typescript
import { ModManagerAPI } from "@/lib/data-service"

const mods = await ModManagerAPI.list()
mods.forEach((mod) => {
  console.log(mod.name, mod.pak_status)
})
```

**Returns**:
```typescript
{
  id: "anubis_model_v4",
  name: "Anubis_Model_v4",
  localized_name: "Anubis Model v4",
  pak_status: "SrcChanged" | "Packed" | "Outdated" | "Unpacked" | "Unextracted",
  modified: "2m ago",
  has_fmodel: boolean,
  has_blend: boolean,
  has_ue: boolean,
  source_modified: boolean,
  badges: [
    { text: "SRC CHANGED", color: "bg-status-warning/20 ...", tooltip: "..." },
    // ...
  ],
  altermatic_variants: [
    {
      label: "base",
      is_base: true,
      Gender: "None",
      IsRarePal: false,
      ReqTrait: [],
      PrefTrait: [],
      MatReplace: [],
      MorphTarget: [],
    },
    // ...
  ],
  // ...
}[]
```

#### `get(modId: string): Promise<ModItem | null>`

Get a single mod by ID.

**Example**:
```typescript
const mod = await ModManagerAPI.get("anubis_model_v4")
if (mod?.pak_status === "SrcChanged") {
  console.log("Source files modified, needs re-cook")
}
```

---

### `PalCreatorAPI`

#### `list(): Promise<CreatorItem[]>`

Get all Pals in the creator list.

**Live endpoint**: `creator list`

**Example**:
```typescript
const pals = await PalCreatorAPI.list()
pals.forEach((pal) => {
  console.log(`${pal.pal_id}: ${pal.name} (${pal.element1}/${pal.element2})`)
})
```

**Returns**:
```typescript
{
  pal_id: "001-B",
  name: "Anubis Prime",
  element1: "Ground",
  element2: "Fire",
  hp: 100,
  attack: 80,
  spawning_logic: "1_10_plain_F_Boss_Anubis",
  learnset: [
    { level: 1, active_move: "Sand Blast", power: 40, element: "Ground" },
    { level: 7, active_move: "Power Shot", power: 35, element: "Neutral" },
  ],
}[]
```

#### `getSpawners(): Promise<Record<string, string>>`

Get all spawner locations (display name → spawn ID mapping).

**Source**: `pythoncli/deps/monster_spawners_cache.json`

**Example**:
```typescript
const spawners = await PalCreatorAPI.getSpawners()

// Build a select dropdown
<select>
  {Object.entries(spawners).map(([displayName, spawnId]) => (
    <option key={spawnId} value={spawnId}>{displayName}</option>
  ))}
</select>
```

**Returns**:
```typescript
{
  "11_1_testarea_1 (Cattiva, Chikipi, Foxparks, Hoocrates)": "11_1_testarea_1",
  "1_10_plain_F_Boss_Anubis (Boss_Anubis)": "1_10_plain_F_Boss_Anubis",
  "2_2_forestsnow_1 (Chillet, Foxcicle, Kitsun, Mimog)": "2_2_forestsnow_1",
  // ...
}
```

#### `save(pal: CreatorItem): Promise<CreatorItem>`

Save or update a Pal. Returns the saved Pal.

**Live endpoint**: `creator save` (POST)

**Example**:
```typescript
const newPal = {
  pal_id: "999",
  name: "CustomPal",
  element1: "Neutral",
  element2: "None",
  // ...
}

const saved = await PalCreatorAPI.save(newPal)
console.log("Saved:", saved.pal_id)
```

---

### `SystemSettingsAPI`

#### `getEnvStatus(): Promise<EnvStatusType>`

Get the status of installed tools (UE5, Blender, FModel, etc.).

**Live endpoint**: `env status`

**Example**:
```typescript
const status = await SystemSettingsAPI.getEnvStatus()

console.log(status.ue_root?.status) // "CONNECTED" | "NOT_FOUND" | "DISCONNECTED"
console.log(status.blender_exe?.status)
console.log(status.fmodel_exe?.status)
```

**Returns**:
```typescript
{
  ue_root: { status: "CONNECTED", path: "C:\\...\\UE_5.1" },
  blender_exe: { status: "CONNECTED", path: "C:\\...\\blender.exe" },
  fmodel_exe: { status: "NOT_FOUND", path: null },
  palworld_exe: { status: "CONNECTED", path: "H:\\...\\Palworld.exe" },
  workspace_root: { status: "CONNECTED", path: "H:\\...\\Output" },
}
```

#### `updatePath(key: string, value: string): Promise<void>`

Update a path setting (e.g., UE5 root, Blender path).

**Live endpoint**: `env set-path` (POST)

**Example**:
```typescript
await SystemSettingsAPI.updatePath("ue_root", "C:\\Program Files\\Epic Games\\UE_5.2")
```

---

### `BuildConsoleAPI`

#### `subscribe(callback: (log: string) => void): () => void`

Subscribe to live console output (logs from Python CLI).

**Live mechanism**: Tauri event listener (`listen("console_output", ...)`)

**Example**:
```typescript
const unsubscribe = BuildConsoleAPI.subscribe((logLine) => {
  console.log("[BUILD]", logLine)
  // Dispatch to state or update UI
})

// Later, unsubscribe:
unsubscribe()
```

---

## Mock Data Types

All types are defined in `lib/mock-data.ts`:

### `ModItem`

```typescript
interface ModItem {
  id: string
  name: string
  localized_name: string
  pak_status: "Unextracted" | "Unpacked" | "Outdated" | "Packed" | "SrcChanged"
  modified: string          // "2m ago", "1h ago", etc.
  source_ext: string        // ".fbx", ".blend", etc.
  has_fmodel: boolean
  has_blend: boolean
  has_ue: boolean
  source_modified: boolean
  has_icon: boolean
  icon_path: string
  badges: ModBadge[]        // Status indicators (SRC CHANGED, ALTERMATIC, etc.)
  sound_metadata: Record<string, SoundEntry>  // Cry names → media info
  audio_overrides: Record<string, string>     // Cry name → override path
  is_altermatic_active: boolean
  altermatic_variants: AltermaticVariant[]
}
```

### `CreatorItem`

```typescript
interface CreatorItem {
  pal_id: string
  name: string
  element1: string
  element2: string | "None"
  hp: number
  attack: number
  defense: number
  sp_attack: number
  sp_defense: number
  speed: number
  work_suitabilities: string[]
  spawning_logic: string      // Spawn ID
  learnset: LearnsetEntry[]
}

interface LearnsetEntry {
  level: number
  active_move: string
  power: number
  element: string
}
```

### `EnvStatusType`

```typescript
interface EnvStatusType {
  ue_root?: { status: string; path: string | null }
  blender_exe?: { status: string; path: string | null }
  fmodel_exe?: { status: string; path: string | null }
  palworld_exe?: { status: string; path: string | null }
  workspace_root?: { status: string; path: string | null }
}
```

---

## Environment Variables

### `NEXT_PUBLIC_USE_LIVE_DATA`

Control whether to use live data or mock data.

```bash
# .env.local
NEXT_PUBLIC_USE_LIVE_DATA=false    # Use mock data (default)
NEXT_PUBLIC_USE_LIVE_DATA=true     # Use live Tauri invoke()
```

### `TAURI_ENV_DEBUG`

Automatically set by `src-tauri/tauri.conf.json` in dev mode. Tells `next.config.ts` to skip static export.

---

## Error Handling

All API functions return `Promise`. Wrap in try/catch:

```typescript
try {
  const mods = await ModManagerAPI.list()
} catch (err) {
  console.error("Failed to fetch mods:", err.message)
  // Show error UI, fall back to mock, etc.
}
```

Common errors:

- **"Live data not yet configured"** — `NEXT_PUBLIC_USE_LIVE_DATA=true` but live API not implemented
- **"Invoke is not defined"** — Component rendered outside Tauri window (SSR)
- **"Python CLI not found"** — Tauri command failed to run Python

---

## Example: Putting It All Together

```typescript
// Page component
import { ModManagerAPI, SystemSettingsAPI } from "@/lib/data-service"
import { useEffect, useState } from "react"

export function ModManagerPage() {
  const [mods, setMods] = useState<ModItem[]>([])
  const [error, setError] = useState("")

  useEffect(() => {
    async function loadData() {
      try {
        const status = await SystemSettingsAPI.getEnvStatus()
        if (status.fmodel_exe?.status !== "CONNECTED") {
          setError("FModel not configured. See System Settings.")
          return
        }

        const modList = await ModManagerAPI.list()
        setMods(modList)
      } catch (err) {
        setError(`Failed to load: ${err.message}`)
      }
    }

    loadData()
  }, [])

  if (error) return <div className="text-red-500">{error}</div>

  return (
    <div>
      {mods.map((mod) => (
        <ModCard key={mod.id} mod={mod} />
      ))}
    </div>
  )
}
```

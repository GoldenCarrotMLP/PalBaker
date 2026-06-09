# Live Data Integration Guide

## Overview

This guide walks you through connecting the Next.js UI to the **real** Python CLI backend. Currently, the app uses mock data. By following these steps, you'll wire up live IPC communication through Tauri.

## Prerequisites

- Rust + Tauri v2 CLI installed on your machine
- Python CLI (`pythoncli/palbaker_cli.py`) working and tested
- Basic understanding of Tauri's `invoke()` system

## Step 1: Define Tauri Commands

Tauri commands are Rust functions exposed to the frontend. They handle communication with Python.

### Create `src-tauri/src/commands.rs`

```rust
// src-tauri/src/commands.rs
use crate::AppState;

#[tauri::command]
pub async fn manager_list(state: tauri::State<'_, AppState>) -> Result<Vec<String>, String> {
  // Call Python CLI: python palbaker_cli.py manager list
  let output = state
    .python_bridge
    .run_command(&["manager", "list"])
    .await
    .map_err(|e| e.to_string())?;
  
  // Parse JSON response
  let json: serde_json::Value = serde_json::from_str(&output)
    .map_err(|e| format!("JSON parse error: {}", e))?;
  
  Ok(/* convert to ModItem[] */)
}

#[tauri::command]
pub async fn creator_list(state: tauri::State<'_, AppState>) -> Result<Vec<String>, String> {
  state.python_bridge.run_command(&["creator", "list"]).await
    .map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn env_status(state: tauri::State<'_, AppState>) -> Result<serde_json::Value, String> {
  state.python_bridge.run_command(&["env", "status"]).await
    .map_err(|e| e.to_string())
    .and_then(|output| {
      serde_json::from_str(&output).map_err(|e| e.to_string())
    })
}
```

### Register Commands in `src-tauri/src/main.rs`

```rust
// src-tauri/src/main.rs
mod commands;

fn main() {
  tauri::Builder::default()
    .invoke_handler(tauri::generate_handler![
      commands::manager_list,
      commands::creator_list,
      commands::env_status,
    ])
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
```

## Step 2: Update Data Service

Edit `lib/data-service.ts` to call Tauri instead of mock data.

```typescript
// lib/data-service.ts
import { invoke } from "@tauri-apps/api/core"

const USE_LIVE_DATA = process.env.NEXT_PUBLIC_USE_LIVE_DATA === "true"

export const ModManagerAPI = {
  async list(): Promise<ModItem[]> {
    if (USE_LIVE_DATA) {
      try {
        const result = await invoke<ModItem[]>("manager_list")
        return result
      } catch (err) {
        console.error("[v0] manager_list failed:", err)
        throw err
      }
    }
    return mockModList
  },

  async get(modId: string): Promise<ModItem | null> {
    const mods = await this.list()
    return mods.find((m) => m.id === modId) || null
  },
}

export const PalCreatorAPI = {
  async list(): Promise<CreatorItem[]> {
    if (USE_LIVE_DATA) {
      return await invoke<CreatorItem[]>("creator_list")
    }
    return mockCreatorList
  },

  async getSpawners(): Promise<Record<string, string>> {
    if (USE_LIVE_DATA) {
      return await invoke<Record<string, string>>("get_spawners")
    }
    return mockSpawnerCache
  },
}

export const SystemSettingsAPI = {
  async getEnvStatus(): Promise<EnvStatusType> {
    if (USE_LIVE_DATA) {
      return await invoke<EnvStatusType>("env_status")
    }
    return mockEnvStatus
  },
}
```

## Step 3: Enable Live Data

Set the environment variable:

```bash
# .env.local or when building
export NEXT_PUBLIC_USE_LIVE_DATA=true

# Then run
pnpm tauri dev
```

Or in `next.config.ts`, you can read from an environment variable:

```typescript
const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_USE_LIVE_DATA: process.env.NEXT_PUBLIC_USE_LIVE_DATA || "false",
  },
}
```

## Step 4: Handle Python CLI Errors

The Python CLI may fail or return errors. Implement proper error handling:

```typescript
export const ModManagerAPI = {
  async list(): Promise<ModItem[]> {
    if (USE_LIVE_DATA) {
      try {
        return await invoke<ModItem[]>("manager_list")
      } catch (err) {
        if (err.includes("CLI not found")) {
          console.error("Python CLI not configured")
          // Fall back to mock or show error UI
          return mockModList
        }
        throw err
      }
    }
    return mockModList
  },
}
```

## Step 5: Add Console Logging

Implement the Build Console to show real Python CLI output:

```typescript
// In app initialization (layout.tsx or main.rs)
import { listen } from "@tauri-apps/api/event"

listen("console_output", (event: Event<string>) => {
  // Event payload is log line from Python
  console.log("[CLI]", event.payload)
  // Dispatch to BuildConsoleAPI or update global state
})
```

Then in `src/main.rs`, capture Python subprocess output:

```rust
// Wrap Python process to capture stdout/stderr
let mut child = Command::new(python_exe)
  .args(&cmd_args)
  .stdout(Stdio::piped())
  .stderr(Stdio::piped())
  .spawn()?;

// Read lines and emit Tauri event
while let Ok(Some(line)) = reader.read_line(&mut buffer) {
  app_handle.emit("console_output", &line)?;
}
```

## Checklist

- [ ] Define all Tauri commands in `src-tauri/src/commands.rs`
- [ ] Register commands in `src-tauri/src/main.rs`
- [ ] Update `lib/data-service.ts` to call `invoke()`
- [ ] Add error handling for CLI failures
- [ ] Set `NEXT_PUBLIC_USE_LIVE_DATA=true`
- [ ] Test `pnpm tauri dev` with real data
- [ ] Verify console logging works
- [ ] Build release: `pnpm tauri build`

## Troubleshooting

### "invoke is not defined"

Make sure you're in a Tauri context. The `invoke` function only works inside Tauri window, not in SSR or during build.

```typescript
// ❌ Wrong
export async function getModList() {
  return await invoke("manager_list") // Fails in SSR
}

// ✅ Right
async function getModList() {
  if (typeof window === "undefined") return mockModList
  return await invoke("manager_list")
}
```

### Commands timeout

Python CLI may take time. Increase Tauri's command timeout in `tauri.conf.json`:

```json
{
  "build": {
    "beforeDevCommand": "TAURI_ENV_DEBUG=true pnpm dev",
    "beforeBuildCommand": "pnpm build"
  }
}
```

### Mismatch between types

Ensure Rust types match TypeScript types. Use `serde_json` and strong typing:

```rust
#[derive(serde::Serialize)]
pub struct ModItem {
  pub id: String,
  pub name: String,
  // ... match TypeScript ModItem shape exactly
}
```

## Next: Deployment

Once live data is working, you can build and distribute:

```bash
pnpm tauri build        # Creates installer in src-tauri/target/release/bundle/
```

The built app will static-export the UI and bundle it with Tauri's webview.

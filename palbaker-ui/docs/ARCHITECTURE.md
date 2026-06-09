# PalBaker UI Architecture

## Overview

PalBaker UI is a Next.js 16 + Tauri v2 desktop app that manages Palworld mods and custom Pals. It communicates with a Python CLI backend (`pythoncli/`) through Tauri's IPC layer.

## Tech Stack

- **Frontend**: Next.js 16 (App Router), React 19, TypeScript
- **Desktop Shell**: Tauri v2 with static export (no Node.js server at runtime)
- **Styling**: Tailwind CSS v4 + shadcn/ui (nova preset)
- **State Management**: React hooks + Context (NavContext for page routing)
- **Navigation**: State-based routing (no URL changes) for Tauri compatibility

## Project Structure

```
palbaker-ui/
├── app/
│   ├── layout.tsx           # Root layout with NavProvider + TooltipProvider
│   ├── page.tsx             # Renders nothing (AppShell owns all rendering)
│   ├── globals.css          # Design tokens, Tailwind directives
│   ├── pal-creator/
│   ├── system-settings/
│   └── (other routes)
├── components/
│   ├── app-shell.tsx        # Main app wrapper + sidebar + top bar + footer
│   ├── build-console.tsx    # Terminal footer
│   ├── mod-manager/
│   │   ├── mod-manager-page.tsx
│   │   ├── mod-card.tsx     # Individual mod item card
│   │   └── mod-card-expanded.tsx
│   ├── pal-creator/
│   ├── system-settings/
│   └── ui/                  # shadcn components
├── lib/
│   ├── mock-data.ts         # 💾 Current mock data
│   ├── data-service.ts      # 🔌 Data abstraction layer (switch between mock/live)
│   ├── nav-context.tsx      # Global page navigation state
│   └── utils.ts
├── src-tauri/               # Tauri desktop app
│   ├── tauri.conf.json      # App config, window, build commands
│   ├── Cargo.toml
│   └── src/
│       ├── main.rs
│       └── lib.rs
├── docs/                    # 📖 Documentation
├── next.config.ts           # Conditional static export (dev vs prod)
└── package.json
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    PalBaker Tauri App                       │
├─────────────────────────────────────────────────────────────┤
│  React Components (mod-manager, pal-creator, etc.)          │
│         ↓                                                    │
│  DataService API (lib/data-service.ts)                      │
│         ↓                                                    │
│  [Mock Data] OR [Tauri IPC] OR [HTTP to Python Server]      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
         ┌──────────────────────────────┐
         │    PalBaker Python CLI       │
         │  (pythoncli/palbaker_cli.py) │
         │                              │
         │ ├─ manager:list              │
         │ ├─ creator:list              │
         │ ├─ env:status                │
         │ └─ (more commands...)        │
         └──────────────────────────────┘
```

## Key Abstractions

### 1. Data Service Layer (`lib/data-service.ts`)

A single source of truth for all data fetching. Allows switching between mock and live data with a flag.

```typescript
// Current: uses mock
export const ModManagerAPI = {
  async list(): Promise<ModItem[]> {
    if (USE_LIVE_DATA) {
      // TODO: invoke("manager_list")
    }
    return mockModList
  },
}

// Usage in components:
const mods = await ModManagerAPI.list()
```

### 2. Navigation Context (`lib/nav-context.tsx`)

Global state for page routing (since Tauri can't use dynamic routing).

```typescript
export type Page = "mod-manager" | "pal-creator" | "system-settings"

export function useNav() {
  return useContext(NavContext) // { page, setPage, search, setSearch }
}
```

### 3. Mock Data (`lib/mock-data.ts`)

All mock data is derived from `pythoncli/cli_queries_dump.json` and follows the exact shapes that the Python CLI returns. This ensures seamless switching to live data.

## Development Workflow

### Running in Dev Mode

```bash
pnpm dev        # Starts Next.js dev server at http://localhost:3000
pnpm tauri dev  # Opens Tauri webview pointed at localhost:3000
```

The `TAURI_ENV_DEBUG=true` flag tells `next.config.ts` to skip static export, so hot-reload works.

### Switching to Live Data

1. In `src-tauri/src/main.rs` or `src/lib.rs`, implement Tauri commands that invoke Python CLI methods
2. In `lib/data-service.ts`, uncomment the TODO sections and implement the actual `invoke()` calls
3. Set `NEXT_PUBLIC_USE_LIVE_DATA=true` in `.env.local`

Example Tauri command (to be implemented):

```rust
// src/lib.rs
#[tauri::command]
fn manager_list(state: tauri::State<AppState>) -> Result<Vec<ModItem>, String> {
  state.python_bridge.run_command("manager", "list")
    .map_err(|e| e.to_string())
}
```

## Component Guidelines

### Page Components

- Live in `components/<page>/<page>-page.tsx`
- Export a single component called `<Page>Page` (e.g., `ModManagerPage`)
- Use `useNav()` to access global page + search state
- Fetch data via `DataService` API (never directly import mock-data or call Python)

### Reusable Components

- Live in `components/<section>/<component>.tsx`
- Accept data as props, never fetch directly
- Keep state local unless it needs to be global (use NavContext)

### State Management

- **Local component state**: `useState` for UI-only state (expanded rows, filters, form inputs)
- **Cross-component shared**: `NavContext` for page + search (auto-resets on page change)
- **Never**: localStorage or unnecessary Context providers

## Debugging

- Check `console.log("[v0] ...")` statements in the browser DevTools console
- In Tauri dev mode, right-click → Inspect to open DevTools
- For Python CLI issues, check the Build Console footer (live logs from Python)

## Performance

- Static export in production means no server runtime cost
- CSS + JS are all bundled into `out/` directory
- Tauri loads from `file://` directly in production
- For dev, HMR is enabled via the `assetPrefix` pointing to localhost:3000

## Next Steps

See `LIVE_DATA_INTEGRATION.md` for step-by-step instructions on wiring up Python CLI communication.

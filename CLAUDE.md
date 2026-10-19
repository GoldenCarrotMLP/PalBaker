# PalBaker Architecture & Coding Guidelines (Claude Code Reference)

PalBaker is an automated modding pipeline for Palworld. It is a monorepo consisting of a **Next.js 16 + Tauri v2 (Rust)** desktop frontend (`palbaker-ui`) and a **Python 3.10+** headless CLI backend (`palbaker-cli`).

## Core Frontend Conventions (Next.js & Tauri)
1. **Static Export Only**: Next.js is configured for `output: "export"`. There is no Node.js backend or SSR at runtime. Do NOT write Next.js API routes or server actions.
2. **State-Based Routing**: Tauri's `file://` scheme breaks standard Next.js App Router URLs. Do NOT use `<Link href="...">` or `useRouter()`. All navigation is handled via `<AppShell>` and `useNav()` from `lib/nav-context.tsx`.
3. **Data Fetching Abstraction**: UI components must NEVER call Python or `invoke()` directly. All data fetching routes through `lib/data-service.ts`, which bridges to `src-tauri/src/commands.rs`.
4. **TailwindCSS v4**: We use Tailwind v4. There is no `tailwind.config.ts`. All tokens, colors, and theme variables are defined in `app/globals.css` using the `@theme inline` directive.
5. **Task Queueing**: Long-running Python tasks (cooking, Blender) must be dispatched via `useTaskQueue()` (`lib/task-queue-context.tsx`). It manages concurrency (e.g., 1 Unreal task, 3 Blender tasks) and parses live JSONL `progress` streams.

## Core Backend Conventions (Python CLI)
1. **No Blind String Replacements**: When retargeting ASTs, replace full package paths (`/Game/Pal...`) BEFORE bare class names. Base game VFX/Audio must retain their original paths.
2. **Tagged Serialization in UE 5.1**: Ensure `HasUnversionedProperties = False` on patched UAssetAPI ASTs to prevent `Array.cpp` buffer overflow crashes in Unreal Engine.
3. **Blender 5.x Slotted Actions**: Do not access `act.fcurves` directly. Use `is_action_empty(act)`. Only auto-push actions beginning with `AS_` into NLA tracks.
4. **Stateless JSON Output**: The CLI must print standard logs to `stdout`, but output final results or streams as single-line JSON (`{"status": "success", ...}`).

## Repository Directory Index

### 🖥️ Frontend (`palbaker-ui/`)
- `app/layout.tsx` & `page.tsx`: Entry point. Mounts React contexts and `<AppShell />`.
- `app/globals.css`: Tailwind v4 theme definitions and Shadcn/ui tokens.
- `components/app-shell.tsx`: Main layout wrapper, sidebar, and view switcher.
- `components/build-console.tsx`: Global terminal UI streaming Python JSONL output.
- `components/mod-manager/`: Mod list UI, expansion cards, animations NLA editor, and dynamic variants list.
- `components/pal-creator/`: Standalone Pal UI, stats sliders, learnset matrices, and interactive Leaflet map (`spawner-map.tsx`).
- `components/system-settings/`: Configures UE5, Blender, FModel paths, and UE4SS installations.
- `lib/data-service.ts`: API Facade. Routes to `mock-data.ts` in dev, or `invoke()` in production.
- `lib/nav-context.tsx`: Global state routing for Tauri.
- `lib/task-queue-context.tsx`: Async subprocess task manager for the UI.
- `lib/terrain-height.ts` & `public/scripts/TerrainHeightWorker.js`: Web worker for processing binary heightmaps for Boss Spawner Z-axis calculations.
- `src-tauri/src/commands.rs`: Rust IPC bridge. Spawns `palbaker_cli.py` as a subprocess and pipes stdout back to React.

### ⚙️ Backend (`palbaker-cli/`)
- `palbaker_cli.py`: Unified CLI router.
- `build_mod.py`: Headless pipeline worker (Blender FBX export -> UE Remote Import -> Micro-cooking -> UnrealPak).
- `unreal_scripts/`: Python scripts injected over UDP into running Unreal Editor (`importer.py`, `materials.py`, `rigging.py`).
- `utils/anim_patcher/`: UAssetAPI logic for cloning sequences, montages, and injecting anim notifies.
- `utils/blender_utils/`: Low-level Blender version-safe adapters.
- `utils/blueprint_patcher/`: AST mutator for generating PalActor Blueprints, mounted weapons, funnels, and bosses.
- `utils/dynamic_pals/`: Runtime variant swapping logic and Format V2 ModelJSON generation.
- `utils/extractor/`: Uses `cue4parse.exe` to dump raw `.psk` models, datatables, and localization strings.
- `utils/creator/`: Manages PalSchema exports, `.json` manifests, and dynamic dependency scraping.

### 🏗️ Build System
- `build-release.mjs`: Complete monorepo compiler. Compiles Python via PyInstaller, stages binaries into Tauri resources, runs `pnpm tauri build`, and auto-uploads to GitHub Releases.
- `scripts/update-version.mjs`: Automated SemVer bumper triggered via Git pre-commit hooks.
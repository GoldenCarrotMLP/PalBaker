# PalBaker

Palworld mod toolchain — monorepo.

```
palbaker/
├── pythoncli/        # Python CLI server (existing)
└── palbaker-ui/      # Next.js frontend + Tauri desktop shell
    └── src-tauri/    # Rust/Tauri application shell
```

## Prerequisites

- [Node.js](https://nodejs.org) >= 20
- [pnpm](https://pnpm.io) >= 9 — `npm i -g pnpm`
- [Rust](https://rustup.rs) (stable toolchain) — `rustup update stable`
- Platform build deps for Tauri v2: https://v2.tauri.app/start/prerequisites/

## Install dependencies

```bash
pnpm install
```

## Development (Next.js only)

```bash
pnpm dev
# opens http://localhost:3000
```

## Development (Tauri desktop)

```bash
pnpm tauri dev
# builds Rust shell, opens webview pointed at the Next.js dev server
```

## Production build (desktop app)

```bash
pnpm tauri build
# outputs installer to palbaker-ui/src-tauri/target/release/bundle/
```

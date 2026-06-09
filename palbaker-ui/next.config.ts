import type { NextConfig } from "next"

const isProd = process.env.NODE_ENV === "production"
const internalHost = process.env.TAURI_DEV_HOST || "localhost"

const nextConfig: NextConfig = {
  // Required for Tauri: export as static files, no Node.js server
  output: "export",
  // next/image doesn't work without a server
  images: { unoptimized: true },
  // In dev, Tauri points the webview at the Next.js dev server.
  // In prod, Tauri loads from the `out/` directory directly (file://).
  assetPrefix: isProd ? undefined : `http://${internalHost}:3000`,
}

export default nextConfig

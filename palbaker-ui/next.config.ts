import type { NextConfig } from "next"

const isProd = process.env.NODE_ENV === "production"
const isTauriDev = process.env.TAURI_ENV_DEBUG === "true"

const nextConfig: NextConfig = {
  // Static export only in production builds (not in Tauri dev)
  ...(isProd && !isTauriDev && { output: "export" }),
  // next/image doesn't work without a server
  images: { unoptimized: true },
}

export default nextConfig

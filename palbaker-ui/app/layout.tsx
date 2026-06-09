import type { Metadata } from "next"
import { Inter } from "next/font/google"
import { Geist_Mono } from "next/font/google"
import "./globals.css"
import { TooltipProvider } from "@/components/ui/tooltip"
import { AppShell } from "@/components/app-shell"
import { NavProvider } from "@/lib/nav-context"

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" })
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-mono" })

export const metadata: Metadata = {
  title: "PalBaker v2.4.0-stable",
  description: "Automated modding toolchain for Palworld — asset extraction, Blender pipeline, UE5 integration.",
  themeColor: "#031427",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`bg-background ${inter.variable} ${geistMono.variable} font-sans`}>
      <body className="antialiased">
        <NavProvider>
          <TooltipProvider>
            <AppShell />
          </TooltipProvider>
        </NavProvider>
      </body>
    </html>
  )
}

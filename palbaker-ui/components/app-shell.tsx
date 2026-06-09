"use client"

import { useState, useEffect } from "react"
import { cn } from "@/lib/utils"
import { useNav, type Page } from "@/lib/nav-context"
import { BuildConsole } from "@/components/build-console"
import { ModManagerPage } from "@/components/mod-manager/mod-manager-page"
import { PalCreatorPage } from "@/components/pal-creator/pal-creator-page"
import { SystemSettingsPage } from "@/components/system-settings/system-settings-page"
import { SystemSettingsAPI } from "@/lib/data-service"
import {
  LayoutGrid,
  PawPrint,
  Settings,
  HelpCircle,
  BookOpen,
  Bell,
  Terminal,
  User,
} from "lucide-react"
import { Separator } from "@/components/ui/separator"

const NAV_ITEMS: { page: Page; label: string; icon: React.ElementType }[] = [
  { page: "mod-manager",     label: "Mod Manager",     icon: LayoutGrid },
  { page: "pal-creator",     label: "Pal Creator",     icon: PawPrint   },
  { page: "system-settings", label: "System Settings", icon: Settings   },
]

const BOTTOM_ITEMS = [
  { label: "Documentation", icon: BookOpen },
  { label: "Support",       icon: HelpCircle },
]

const PAGE_INFO: Record<Page, { title: string; subtitle: string; searchPlaceholder: string }> = {
  "mod-manager":     { title: "Mod Manager",     subtitle: "ACTIVE WORKSPACE / LOCAL_CACHE", searchPlaceholder: "Search mods..."     },
  "pal-creator":     { title: "Pal Creator",     subtitle: "New Species Definition",         searchPlaceholder: "Search templates..." },
  "system-settings": { title: "System Settings", subtitle: "ENVIRONMENT CONFIG",             searchPlaceholder: "Search settings..."  },
}

export function AppShell() {
  const { page, setPage, search, setSearch } = useNav()
  const info = PAGE_INFO[page]
  const [version, setVersion] = useState("v2.4.0-experimental")

  useEffect(() => {
    async function loadVersion() {
      try {
        const v = await SystemSettingsAPI.getAppVersion()
        setVersion(v)
      } catch (err) {
        console.error("Failed to load app version:", err)
      }
    }
    loadVersion()
  }, [])

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      {/* Sidebar */}
      <aside className="flex flex-col w-[210px] shrink-0 bg-sidebar border-r border-border">
        {/* Logo */}
        <div className="px-5 pt-6 pb-5">
          <div className="text-primary font-bold text-xl leading-none tracking-wide">PALBAKER</div>
          <div className="text-muted-foreground text-xs mt-1 font-mono">{version}</div>
        </div>

        <Separator className="opacity-50" />

        {/* Main nav */}
        <nav className="flex-1 flex flex-col gap-1 px-3 py-4">
          {NAV_ITEMS.map(({ page: p, label, icon: Icon }) => {
            const active = page === p
            return (
              <button
                key={p}
                onClick={() => setPage(p)}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors w-full text-left",
                  active
                    ? "bg-sidebar-accent text-primary"
                    : "text-sidebar-foreground hover:bg-sidebar-accent/60 hover:text-foreground"
                )}
              >
                <Icon className={cn("size-4 shrink-0", active ? "text-primary" : "text-muted-foreground")} />
                {label}
              </button>
            )
          })}
        </nav>

        <Separator className="opacity-50" />

        {/* Bottom links */}
        <nav className="flex flex-col gap-1 px-3 py-3">
          {BOTTOM_ITEMS.map(({ label, icon: Icon }) => (
            <button
              key={label}
              className="flex items-center gap-3 px-3 py-2 rounded-md text-sm text-muted-foreground hover:text-foreground hover:bg-sidebar-accent/60 transition-colors w-full text-left"
            >
              <Icon className="size-4 shrink-0" />
              {label}
            </button>
          ))}
        </nav>
      </aside>

      {/* Main content area */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Top header */}
        <header className="flex items-center gap-4 px-6 h-14 border-b border-border bg-surface shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <span className="text-foreground font-bold text-lg whitespace-nowrap">{info.title}</span>
            <span className="text-border">|</span>
            <span className="text-muted-foreground text-sm truncate">{info.subtitle}</span>
          </div>
          <div className="flex items-center gap-2 ml-auto">
            <div className="relative hidden md:flex items-center">
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={info.searchPlaceholder}
                className="w-52 bg-muted/50 border border-border rounded-md pl-9 pr-3 py-1.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <svg className="absolute left-2.5 size-4 text-muted-foreground pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
              </svg>
            </div>
            <button className="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors" aria-label="Notifications">
              <Bell className="size-4" />
            </button>
            <button className="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors" aria-label="Terminal">
              <Terminal className="size-4" />
            </button>
            <button className="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors" aria-label="Profile">
              <User className="size-4" />
            </button>
          </div>
        </header>

        {/* Page content — kept mounted to preserve form state and prevent IPC refetching */}
        <main className="flex-1 overflow-y-auto px-6 py-5">
          <div className={cn(page !== "mod-manager" && "hidden")}>
            <ModManagerPage />
          </div>
          <div className={cn(page !== "pal-creator" && "hidden")}>
            <PalCreatorPage />
          </div>
          <div className={cn(page !== "system-settings" && "hidden")}>
            <SystemSettingsPage />
          </div>
        </main>

        <BuildConsole />
      </div>
    </div>
  )
}

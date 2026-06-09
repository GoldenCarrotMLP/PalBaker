"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { BuildConsole } from "@/components/build-console"
import {
  LayoutGrid,
  PawPrint,
  Settings,
  HelpCircle,
  BookOpen,
  Bell,
  Terminal,
  UploadCloud,
  User,
} from "lucide-react"
import { Separator } from "@/components/ui/separator"

const NAV_ITEMS = [
  { href: "/", label: "Mod Manager", icon: LayoutGrid },
  { href: "/pal-creator", label: "Pal Creator", icon: PawPrint },
  { href: "/system-settings", label: "System Settings", icon: Settings },
]

const BOTTOM_ITEMS = [
  { href: "/docs", label: "Documentation", icon: BookOpen },
  { href: "/support", label: "Support", icon: HelpCircle },
]

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      {/* Sidebar */}
      <aside className="flex flex-col w-[210px] shrink-0 bg-sidebar border-r border-border">
        {/* Logo */}
        <div className="px-5 pt-6 pb-5">
          <div className="text-primary font-bold text-xl leading-none tracking-wide">PALBAKER</div>
          <div className="text-muted-foreground text-xs mt-1 font-mono">v2.4.0-stable</div>
        </div>

        <Separator className="opacity-50" />

        {/* Main nav */}
        <nav className="flex-1 flex flex-col gap-1 px-3 py-4">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
            const active = href === "/" ? pathname === "/" : pathname.startsWith(href)
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                  active
                    ? "bg-sidebar-accent text-primary"
                    : "text-sidebar-foreground hover:bg-sidebar-accent/60 hover:text-foreground"
                )}
              >
                <Icon
                  className={cn("size-4 shrink-0", active ? "text-primary" : "text-muted-foreground")}
                />
                {label}
              </Link>
            )
          })}
        </nav>

        {/* Push to Unreal CTA */}
        <div className="px-3 pb-4">
          <button className="w-full py-2.5 rounded-md bg-primary text-primary-foreground text-sm font-bold tracking-wider uppercase hover:opacity-90 transition-opacity">
            Push to Unreal
          </button>
        </div>

        <Separator className="opacity-50" />

        {/* Bottom links */}
        <nav className="flex flex-col gap-1 px-3 py-3">
          {BOTTOM_ITEMS.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className="flex items-center gap-3 px-3 py-2 rounded-md text-sm text-muted-foreground hover:text-foreground hover:bg-sidebar-accent/60 transition-colors"
            >
              <Icon className="size-4 shrink-0" />
              {label}
            </Link>
          ))}
        </nav>
      </aside>

      {/* Main content area */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Top header */}
        <TopHeader pathname={pathname} />

        {/* Page content */}
        <main className="flex-1 overflow-y-auto px-6 py-5">
          {children}
        </main>

        {/* Build Console Terminal */}
        <BuildConsole />
      </div>
    </div>
  )
}

function TopHeader({ pathname }: { pathname: string }) {
  const pageInfo = getPageInfo(pathname)

  return (
    <header className="flex items-center gap-4 px-6 h-14 border-b border-border bg-surface shrink-0">
      <div className="flex items-center gap-3 min-w-0">
        <span className="text-foreground font-bold text-lg whitespace-nowrap">{pageInfo.title}</span>
        {pageInfo.subtitle && (
          <>
            <span className="text-border">|</span>
            <span className="text-muted-foreground text-sm truncate">{pageInfo.subtitle}</span>
          </>
        )}
      </div>

      <div className="flex items-center gap-2 ml-auto">
        {/* Search */}
        <div className="relative hidden md:flex items-center">
          <input
            type="text"
            placeholder={pageInfo.searchPlaceholder}
            className="w-52 bg-muted/50 border border-border rounded-md pl-9 pr-3 py-1.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          />
          <svg className="absolute left-2.5 size-4 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
          </svg>
        </div>
        <button className="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
          <Bell className="size-4" />
        </button>
        <button className="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
          <Terminal className="size-4" />
        </button>
        <button className="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
          <User className="size-4" />
        </button>
      </div>
    </header>
  )
}

function getPageInfo(pathname: string) {
  if (pathname.startsWith("/pal-creator")) {
    return {
      title: "Pal Creator",
      subtitle: "New Species Definition",
      searchPlaceholder: "Search templates...",
    }
  }
  if (pathname.startsWith("/system-settings")) {
    return {
      title: "System Settings",
      subtitle: "ENVIRONMENT CONFIG",
      searchPlaceholder: "Search settings...",
    }
  }
  return {
    title: "Mod Manager",
    subtitle: "ACTIVE WORKSPACE / LOCAL_CACHE",
    searchPlaceholder: "Search mods...",
  }
}

"use client"

import { createContext, useContext, useState } from "react"

export type Page = "mod-manager" | "pal-creator" | "system-settings"

interface NavContextValue {
  page: Page
  setPage: (p: Page) => void
}

const NavContext = createContext<NavContextValue>({
  page: "mod-manager",
  setPage: () => {},
})

export function NavProvider({ children }: { children: React.ReactNode }) {
  const [page, setPage] = useState<Page>("mod-manager")
  return <NavContext.Provider value={{ page, setPage }}>{children}</NavContext.Provider>
}

export function useNav() {
  return useContext(NavContext)
}

"use client"

import { createContext, useContext, useState } from "react"

export type Page = "mod-manager" | "pal-creator" | "system-settings"

interface NavContextValue {
  page: Page
  setPage: (p: Page) => void
  search: string
  setSearch: (q: string) => void
  refreshTrigger: number
  invalidateCache: () => void
}

const NavContext = createContext<NavContextValue>({
  page: "mod-manager",
  setPage: () => {},
  search: "",
  setSearch: () => {},
  refreshTrigger: 0,
  invalidateCache: () => {},
})

export function NavProvider({ children }: { children: React.ReactNode }) {
  const [page, setPage] = useState<Page>("mod-manager")
  const [search, setSearch] = useState("")
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  function handleSetPage(p: Page) {
    setPage(p)
    setSearch("") // clear search on page change
  }

  function invalidateCache() {
    setRefreshTrigger((prev) => prev + 1)
  }

  return (
    <NavContext.Provider value={{ page, setPage: handleSetPage, search, setSearch, refreshTrigger, invalidateCache }}>
      {children}
    </NavContext.Provider>
  )
}

export function useNav() {
  return useContext(NavContext)
}
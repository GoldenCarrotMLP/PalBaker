"use client"

import { createContext, useContext, useState } from "react"

export type Page = "mod-manager" | "pal-creator" | "system-settings"

interface NavContextValue {
  page: Page
  setPage: (p: Page) => void
  search: string
  setSearch: (q: string) => void
}

const NavContext = createContext<NavContextValue>({
  page: "mod-manager",
  setPage: () => {},
  search: "",
  setSearch: () => {},
})

export function NavProvider({ children }: { children: React.ReactNode }) {
  const [page, setPage] = useState<Page>("mod-manager")
  const [search, setSearch] = useState("")

  function handleSetPage(p: Page) {
    setPage(p)
    setSearch("") // clear search on page change
  }

  return (
    <NavContext.Provider value={{ page, setPage: handleSetPage, search, setSearch }}>
      {children}
    </NavContext.Provider>
  )
}

export function useNav() {
  return useContext(NavContext)
}

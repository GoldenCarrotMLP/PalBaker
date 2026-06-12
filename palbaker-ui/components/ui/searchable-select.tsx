"use client"

import * as React from "react"
import { Check, ChevronsUpDown, Search } from "lucide-react"
import { cn } from "@/lib/utils"

interface Option {
  value: string
  label: string
}

interface SearchableSelectProps {
  value: string
  onChange: (val: string) => void
  options: Option[]
  placeholder?: string
  emptyText?: string
  className?: string
}

export function SearchableSelect({
  value,
  onChange,
  options,
  placeholder = "Select option...",
  emptyText = "No results found.",
  className,
}: SearchableSelectProps) {
  const [open, setOpen] = React.useState(false)
  const [search, setSearch] = React.useState("")
  const containerRef = React.useRef<HTMLDivElement>(null)

  // Close popover when clicking outside the container boundary
  React.useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    if (open) {
      document.addEventListener("mousedown", handleClickOutside)
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside)
    }
  }, [open])

  const selectedOption = options.find((opt) => opt.value === value)

  const filteredOptions = React.useMemo(() => {
    const query = search.toLowerCase().trim()
    if (!query) return options
    return options.filter(
      (opt) =>
        opt.label.toLowerCase().includes(query) ||
        opt.value.toLowerCase().includes(query)
    )
  }, [options, search])

  // Auto scroll list container to active item when expanding popover
  const listRef = React.useRef<HTMLDivElement>(null)
  React.useEffect(() => {
    if (open && listRef.current) {
      const activeItem = listRef.current.querySelector("[data-active='true']")
      if (activeItem) {
        activeItem.scrollIntoView({ block: "nearest" })
      }
    }
  }, [open])

  return (
    <div ref={containerRef} className={cn("relative w-full", className)}>
      {/* Trigger Button (Standardized to h-9 to align with text inputs) */}
      <button
        type="button"
        onClick={() => {
          setOpen(!open)
          setSearch("")
        }}
        className="flex h-9 w-full items-center justify-between rounded-lg border border-input bg-muted/50 px-3 py-1 text-sm text-foreground shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary text-left cursor-pointer transition-colors hover:bg-muted/80"
      >
        <span className="truncate">
          {selectedOption ? selectedOption.label : placeholder}
        </span>
        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
      </button>

      {/* Dropdown Popover */}
      {open && (
        <div className="absolute left-0 right-0 z-50 mt-1 max-h-60 flex flex-col overflow-hidden rounded-md border border-border bg-popover text-popover-foreground shadow-xl animate-in fade-in duration-100 slide-in-from-top-1">
          {/* Search Input Box */}
          <div className="flex items-center border-b border-border px-2 shrink-0 bg-muted/20">
            <Search className="mr-2 h-3.5 w-3.5 shrink-0 opacity-50 text-muted-foreground" />
            <input
              type="text"
              placeholder="Type to filter..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="flex h-8 w-full bg-transparent py-1 text-xs outline-none placeholder:text-muted-foreground/60 border-0 focus:ring-0"
              autoFocus
            />
          </div>

          {/* Options list wrapper */}
          <div
            ref={listRef}
            className="overflow-y-auto flex-1 py-1 max-h-48 scrollbar-thin"
          >
            {filteredOptions.length === 0 ? (
              <div className="px-3 py-2 text-xs text-muted-foreground italic text-center">
                {emptyText}
              </div>
            ) : (
              filteredOptions.map((opt) => {
                const isSelected = opt.value === value
                return (
                  <button
                    key={opt.value}
                    type="button"
                    data-active={isSelected}
                    onClick={() => {
                      onChange(opt.value)
                      setOpen(false)
                      setSearch("")
                    }}
                    className={cn(
                      "relative flex w-full select-none items-center rounded-sm py-1.5 pl-8 pr-2 text-xs text-foreground hover:bg-accent hover:text-accent-foreground outline-none cursor-pointer text-left transition-colors",
                      isSelected && "bg-accent/40 text-primary font-medium"
                    )}
                  >
                    {isSelected && (
                      <span className="absolute left-2.5 flex h-3.5 w-3.5 items-center justify-center">
                        <Check className="h-3.5 w-3.5 text-primary" />
                      </span>
                    )}
                    <span className="truncate">{opt.label}</span>
                  </button>
                )
              })
            )}
          </div>
        </div>
      )}
    </div>
  )
}
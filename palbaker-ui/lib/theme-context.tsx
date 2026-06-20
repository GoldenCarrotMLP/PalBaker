"use client"

import { createContext, useContext, useState, useCallback, useEffect, useRef } from "react"
import {
  type ColorHCL,
  type ThemePreset,
  deriveTokens,
  applyTokens,
  DEFAULT_THEME,
  BUILT_IN_PRESETS,
} from "./theme-engine"

interface ThemeContextValue {
  active: ThemePreset
  base: ColorHCL
  accent: ColorHCL
  layerDepth: number
  borderWeight: number
  presets: ThemePreset[]
  setBase: (c: Partial<ColorHCL>) => void
  setAccent: (c: Partial<ColorHCL>) => void
  setLayerDepth: (v: number) => void
  setBorderWeight: (v: number) => void
  setActivePreset: (preset: ThemePreset) => void
  saveCustomPreset: (name: string) => void
  deleteCustomPreset: (name: string) => void
  renameCustomPreset: (oldName: string, newName: string) => void
  duplicatePreset: (source: ThemePreset, newName: string) => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

const STORAGE_KEY = "palbaker-theme"
const CUSTOM_PRESETS_KEY = "palbaker-custom-presets"

function loadSavedPreset(): ThemePreset | null {
  if (typeof window === "undefined") return null
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch {}
  return null
}

function loadCustomPresets(): ThemePreset[] {
  if (typeof window === "undefined") return []
  try {
    const raw = localStorage.getItem(CUSTOM_PRESETS_KEY)
    if (raw) return JSON.parse(raw)
  } catch {}
  return []
}

function saveCustomPresets(presets: ThemePreset[]) {
  if (typeof window === "undefined") return
  localStorage.setItem(CUSTOM_PRESETS_KEY, JSON.stringify(presets))
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const saved = useRef(loadSavedPreset())
  const [customPresets, setCustomPresets] = useState<ThemePreset[]>(loadCustomPresets)

  const [active, setActive] = useState<ThemePreset>(saved.current ?? DEFAULT_THEME)
  const [base, setBaseState] = useState<ColorHCL>(active.base)
  const [accent, setAccentState] = useState<ColorHCL>(active.accent)
  const [layerDepth, setLayerDepthState] = useState<number>(active.layerDepth ?? 1)
  const [borderWeight, setBorderWeightState] = useState<number>(active.borderWeight ?? 1)

  // Derive and inject tokens whenever base, accent, layerDepth, or borderWeight changes
  const rafRef = useRef<number>(0)
  useEffect(() => {
    cancelAnimationFrame(rafRef.current)
    rafRef.current = requestAnimationFrame(() => {
      const tokens = deriveTokens(base, accent, layerDepth, borderWeight)
      applyTokens(tokens)
    })
    return () => cancelAnimationFrame(rafRef.current)
  }, [base, accent, layerDepth, borderWeight])

  // Persist active theme to localStorage
  useEffect(() => {
    if (typeof window === "undefined") return
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...active, base, accent, layerDepth, borderWeight }))
  }, [base, accent, layerDepth, borderWeight, active.name])

  const setBase = useCallback((patch: Partial<ColorHCL>) => {
    setBaseState((prev) => ({ ...prev, ...patch }))
  }, [])

  const setAccent = useCallback((patch: Partial<ColorHCL>) => {
    setAccentState((prev) => ({ ...prev, ...patch }))
  }, [])

  const setLayerDepth = useCallback((v: number) => {
    setLayerDepthState(v)
  }, [])

  const setBorderWeight = useCallback((v: number) => {
    setBorderWeightState(v)
  }, [])

  const setActivePreset = useCallback((preset: ThemePreset) => {
    setActive(preset)
    setBaseState(preset.base)
    setAccentState(preset.accent)
    setLayerDepthState(preset.layerDepth ?? 1)
    setBorderWeightState(preset.borderWeight ?? 1)
  }, [])

  const saveCustomPreset = useCallback((name: string) => {
    const preset: ThemePreset = { name, base, accent, layerDepth, borderWeight }
    setCustomPresets((prev) => {
      const next = [...prev.filter((p) => p.name !== name), preset]
      saveCustomPresets(next)
      return next
    })
    setActive(preset)
  }, [base, accent, layerDepth, borderWeight])

  const deleteCustomPreset = useCallback((name: string) => {
    setCustomPresets((prev) => {
      const next = prev.filter((p) => p.name !== name)
      saveCustomPresets(next)
      return next
    })
  }, [])

  const renameCustomPreset = useCallback((oldName: string, newName: string) => {
    setCustomPresets((prev) => {
      const next = prev.map((p) => (p.name === oldName ? { ...p, name: newName } : p))
      saveCustomPresets(next)
      return next
    })
  }, [])

  const duplicatePreset = useCallback((source: ThemePreset, newName: string) => {
    const preset: ThemePreset = { name: newName, base: { ...source.base }, accent: { ...source.accent }, layerDepth: source.layerDepth ?? 1, borderWeight: source.borderWeight ?? 1 }
    setCustomPresets((prev) => {
      const next = [...prev, preset]
      saveCustomPresets(next)
      return next
    })
  }, [])

  const allPresets = [...BUILT_IN_PRESETS, ...customPresets]

  return (
    <ThemeContext.Provider
      value={{
        active,
        base,
        accent,
        layerDepth,
        borderWeight,
        presets: allPresets,
        setBase,
        setAccent,
        setLayerDepth,
        setBorderWeight,
        setActivePreset,
        saveCustomPreset,
        deleteCustomPreset,
        renameCustomPreset,
        duplicatePreset,
      }}
    >
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider")
  return ctx
}

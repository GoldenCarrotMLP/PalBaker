"use client"

import { useState, useEffect } from "react"
import { X, Copy, Check, FileText, ChevronRight, ChevronDown, BookOpen, Loader2, FolderOpen, Folder, Home } from "lucide-react"
import { cn } from "@/lib/utils"

interface DocLink {
  title: string
  url: string
}

interface DocCategory {
  title: string
  links: DocLink[]
  isOpen: boolean
}

interface MarkdownCodeBlockProps {
  code: string
  language?: string
}

function MarkdownCodeBlock({ code, language }: MarkdownCodeBlockProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error("Failed to copy code block:", err)
    }
  }

  return (
    <pre className="relative group bg-console-bg border border-border p-4 rounded-md font-mono text-xs text-foreground/90 overflow-x-auto my-4 max-w-full">
      <div className="flex justify-between items-center text-[10px] text-muted-foreground uppercase border-b border-border/40 pb-2 mb-2 font-sans select-none">
        <span>{language || "code"}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 hover:text-foreground transition-colors cursor-pointer"
        >
          {copied ? (
            <>
              <Check className="size-3 text-status-success" />
              <span className="text-status-success">Copied</span>
            </>
          ) : (
            <>
              <Copy className="size-3" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      <code>{code}</code>
    </pre>
  )
}

function renderInlineContent(text: string, onInternalNavigate: (url: string) => void): React.ReactNode[] {
  const regex = /(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))/g
  const parts = text.split(regex)

  return parts.map((part, idx) => {
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={idx} className="bg-muted px-1.5 py-0.5 rounded font-mono text-xs text-primary">{part.slice(1, -1)}</code>
    }
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={idx} className="font-bold text-foreground">{part.slice(2, -2)}</strong>
    }
    if (part.startsWith("[") && part.includes("](")) {
      const match = part.match(/\[([^\]]+)\]\(([^)]+)\)/)
      if (match) {
        const [, label, url] = match
        
        if (url.startsWith("/docs/")) {
          return (
            <button
              key={idx}
              onClick={() => onInternalNavigate(url)}
              className="text-primary hover:underline font-semibold cursor-pointer"
            >
              {label}
            </button>
          )
        }
        
        return (
          <a key={idx} href={url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline font-semibold">
            {label}
          </a>
        )
      }
    }
    return part
  })
}

function parseAndRenderMarkdown(content: string, onInternalNavigate: (url: string) => void): React.ReactNode[] {
  // Strip Windows Carriage Returns to ensure correct line matching
  const cleanContent = content.replace(/\r/g, "")
  const lines = cleanContent.split("\n")
  const elements: React.ReactNode[] = []
  
  let currentCodeBlock: string[] = []
  let inCodeBlock = false
  let codeLang = ""

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]

    if (line.startsWith("```")) {
      if (inCodeBlock) {
        elements.push(<MarkdownCodeBlock key={`code-${i}`} code={currentCodeBlock.join("\n")} language={codeLang} />)
        currentCodeBlock = []
        inCodeBlock = false
      } else {
        inCodeBlock = true
        codeLang = line.slice(3).trim()
      }
      continue
    }

    if (inCodeBlock) {
      currentCodeBlock.push(line)
      continue
    }

    if (line.startsWith("# ")) {
      elements.push(<h1 key={i} className="text-xl font-bold text-primary mt-6 mb-3 border-b border-border pb-1.5">{renderInlineContent(line.slice(2), onInternalNavigate)}</h1>)
      continue
    }
    if (line.startsWith("## ")) {
      elements.push(<h2 key={i} className="text-lg font-bold text-foreground mt-5 mb-2.5">{renderInlineContent(line.slice(3), onInternalNavigate)}</h2>)
      continue
    }
    if (line.startsWith("### ")) {
      elements.push(<h3 key={i} className="text-base font-bold text-foreground mt-4 mb-2">{renderInlineContent(line.slice(4), onInternalNavigate)}</h3>)
      continue
    }
    if (line.startsWith("#### ")) {
      elements.push(<h4 key={i} className="text-sm font-bold text-foreground mt-3 mb-1.5 italic">{renderInlineContent(line.slice(5), onInternalNavigate)}</h4>)
      continue
    }

    if (line.startsWith("- ") || line.startsWith("* ")) {
      elements.push(
        <ul key={i} className="list-disc pl-5 my-1 text-sm text-foreground/85">
          <li>{renderInlineContent(line.slice(2), onInternalNavigate)}</li>
        </ul>
      )
      continue
    }

    if (line.trim() === "---") {
      elements.push(<hr key={i} className="border-border/60 my-6" />)
      continue
    }

    if (line.trim() === "") {
      elements.push(<div key={i} className="h-2" />)
      continue
    }

    elements.push(
      <p key={i} className="text-sm text-foreground/85 leading-relaxed my-2">
        {renderInlineContent(line, onInternalNavigate)}
      </p>
    )
  }

  return elements
}

interface DocsModalProps {
  onClose: () => void
}

export function DocsModal({ onClose }: DocsModalProps) {
  const [categories, setCategories] = useState<DocCategory[]>([])
  const [activeUrl, setActiveUrl] = useState<string>("/docs/index.md")
  const [content, setContent] = useState<string>("")
  const [loading, setLoading] = useState<boolean>(true)
  const [indexLoading, setIndexLoading] = useState<boolean>(true)

  // 1. Fetch and Parse the Master Index on Mount
  useEffect(() => {
    async function loadIndex() {
      try {
        const res = await fetch("/docs/index.md")
        if (res.ok) {
          const text = await res.text()
          const parsedCategories: DocCategory[] = []
          let currentCat: DocCategory | null = null
          
          // Strip Carriage Returns to normalize string endings
          const cleanText = text.replace(/\r/g, "")
          const lines = cleanText.split("\n")
          
          for (const line of lines) {
            // Match Folder/Category (e.g., "- Mod Manager Pipeline")
            const catMatch = line.match(/^[-*]\s+([^\[\]]+)$/)
            if (catMatch) {
              currentCat = { title: catMatch[1].trim(), links: [], isOpen: false }
              parsedCategories.push(currentCat)
              continue
            }
            
            // Match Link inside Folder (e.g., "  - [Extracting Game Assets](/docs/getting-started/extraction.md)")
            const linkMatch = line.match(/^\s+[-*]\s+\[([^\]]+)\]\(([^)]+)\)$/)
            if (linkMatch && currentCat) {
              currentCat.links.push({ title: linkMatch[1].trim(), url: linkMatch[2].trim() })
            }
          }

          // Open the first category by default
          if (parsedCategories.length > 0) {
            parsedCategories[0].isOpen = true
          }
          
          setCategories(parsedCategories)
        }
      } catch (err) {
        console.error("Failed to parse master index:", err)
      } finally {
        setIndexLoading(false)
      }
    }
    loadIndex()
  }, [])

  // 2. Fetch Active Content whenever activeUrl changes
  useEffect(() => {
    async function loadDocument() {
      setLoading(true)
      try {
        const response = await fetch(`${activeUrl}?t=${Date.now()}`)
        if (response.ok) {
          const text = await response.text()
          setContent(text)
        } else {
          setContent(`# 404: Document Not Found\nWe couldn't find the documentation file at \`${activeUrl}\`.\n\nMake sure the file exists in the \`public\` folder and matches the path in \`index.md\`!`)
        }
      } catch (err: any) {
        setContent(`# Error\nAn unexpected network exception occurred while fetching \`${activeUrl}\`: ${err.message || err}`)
      } finally {
        setLoading(false)
      }
    }
    loadDocument()
  }, [activeUrl])

  const toggleCategory = (idx: number) => {
    setCategories((prev) => 
      prev.map((cat, i) => i === idx ? { ...cat, isOpen: !cat.isOpen } : cat)
    )
  }

  // Derive title for the header
  let activeTitle = "Welcome"
  if (activeUrl !== "/docs/index.md") {
    for (const cat of categories) {
      const match = cat.links.find((l) => l.url === activeUrl)
      if (match) {
        activeTitle = match.title
        break
      }
    }
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-fade-in">
      <div className="bg-card border border-border rounded-lg shadow-2xl w-full max-w-6xl h-[85vh] flex overflow-hidden">
        
        {/* Left Column: Index/File Tree View */}
        <aside className="w-72 shrink-0 border-r border-border bg-sidebar p-4 flex flex-col gap-4">
          <div className="flex items-center gap-2 text-primary">
            <BookOpen className="size-4 shrink-0" />
            <span className="font-extrabold text-xs uppercase tracking-widest">
              DOCS / DIRECTORY
            </span>
          </div>
          
          <nav className="flex-1 flex flex-col gap-1 overflow-y-auto pr-1">
            {indexLoading ? (
              <div className="flex items-center gap-2 text-muted-foreground text-xs p-2">
                <Loader2 className="size-3.5 animate-spin" /> Loading map...
              </div>
            ) : (
              <>
                {/* Master Home Link */}
                <button
                  onClick={() => setActiveUrl("/docs/index.md")}
                  className={cn(
                    "flex items-center gap-2.5 w-full px-3 py-2 mb-2 rounded-md text-xs font-semibold tracking-wide text-left transition-colors cursor-pointer",
                    activeUrl === "/docs/index.md" ? "bg-primary/10 text-primary" : "text-foreground hover:bg-sidebar-accent/50"
                  )}
                >
                  <Home className="size-3.5" />
                  Home
                </button>

                {/* Collapsible Categories */}
                {categories.map((cat, cIdx) => (
                  <div key={cIdx} className="flex flex-col gap-0.5">
                    <button
                      onClick={() => toggleCategory(cIdx)}
                      className="flex items-center justify-between w-full px-2 py-1.5 rounded-md text-xs font-semibold text-muted-foreground hover:text-foreground hover:bg-sidebar-accent/30 transition-colors cursor-pointer group"
                    >
                      <div className="flex items-center gap-2">
                        {cat.isOpen ? <FolderOpen className="size-3.5" /> : <Folder className="size-3.5" />}
                        {cat.title}
                      </div>
                      {cat.isOpen ? <ChevronDown className="size-3" /> : <ChevronRight className="size-3" />}
                    </button>
                    
                    {cat.isOpen && (
                      <div className="flex flex-col gap-0.5 pl-4 ml-3 border-l border-border/50 mt-0.5 mb-2">
                        {cat.links.map((link) => {
                          const isActive = activeUrl === link.url
                          return (
                            <button
                              key={link.url}
                              onClick={() => setActiveUrl(link.url)}
                              className={cn(
                                "flex items-center gap-2 w-full px-2 py-1.5 rounded-md text-xs font-medium text-left transition-colors cursor-pointer",
                                isActive
                                  ? "bg-sidebar-accent text-primary font-bold"
                                  : "text-sidebar-foreground hover:bg-sidebar-accent/50 hover:text-foreground"
                              )}
                            >
                              <FileText className={cn("size-3 shrink-0", isActive ? "text-primary" : "text-muted-foreground")} />
                              <span className="truncate">{link.title}</span>
                            </button>
                          )
                        })}
                      </div>
                    )}
                  </div>
                ))}
              </>
            )}
          </nav>
        </aside>

        {/* Right Column: Markdown Viewer Pane */}
        <main className="flex-1 min-w-0 bg-background flex flex-col">
          
          {/* Header */}
          <header className="flex items-center justify-between px-8 h-12 border-b border-border bg-surface shrink-0">
            <div className="flex items-center gap-2 font-bold text-sm tracking-wide text-foreground">
              <span>{activeUrl.split("/").slice(0, -1).join("/")}</span>
              <span className="text-border">/</span>
              <span className="text-primary">{activeUrl.split("/").pop()}</span>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
              title="Close Documentation"
            >
              <X className="size-4" />
            </button>
          </header>

          {/* Render Pane */}
          <div className="flex-1 overflow-y-auto px-10 py-6">
            <div className="max-w-4xl mx-auto pb-10">
              {loading ? (
                <div className="flex flex-col items-center justify-center h-48 gap-3 text-muted-foreground">
                  <Loader2 className="size-6 animate-spin text-primary" />
                  <span className="text-xs font-mono">Loading document...</span>
                </div>
              ) : (
                parseAndRenderMarkdown(content, (url) => setActiveUrl(url))
              )}
            </div>
          </div>

        </main>
        
      </div>
    </div>
  )
}
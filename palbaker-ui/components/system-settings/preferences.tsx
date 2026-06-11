"use client"

export function Preferences({ showMappedNames, onToggle }: { showMappedNames: boolean, onToggle: (v: boolean) => void }) {
  return (
    <section className="bg-card rounded-md border border-border p-5 flex flex-col gap-4">
      <div className="flex items-center gap-2 mb-1">
        <span className="size-4 text-primary">⊙</span>
        <h2 className="text-foreground font-bold text-sm uppercase tracking-widest">Preferences</h2>
      </div>

      <div className="bg-muted/40 rounded-md border border-border p-4 flex items-start justify-between gap-4">
        <div>
          <div className="text-foreground text-sm font-semibold">SHOW MAPPED NAMES</div>
          <div className="text-muted-foreground text-xs mt-1 leading-relaxed">
            Display human-readable asset aliases instead of raw internal IDs
          </div>
        </div>
        <label className="shrink-0 cursor-pointer">
          <div className="relative w-11 h-6">
            <input
              type="checkbox"
              checked={showMappedNames}
              onChange={(e) => onToggle(e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-muted border border-border peer-checked:bg-status-success rounded-full transition-colors" />
            <div className="absolute top-0.5 left-0.5 size-5 bg-white rounded-full shadow transition-transform peer-checked:translate-x-5" />
          </div>
        </label>
      </div>
    </section>
  )
}
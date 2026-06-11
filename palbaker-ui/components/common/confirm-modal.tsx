"use client"
import { X } from "lucide-react"

interface Props {
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  danger?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export function ConfirmModal({ title, message, confirmText = "Confirm", cancelText = "Cancel", danger = true, onConfirm, onCancel }: Props) {
  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-background border border-border rounded-lg shadow-lg w-full max-w-md flex flex-col p-6 gap-4">
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-lg text-foreground">{title}</h3>
          <button onClick={onCancel} className="text-muted-foreground hover:text-foreground cursor-pointer">
            <X className="size-5" />
          </button>
        </div>
        <p className="text-sm text-foreground/80">{message}</p>
        <div className="flex justify-end gap-3 mt-4">
          <button onClick={onCancel} className="h-9 px-4 rounded text-sm font-semibold border border-input bg-transparent hover:bg-muted/50 transition-colors cursor-pointer">
            {cancelText}
          </button>
          <button onClick={onConfirm} className={`h-9 px-4 rounded text-sm font-semibold transition-colors cursor-pointer text-white shadow ${danger ? "bg-status-error hover:bg-status-error/90" : "bg-primary hover:bg-primary/90"}`}>
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  )
}
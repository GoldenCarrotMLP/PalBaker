// lib/api/core.ts
export const USE_LIVE_DATA = typeof window !== "undefined" && (window as unknown as { __TAURI_INTERNALS__?: unknown }).__TAURI_INTERNALS__ !== undefined;

export const IS_DEV = typeof window !== "undefined" && (
  process.env.NODE_ENV === "development" || 
  !(window as unknown as { __TAURI_INTERNALS__?: unknown }).__TAURI_INTERNALS__
);

/**
 * When the CLI exits non-zero, Rust rejects with the whole JSONL stdout. Returns the last
 * {"status": "error" | "validation_failed"} (or error_code) envelope in it, if any.
 */
function findErrorEnvelope(raw: string): Record<string, unknown> | null {
  const lines = raw.split(/\r?\n/)
  for (let i = lines.length - 1; i >= 0; i--) {
    const line = lines[i]
    const start = line.indexOf("{")
    const end = line.lastIndexOf("}")
    if (start < 0 || end <= start) continue
    try {
      const parsed = JSON.parse(line.slice(start, end + 1))
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        const obj = parsed as Record<string, unknown>
        if (obj.status === "error" || obj.status === "validation_failed" || typeof obj.error_code === "string") {
          return obj
        }
      }
    } catch {
      // Not a JSON line
    }
  }
  return null
}

export function handleBackendError(err: unknown): never {
  let cleanMessage = "";
  let errorCode: string | null = null;

  if (typeof err === "string") {
    const envelope = findErrorEnvelope(err)
    if (envelope) {
      err = envelope
    }
  }

  if (err && typeof err === "object") {
    const errObj = err as Record<string, unknown>;
    errorCode = typeof errObj.error_code === "string" ? errObj.error_code : null;
    
    if (errObj.status === "validation_failed") {
      // Stringify the full validation object so the UI can catch it
      throw new Error(JSON.stringify(errObj))
    }

    cleanMessage = typeof errObj.message === "string" 
      ? errObj.message 
      : (typeof errObj.error === "string" ? errObj.error : JSON.stringify(err));
  } else {
    cleanMessage = String(err);
    try {
      const parsed = JSON.parse(cleanMessage);
      if (parsed && typeof parsed === "object") {
        const parsedObj = parsed as Record<string, unknown>;
        if (typeof parsedObj.error_code === "string") {
          errorCode = parsedObj.error_code;
        } else if (typeof parsedObj.message === "string") {
          cleanMessage = parsedObj.message;
        } else if (typeof parsedObj.error === "string") {
          cleanMessage = parsedObj.error;
        }
      }
    } catch {
      // Clean bypass
    }
  }

  // Only these codes have dedicated wizards; other codes (TIMEOUT, CRASH, ...) keep their descriptive message
  if (errorCode === "UNREAL_CLOSED" || errorCode === "REMOTE_EXEC_DISABLED") {
    throw new Error(errorCode);
  }
  throw new Error(cleanMessage || errorCode || "Unknown backend error");
}
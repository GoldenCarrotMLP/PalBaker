// lib/api/core.ts
export const USE_LIVE_DATA = typeof window !== "undefined" && (window as unknown as { __TAURI_INTERNALS__?: unknown }).__TAURI_INTERNALS__ !== undefined;

export const IS_DEV = typeof window !== "undefined" && (
  process.env.NODE_ENV === "development" || 
  !(window as unknown as { __TAURI_INTERNALS__?: unknown }).__TAURI_INTERNALS__
);

export function handleBackendError(err: unknown): never {
  let cleanMessage = "";
  let errorCode: string | null = null;

  if (err && typeof err === "object") {
    const errObj = err as Record<string, unknown>;
    errorCode = typeof errObj.error_code === "string" ? errObj.error_code : null;
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

  if (errorCode) {
    throw new Error(errorCode);
  }
  throw new Error(cleanMessage);
}
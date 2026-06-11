// lib/api/core.ts
export const USE_LIVE_DATA = typeof window !== "undefined" && (window as any).__TAURI_INTERNALS__ !== undefined;

export const IS_DEV = typeof window !== "undefined" && (
  process.env.NODE_ENV === "development" || 
  !(window as any).__TAURI_INTERNALS__
);

export function handleBackendError(err: any): never {
  let cleanMessage = String(err);
  try {
    const parsed = JSON.parse(cleanMessage);
    if (parsed.error_code) {
      throw new Error(parsed.error_code);
    }
    if (parsed.message) {
      cleanMessage = parsed.message;
    } else if (parsed.error) {
      cleanMessage = parsed.error;
    }
  } catch (e) {
    // If JSON parsing fails (e.g. raw "CLI exited with status 1" strings),
    // we do absolutely nothing. We just let the cleanMessage string pass through intact!
  }
  throw new Error(cleanMessage);
}
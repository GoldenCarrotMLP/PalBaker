# pythoncli/utils/sidecar_helper.py
import json
import os

def load_sidecar(path: str) -> dict:
    """Safely loads a companion sidecar JSON."""
    if os.path.exists(path) and os.path.getsize(path) > 0:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_sidecar(path: str, data: dict):
    """Safely writes a companion sidecar JSON to disk."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"[Sidecar Helper] Error saving sidecar: {e}")

def update_sidecar_fields(path: str, **kwargs) -> dict:
    """
    Performs a non-destructive delta-merge.
    Preserves all existing properties (like Gender, IsRarePal, etc.) and only updates the requested keys.
    """
    data = load_sidecar(path)
    for k, v in kwargs.items():
        data[k] = v
    save_sidecar(path, data)
    return data
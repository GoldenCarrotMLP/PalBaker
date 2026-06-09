import os
import json

MAP_FILE = "pal_names_map.json"
_names_cache = {}

def load_names_map():
    global _names_cache
    if _names_cache:
        return _names_cache
    
    # Force loading of the name map from the root PalBaker directory
    map_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), MAP_FILE)
    if not os.path.exists(map_path):
        return {}
        
    try:
        with open(map_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            rows = data.get("Rows", {})
            for key, val in rows.items():
                localized = val.get("TextData", {}).get("LocalizedString", key)
                _names_cache[key] = str(localized).strip()
    except Exception as e:
        print(f"Error loading name map: {e}")
        
    return _names_cache

def get_localized_name(internal_name: str) -> str:
    cache = load_names_map()
    return cache.get(internal_name, internal_name)
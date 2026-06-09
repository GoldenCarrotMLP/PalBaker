# Technical Debt: Hardcoded Game Metadata and Folder Structures

## 1. Directory Path Assumptions
### Description
The scanning and pathing engine (`utils/scanner.py` and `build_mod.py`) assumes a rigid folder structure under the FModel export directory and the Unreal project `Content` folder:
* `Exports/Pal/Content/Pal/Model/Character/Monster`
* `Exports/Pal/Content/Pal/Model/Character/Pending Monster`
### Debt / Risk
* **Category Expansion:** If Pocketpair introduces new character directories (e.g., `RaidMonster`, `DlcMonster`, or `NPC`) in future game updates, the manager will completely fail to detect them until the folder array is manually updated in Python.
* **Hardcoded Fallbacks:** If the script fails to parse the FModel output path, it defaults to a hardcoded fallback path (`/Game/Pal/Model/Character/Monster/WeaselDragon`).

## 2. Rule-Based Material Parent Selection
### Description
Because the simplified JSON structure lacks explicit Parent Material parameters, `ue_import.py` assigns base parent materials based on string matching on the material instance name:
```python
if "eye" in lower_name or "mouth" in lower_name:
    parent_path = "...MI_PalLit_CharacterEyeBase"
```
### Debt / Risk
* **Naming Collisions:** If a modder creates a body texture named `MI_HawkBird_EyeCatchingBody.json`, the script will misidentify `"eye"` in the name and incorrectly assign it the `CharacterEyeBase` parent instead of `CharacterBodyBase`.
* **Structural Maintenance:** If the game developers change the master materials or add new shading models, these string rules must be manually refactored.

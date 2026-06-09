# API & Configuration Formats

## 1. State Tracking (`.palbaker_state.json`)
Generated inside the FModel output directory for a specific mod after a successful Push operation. Used to detect manual modifications.
```json
{
    "last_ue_mtime": 1716750000.0,
    "last_source_mtime": 1716740000.0
}
```

## 2. CLI Arguments (`build_mod.py`)
`python build_mod.py <MONSTER_NAME> <CATEGORY> <ACTION>`
* **MONSTER_NAME:** The internal name of the monster (e.g., `WeaselDragon`).
* **CATEGORY:** The subdirectory type (`Monster` or `Pending Monster`).
* **ACTION:** 
    * `push`: Runs Blender export and Unreal import only.
    * `cook`: Modifies `DefaultGame.ini`, runs Unreal Cooker, and packs the file.
    * `full`: Executes both `push` and `cook`.

## 3. Import Configuration (`import_config.json`)
Generated temporarily by `build_mod.py` to pass data to `ue_import.py` inside the Unreal Engine environment.
```json
{
    "ue_target_path": "/Game/Pal/Model/Character/Monster/WeaselDragon",
    "textures": [
        "C:\\Path\\To\\T_WeaselDragon_Body_B.png"
    ],
    "fbx_file": "C:\\Path\\To\\WeaselDragon.fbx",
    "mi_jsons": [
        "C:\\Path\\To\\MI_WeaselDragon_Body.json"
    ]
}
```
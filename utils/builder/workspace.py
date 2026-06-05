# utils/builder/workspace.py
import os
import json

def get_virtual_path_for_file(absolute_path: str) -> str:
    """
    Robust relative-path calculator. Traverses the directory tree structurally 
    to prevent string-split collisions if a user names their root folder "Pal/Content".
    """
    clean_path = absolute_path.replace("\\", "/")
    parts = clean_path.split("/")
    
    target_idx = -1
    for i in range(len(parts) - 2):
        if parts[i].lower() == "exports" and parts[i+1].lower() == "pal" and parts[i+2].lower() == "content":
            target_idx = i + 2
            break
            
    if target_idx == -1:
        for i in range(len(parts) - 1, -1, -1):
            if parts[i].lower() == "content":
                target_idx = i
                break

    if target_idx != -1 and target_idx + 1 < len(parts):
        relative_part = "/".join(parts[target_idx+1:])
        folder_part = "/".join(relative_part.split("/")[:-1]).replace(" ", "_")
        return f"/Game/{folder_part}"
        
    return ""

class ModWorkspace:
    def __init__(self, monster_name: str, category: str, settings: dict):
        self.monster_name = monster_name
        self.category = category
        self.settings = settings

        # Settings Roots
        self.fmodel_root = settings.get("fmodel_output", "")
        self.ue_root = settings.get("ue_root", "")
        self.uproject_path = settings.get("uproject", "")
        self.blender_path = settings.get("blender", "blender")
        self.palworld_exe = settings.get("palworld_exe", "")

        # Project metadata
        self.project_dir = os.path.dirname(self.uproject_path) if self.uproject_path else ""
        self.target_project_name = os.path.splitext(os.path.basename(self.uproject_path))[0] if self.uproject_path else ""

        # External Tool Paths
        self.ue_cmd_path = os.path.join(self.ue_root, "Engine", "Binaries", "Win64", "UnrealEditor-Cmd.exe") if self.ue_root else ""
        self.unrealpak_path = os.path.join(self.ue_root, "Engine", "Binaries", "Win64", "UnrealPak.exe") if self.ue_root else ""

        # Staging Source Directories
        self.fmodel_dir = os.path.join(self.fmodel_root, "Exports", "Pal", "Content", "Pal", "Model", "Character", category, monster_name) if self.fmodel_root else ""
        self.fmodel_altermatic_dir = os.path.join(self.fmodel_root, "Exports", "Pal", "Content", "Palbaker", "Model", "Character", category, monster_name) if self.fmodel_root else ""
        
        # --- Persistent Switch Integration ---
        is_altermatic_active = False
        base_type = "vanilla"
        manifest_path = os.path.join(self.fmodel_altermatic_dir if self.fmodel_altermatic_dir else self.fmodel_dir, f"{monster_name}_altermatic.json")
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    is_altermatic_active = bool(data.get("is_altermatic_active", False))
                    
                    variants = data.get("variants", [])
                    if isinstance(variants, dict):
                        base_block = variants.get("base", {})
                    else:
                        base_block = next((v for v in variants if v.get("is_base")), {})
                    
                    base_skeleton = base_block.get("SkeletonSource", "base")
                    base_type = "custom" if base_skeleton != "base" else "vanilla"
            except Exception:
                pass
        self.is_altermatic_active = is_altermatic_active
        self.base_type = base_type

        # Standalone Custom Pal detection
        creator_json = os.path.join(self.fmodel_root, "Exports", "Pal", "Content", "Palbaker", "Creator", f"{monster_name}_creator.json") if self.fmodel_root else ""
        self.is_custom_pal = os.path.exists(creator_json)

        # FIXED: Look strictly inside the Pal's local directory for custom mod icons
        self.icon_fmodel_path = os.path.normpath(os.path.join(self.fmodel_dir, f"T_{monster_name}_icon_normal.png")) if self.fmodel_dir else ""
        self.has_icon = os.path.exists(self.icon_fmodel_path) if self.icon_fmodel_path else False

        # Dumb/Resolved Virtual Paths
        category_sanitized = category.replace(" ", "_")
        self.ue_virtual_path = f"/Game/Pal/Model/Character/{category_sanitized}/{monster_name}"
        self.ue_altermatic_virtual_path = f"/Game/Palbaker/Model/Character/{category_sanitized}/{monster_name}"
        
        self.skeleton_virtual_path = f"/Game/Pal/Model/Character/Skeleton/{monster_name}"
        self.anims_virtual_path = f"/Game/Pal/Animation/Character/Monster/{monster_name}"
        
        # --- DETERMINISTIC PARENT TEMPLATE RESOLUTION ---
        template_id = "WeaselDragon"  # Default fallback
        if os.path.exists(creator_json):
            try:
                with open(creator_json, "r", encoding="utf-8") as f:
                    c_data = json.load(f)
                    template_id = c_data.get("TemplateID", "WeaselDragon")
            except Exception:
                pass
        else:
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        variants = data.get("variants", {})
                        if isinstance(variants, dict):
                            base_block = variants.get("base", {})
                        else:
                            base_block = next((v for v in variants if v.get("is_base")), {})
                        template_id = base_block.get("TemplateID", "WeaselDragon")
                except Exception:
                    pass

        self.template_id = template_id  # <-- Expose the parent template ID here

        # Determine the exact padded folder name based on parent template ID length
        parent_len = len(template_id)
        custom_folder_name = monster_name[:parent_len].ljust(parent_len, "_")
        
        # Verify if this standalone blueprint was pre-cooked and injected into the Saved/Cooked directory
        cooked_bp_path = os.path.join(self.project_dir, "Saved", "Cooked", "Windows", self.target_project_name, "Content", "Pal", "Blueprint", "Character", "Monster", "PalActorBP", custom_folder_name)
        
        if os.path.exists(cooked_bp_path):
            self.blueprint_virtual_path = f"/Game/Pal/Blueprint/Character/Monster/PalActorBP/{custom_folder_name}"
        else:
            self.blueprint_virtual_path = f"/Game/Pal/Blueprint/Character/Monster/PalActorBP/{monster_name}"
            
        self.icon_virtual_path = "/Game/Pal/Texture/PalIcon/Normal"

        # Configuration Backups
        self.config_dir = os.path.join(self.project_dir, "Config") if self.project_dir else ""
        self.ini_path = os.path.join(self.config_dir, "DefaultGame.ini") if self.config_dir else ""
        self.ini_backup = os.path.join(self.config_dir, "DefaultGame.ini.palbaker.bak") if self.config_dir else ""

        # Cooked Output Folders
        self.cooked_dir = os.path.join(self.project_dir, "Saved", "Cooked", "Windows", self.target_project_name, "Content", self.ue_virtual_path.replace("/Game/", "").replace("/", os.sep)) if self.project_dir else ""
        self.cooked_altermatic_dir = os.path.join(self.project_dir, "Saved", "Cooked", "Windows", self.target_project_name, "Content", self.ue_altermatic_virtual_path.replace("/Game/", "").replace("/", os.sep)) if self.project_dir else ""
        self.cooked_skel_dir = os.path.join(self.project_dir, "Saved", "Cooked", "Windows", self.target_project_name, "Content", self.skeleton_virtual_path.replace("/Game/", "").replace("/", os.sep)) if self.project_dir else ""
        self.cooked_anims_dir = os.path.join(self.project_dir, "Saved", "Cooked", "Windows", self.target_project_name, "Content", self.anims_virtual_path.replace("/Game/", "").replace("/", os.sep)) if self.project_dir else ""
        self.cooked_bp_dir = os.path.join(self.project_dir, "Saved", "Cooked", "Windows", self.target_project_name, "Content", self.blueprint_virtual_path.replace("/Game/", "").replace("/", os.sep)) if self.project_dir else ""
        
        # Custom ModKit Staging Checks
        self.anims_source_dir = os.path.join(self.project_dir, "Content", "Pal", "Animation", "Character", "Monster", monster_name) if self.project_dir else ""
        self.has_anims = os.path.exists(self.anims_source_dir) if self.anims_source_dir else False

        self.custom_shader_raw = os.path.join(self.project_dir, "Content", "CartoonCelShader", "Materials", "CelShader") if self.project_dir else ""
        self.has_custom_shader = os.path.exists(self.custom_shader_raw) if self.custom_shader_raw else False

        # Output PAK Directories
        self.output_dir = self.fmodel_dir if os.path.exists(self.fmodel_dir) else self.project_dir
        if self.palworld_exe and os.path.exists(self.palworld_exe):
            self.output_dir = os.path.join(os.path.dirname(self.palworld_exe), "Pal", "Content", "Paks", "palBaker")

        self.output_pak_clean = os.path.join(self.output_dir, f"{monster_name}_P.pak")
        self.output_pak_err = os.path.join(self.output_dir, f"{monster_name}_err_P.pak")

        # Compiled Audio Media Directories
        self.audio_media_dir = os.path.join(self.fmodel_dir, ".palbaker_audio", "WwiseAudio", "Media") if self.fmodel_dir else ""
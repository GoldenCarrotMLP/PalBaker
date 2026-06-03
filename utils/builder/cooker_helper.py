# utils/builder/cooker_helper.py
import os
import sys
import shutil
import subprocess
from utils.audio_helper import get_staged_audio_overrides

def run_and_stream(cmd_args) -> bool:
    """
    Executes a command, streams output in real-time, and returns True 
    if 'Warning:' or 'Error:' was printed in stdout, False otherwise.
    """
    process = subprocess.Popen(
        cmd_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
        bufsize=1  # Line-buffered
    )
    
    had_issues = False
    if process.stdout:
        for line in iter(process.stdout.readline, ''):
            if not line:
                break
            stripped = line.strip()
            print(stripped, flush=True) 
            
            # Scan for issues
            line_lower = stripped.lower()
            if "error:" in line_lower:
                had_issues = True
            
    process.wait()
    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, cmd_args)
        
    return had_issues


def clean_cook_environment(workspace):
    """Wipes existing cooked folders and target PAK files to prepare for a clean compile run."""
    for p in [workspace.output_pak_clean, workspace.output_pak_err]:
        if os.path.exists(p):
            try:
                os.remove(p)
                print(f"Cleaned old target pak: {os.path.basename(p)}", flush=True)
            except OSError:
                print(f"CRITICAL ERROR: Cannot overwrite '{os.path.basename(p)}'. Close the game!", flush=True)
                sys.exit(1)

    # Clean cooked folders (including Altermatic variants)
    if os.path.exists(workspace.cooked_dir): 
        shutil.rmtree(workspace.cooked_dir, ignore_errors=True)
    if os.path.exists(workspace.cooked_altermatic_dir): 
        shutil.rmtree(workspace.cooked_altermatic_dir, ignore_errors=True)
    if os.path.exists(workspace.cooked_skel_dir): 
        shutil.rmtree(workspace.cooked_skel_dir, ignore_errors=True)
    if os.path.exists(workspace.cooked_anims_dir): 
        shutil.rmtree(workspace.cooked_anims_dir, ignore_errors=True)
    if os.path.exists(workspace.cooked_bp_dir): 
        shutil.rmtree(workspace.cooked_bp_dir, ignore_errors=True)


def resolve_packaging_manifest(workspace, has_anims: bool) -> list[tuple[str, str]]:
    """Compiles the absolute file sources and virtual destination paths to pass to UnrealPak."""
    folders_to_pack = [
        (workspace.cooked_dir, workspace.ue_virtual_path.replace("/Game/", "")),
        (workspace.cooked_skel_dir, workspace.skeleton_virtual_path.replace("/Game/", ""))
    ]

    # Package Altermatic cooked directories strictly if the framework switch is toggled ON
    if workspace.is_altermatic_active and os.path.exists(workspace.cooked_altermatic_dir):
        folders_to_pack.append((workspace.cooked_altermatic_dir, workspace.ue_altermatic_virtual_path.replace("/Game/", "")))
        print("  -> Altermatic variants detected: Packing custom variant meshes.", flush=True)

    if hasattr(workspace, 'cooked_bp_dir') and os.path.exists(workspace.cooked_bp_dir):
        bp_cooked_base = os.path.join(workspace.cooked_bp_dir, f"BP_{workspace.monster_name}")
        bp_parts_found = False
        for ext in [".uasset", ".uexp", ".ubulk"]:
            cooked_file = bp_cooked_base + ext
            if os.path.exists(cooked_file):
                virtual_file = f"Pal/Blueprint/Character/Monster/PalActorBP/{workspace.monster_name}/BP_{workspace.monster_name}{ext}"
                folders_to_pack.append((cooked_file, virtual_file))
                bp_parts_found = True
        if bp_parts_found:
            print(f"  -> Custom Blueprint detected: Packing only BP_{workspace.monster_name} Blueprint files.", flush=True)

    if has_anims:
        folders_to_pack.append((workspace.cooked_anims_dir, workspace.anims_virtual_path.replace("/Game/", "")))
        print("  -> Custom animations detected: Shipping complete Skeleton, Animation, and BP assets.", flush=True)
    else:
        print("  -> No custom animations: Shipping BP assets, but stripping Skeleton asset to prevent ragdoll glitches.", flush=True)

    if workspace.has_custom_shader:
        custom_shader_cooked = os.path.join(workspace.project_dir, "Saved", "Cooked", "Windows", workspace.target_project_name, "Content", "CartoonCelShader", "Materials", "CelShader")
        folders_to_pack.append((custom_shader_cooked, "CartoonCelShader/Materials/CelShader"))
        print("  -> Custom Cartoon Cel Shader detected: Packing shader dependencies.", flush=True)

    if workspace.has_icon:
        icon_cooked_base = os.path.join(workspace.project_dir, "Saved", "Cooked", "Windows", workspace.target_project_name, "Content", "Pal", "Texture", "PalIcon", "Normal", f"T_{workspace.monster_name}_icon_normal")
        icon_parts_found = False
        for ext in [".uasset", ".uexp", ".ubulk"]:
            cooked_file = icon_cooked_base + ext
            if os.path.exists(cooked_file):
                virtual_file = f"Pal/Texture/PalIcon/Normal/T_{workspace.monster_name}_icon_normal{ext}"
                folders_to_pack.append((cooked_file, virtual_file))
                icon_parts_found = True
        if icon_parts_found:
            print(f"  -> Custom Icon detected: Packing only {workspace.monster_name} icon files.", flush=True)

    # Gather WEM overrides staged on the fly
    audio_overrides = get_staged_audio_overrides(workspace)
    if audio_overrides:
        folders_to_pack.extend(audio_overrides)
        for abs_wem, _ in audio_overrides:
            print(f"  -> Packed custom audio override: {os.path.basename(abs_wem)}", flush=True)

    return folders_to_pack


def pack_cooked_assets(unrealpak_path: str, response_file: str, output_pak: str, folders_to_pack: list, has_anims: bool) -> int:
    """
    Creates the response file for UnrealPak and executes the packaging.
    Supports both Directory-level and File-level packaging paths.
    """
    os.makedirs(os.path.dirname(response_file), exist_ok=True)

    files_found = 0
    with open(response_file, "w") as f:
        for path_on_disk, relative_virtual_path in folders_to_pack:
            if os.path.exists(path_on_disk):
                # Case A: Directory-level packaging (Standard recursive walk)
                if os.path.isdir(path_on_disk):
                    for root, _, files in os.walk(path_on_disk):
                        for file in files:
                            if file.endswith((".uasset", ".uexp", ".ubulk")):
                                # Exclude PhysicsAsset always
                                if "PhysicsAsset" in file:
                                    continue
                                # Exclude Skeleton if no custom animations are shipped
                                if "Skeleton" in file and not has_anims:
                                    continue
                                    
                                abs_path = os.path.join(root, file)
                                rel_to_cooked = os.path.relpath(abs_path, path_on_disk)
                                rel_virtual = "../../../Pal/Content/" + relative_virtual_path + "/" + rel_to_cooked.replace("\\", "/")
                                f.write(f'"{abs_path}" "{rel_virtual}"\n')
                                files_found += 1
                # Case B: File-level packaging (Single explicit asset)
                else:
                    rel_virtual = "../../../Pal/Content/" + relative_virtual_path.replace("\\", "/")
                    f.write(f'"{path_on_disk}" "{rel_virtual}"\n')
                    files_found += 1
                            
    if files_found > 0:
        run_and_stream([unrealpak_path, output_pak, f"-Create={response_file}"])
        
    return files_found
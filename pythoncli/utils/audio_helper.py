# utils/audio_helper.py
import os
import json
import shutil
import subprocess
import sys
from utils.extractor import extract_single_file

SOUND_MAP_FILE = "resolved_sound_map.json"
_sound_map_cache = {}

def apply_custom_audio_worker(settings: dict, mod_data: dict, cry_name: str, src_path: str) -> tuple[bool, str]:
    try:
        fmodel_path = mod_data.get("fmodel_path")
        if not fmodel_path: return False, "No FModel path found."
        
        audio_dir = os.path.join(fmodel_path, ".palbaker_audio")
        sources_dir = os.path.join(audio_dir, "sources")
        wem_dir = os.path.join(audio_dir, "WwiseAudio", "Media")
        
        os.makedirs(sources_dir, exist_ok=True)
        os.makedirs(wem_dir, exist_ok=True)
        
        ext = os.path.splitext(src_path)[1].lower()
        for clean_ext in [".wav", ".mp3", ".ogg"]:
            old_file = os.path.join(sources_dir, f"{cry_name}{clean_ext}")
            if os.path.exists(old_file):
                try: os.remove(old_file)
                except OSError: pass
        
        dest_path = os.path.join(sources_dir, f"{cry_name}{ext}")
        shutil.copy2(src_path, dest_path)
        
        sound_meta = mod_data.get("sound_metadata", {}).get(cry_name, {})
        media_id = sound_meta.get("media_id")
        if not media_id:
            return False, f"No media_id found for {cry_name}"
            
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidate_paths = [
            os.path.join(repo_root, "deps", "wwise", "Authoring", "x64", "Release", "bin", "WwiseConsole.exe"),
            os.path.join(repo_root, "deps", "wwise", "bin", "WwiseConsole.exe")
        ]
        wwise_console = next((p for p in candidate_paths if os.path.exists(p)), None)
        
        project_dir = os.path.join(repo_root, "deps", "wwise", "project")
        wproj_path = None
        if os.path.exists(project_dir):
            for root, _, files in os.walk(project_dir):
                for f in files:
                    if f.endswith(".wproj"):
                        wproj_path = os.path.join(root, f)
                        break
                if wproj_path: break
        
        if not wwise_console or not wproj_path:
            return False, "Wwise environment not found in deps/wwise/. Cannot compile."
            
        wwise_target_file = dest_path
        vgmstream_cli = os.path.join(repo_root, "deps", "vgmstream", "vgmstream-cli.exe")
        if not os.path.exists(vgmstream_cli):
            vgmstream_cli = os.path.join(repo_root, "deps", "vgmstream-cli.exe")
            
        if ext in [".mp3", ".ogg"]:
            temp_wav_path = os.path.join(sources_dir, f"{cry_name}_temp.wav")
            if os.path.exists(temp_wav_path):
                try: os.remove(temp_wav_path)
                except OSError: pass
                
            if os.path.exists(vgmstream_cli):
                decode_cmd = [vgmstream_cli, "-o", temp_wav_path, dest_path]
                creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                subprocess.run(decode_cmd, capture_output=True, creationflags=creation_flags)
                
                if os.path.exists(temp_wav_path):
                    wwise_target_file = temp_wav_path
                else:
                    return False, f"Failed to decode {ext.upper()} to WAV for Wwise compilation."
            else:
                return False, "vgmstream-cli not found. Cannot decode MP3/OGG for Wwise."

        wsources_path = os.path.join(audio_dir, f"{cry_name}_list.wsources")
        output_test_dir = os.path.join(audio_dir, "output_test")
        
        if os.path.exists(output_test_dir):
            shutil.rmtree(output_test_dir, ignore_errors=True)
        os.makedirs(output_test_dir, exist_ok=True)
        
        xml_content = f'<?xml version="1.0" encoding="utf-8"?>\n<ExternalSourcesList SchemaVersion="1">\n    <Source Path="{wwise_target_file.replace(os.sep, "/")}" Conversion="Default Conversion Settings" />\n</ExternalSourcesList>'
        with open(wsources_path, "w", encoding="utf-8") as f:
            f.write(xml_content)
            
        cmd = [
            wwise_console,
            "convert-external-source", wproj_path,
            "--source-file", wsources_path,
            "--output", output_test_dir,
            "--platform", "Windows"
        ]
        
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        wwise_res = subprocess.run(cmd, capture_output=True, creationflags=creation_flags)
        
        compiled_dir = os.path.join(output_test_dir, "Windows")
        success_file = False
        
        if os.path.exists(compiled_dir):
            files = [f for f in os.listdir(compiled_dir) if f.endswith(".wem")]
            if files:
                source_wem = os.path.join(compiled_dir, files[0])
                target_wem = os.path.join(wem_dir, f"{media_id}.wem")
                shutil.copy2(source_wem, target_wem)
                success_file = True
                
        shutil.rmtree(output_test_dir, ignore_errors=True)
        try: os.remove(wsources_path)
        except OSError: pass
        
        if wwise_target_file != dest_path and os.path.exists(wwise_target_file):
            try: os.remove(wwise_target_file)
            except OSError: pass
        
        if success_file:
            return True, f"SUCCESS: Converted and staged {cry_name} -> {media_id}.wem"
        else:
            return False, f"ERROR: Wwise failed to generate .wem for {cry_name}. The file may be corrupted."

    except Exception as e:
        return False, f"Exception during audio processing: {e}"

def clear_audio_worker(mod_data: dict, cry_name: str) -> bool:
    fmodel_path = mod_data.get("fmodel_path")
    if not fmodel_path: return False
    
    audio_dir = os.path.join(fmodel_path, ".palbaker_audio")
    sources_dir = os.path.join(audio_dir, "sources")
    wem_dir = os.path.join(audio_dir, "WwiseAudio", "Media")
    removed = False
    
    if os.path.exists(sources_dir):
        for ext in [".wav", ".mp3", ".ogg"]:
            path = os.path.join(sources_dir, f"{cry_name}{ext}")
            if os.path.exists(path):
                try:
                    os.remove(path)
                    removed = True
                except Exception:
                    pass
    
    media_id = mod_data.get("sound_metadata", {}).get(cry_name, {}).get("media_id")
    if media_id and os.path.exists(wem_dir):
        wem_path = os.path.join(wem_dir, f"{media_id}.wem")
        if os.path.exists(wem_path):
            try:
                os.remove(wem_path)
                removed = True
            except Exception:
                pass
                
    return removed

# utils/audio_helper.py (Append to the end of the file)
def get_staged_audio_overrides(workspace) -> list[tuple[str, str]]:
    """Returns the list of absolute staged WEM source paths and their target virtual paths."""
    overrides = []
    if workspace.audio_media_dir and os.path.exists(workspace.audio_media_dir):
        for wem_file in os.listdir(workspace.audio_media_dir):
            if wem_file.endswith(".wem"):
                abs_wem = os.path.join(workspace.audio_media_dir, wem_file)
                virtual_wem = f"WwiseAudio/Media/{wem_file}"
                overrides.append((abs_wem, virtual_wem))
    return overrides

def load_sound_map() -> dict:
    """Loads and caches the resolved sound mapping structure."""
    global _sound_map_cache
    if _sound_map_cache:
        return _sound_map_cache
    
    # Locate resolved_sound_map.json in the repository root directory
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    map_path = os.path.join(repo_root, SOUND_MAP_FILE)
    
    if not os.path.exists(map_path):
        return {}
        
    try:
        with open(map_path, "r", encoding="utf-8") as f:
            _sound_map_cache = json.load(f)
    except Exception as e:
        print(f"Error loading sound map: {e}")
        _sound_map_cache = {}
        
    return _sound_map_cache

def get_pal_sound_metadata(internal_name: str) -> dict:
    """
    Returns the mapped sounds dictionary for a specific Pal, 
    or an empty dict if the Pal does not have mapped cries.
    """
    sound_map = load_sound_map()
    return sound_map.get(internal_name, {})
# controllers/audio_controller.py
import os
import sys
import shutil
import subprocess
import flet as ft

class AudioController:
    def __init__(self, master_controller):
        self.mc = master_controller
        self.settings = master_controller.settings
        self.view = master_controller.view

    async def apply_custom_audio(self, mod_data: dict, cry_name: str, src_path: str):
        """Stands up an isolated thread to convert audio to .wem instantly upon file upload."""
        def conversion_worker():
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
                
                # Copy source to local FModel staging directory
                dest_path = os.path.join(sources_dir, f"{cry_name}{ext}")
                shutil.copy2(src_path, dest_path)
                
                # Discover Media ID target from internal DB
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
                    
                # WWISE BYPASS: Convert MP3/OGG to a temporary WAV before feeding Wwise
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
                
                # Write XML source mapping
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
                subprocess.run(cmd, capture_output=True, creationflags=creation_flags)
                
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
                
                # Cleanup the temp WAV if we generated one
                if wwise_target_file != dest_path and os.path.exists(wwise_target_file):
                    try: os.remove(wwise_target_file)
                    except OSError: pass
                
                if success_file:
                    return True, f"SUCCESS: Converted and staged {cry_name} -> {media_id}.wem"
                else:
                    return False, f"ERROR: Wwise failed to generate .wem for {cry_name}. The file may be corrupted."

            except Exception as e:
                return False, f"Exception during audio processing: {e}"
                
        self.view.write_log(f"Staging and compiling {cry_name}...", "standard")
        success, msg = await self.mc.run_async_task_threadsafe(conversion_worker)
        if success:
            self.view.write_log(msg, "success")
        else:
            self.view.write_log(msg, "error")
            
        self.mc.refresh_mods(scan_disk=True)

    def play_wav_file(self, wav_path: str):
        if not os.path.exists(wav_path):
            return

        if sys.platform == "win32":
            import winsound
            try:
                winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception as e:
                self.view.write_log(f"Windows Playback Error: {e}", "error")
        elif sys.platform == "darwin":
            subprocess.Popen(["afplay", wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            for player in ["paplay", "aplay", "play"]:
                if shutil.which(player):
                    subprocess.Popen([player, wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    break

    async def play_audio(self, mod_data: dict, cry_name: str):
        fmodel_path = mod_data.get("fmodel_path")
        if not fmodel_path: return

        audio_dir = os.path.join(fmodel_path, ".palbaker_audio", "sources")
        
        custom_file = None
        for ext in [".wav", ".mp3", ".ogg"]:
            test_file = os.path.join(audio_dir, f"{cry_name}{ext}")
            if os.path.exists(test_file):
                custom_file = test_file
                break

        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        vgmstream_cli = os.path.join(repo_root, "deps", "vgmstream", "vgmstream-cli.exe")
        if not os.path.exists(vgmstream_cli):
            vgmstream_cli = os.path.join(repo_root, "deps", "vgmstream-cli.exe")

        if custom_file:
            ext = os.path.splitext(custom_file)[1].lower()
            if ext == ".wav":
                self.play_wav_file(custom_file)
                self.view.write_log(f"Playing custom override for {mod_data['name']}: {cry_name}", "standard")
            else:
                temp_custom_wav = os.path.join(audio_dir, ".temp_custom_preview.wav")
                if not os.path.exists(vgmstream_cli):
                    self.view.write_log("Could not locate 'vgmstream-cli.exe' to decode custom MP3/OGG preview.", "error")
                    return
                
                self.view.write_log(f"Decoding custom {ext[1:].upper()} override for playback...", "standard")
                
                def decode_custom():
                    try:
                        if os.path.exists(temp_custom_wav):
                            try: os.remove(temp_custom_wav)
                            except OSError: pass
                        cmd = [vgmstream_cli, "-o", temp_custom_wav, custom_file]
                        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creation_flags)
                        if os.path.exists(temp_custom_wav):
                            self.play_wav_file(temp_custom_wav)
                    except Exception as e:
                        self.view.write_log(f"Failed to decode custom override: {e}", "error")
                
                self.mc.view.run_in_thread(decode_custom)
            return

        sound_meta = mod_data.get("sound_metadata", {})
        cry_meta = sound_meta.get(cry_name)
        if not cry_meta:
            self.view.write_log(f"No sound metadata found for {cry_name}", "warning")
            return

        wem_rel = cry_meta.get("wem_relative_path")
        if not wem_rel: return

        fmodel_root = self.settings.get("fmodel_output", "")
        if not fmodel_root: return

        wem_abs_path = os.path.normpath(os.path.join(fmodel_root, "Exports", wem_rel))
        if not os.path.exists(wem_abs_path):
            self.view.write_log(f"Original game .wem asset not found inside FModel output: {os.path.basename(wem_abs_path)}", "error")
            return

        if not os.path.exists(vgmstream_cli):
            self.view.write_log("Could not locate 'vgmstream-cli.exe' inside 'deps/vgmstream/'. Preview unavailable.", "error")
            return

        os.makedirs(audio_dir, exist_ok=True)
        temp_wav = os.path.join(audio_dir, ".temp_preview.wav")

        self.view.write_log(f"Decoding original game audio for {mod_data['name']} ({cry_name})...", "standard")

        def decode_worker():
            try:
                if os.path.exists(temp_wav):
                    try: os.remove(temp_wav)
                    except OSError: pass

                cmd = [vgmstream_cli, "-o", temp_wav, wem_abs_path]
                creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creation_flags)
                
                if os.path.exists(temp_wav):
                    self.play_wav_file(temp_wav)
                else:
                    self.view.write_log("vgmstream executed but failed to save temporary preview wav.", "error")
            except Exception as e:
                self.view.write_log(f"vgmstream decoding failed: {e}", "error")

        self.mc.view.run_in_thread(decode_worker)

    # FIXED: Reconfigured clear_audio to be an asynchronous method to prevent runtime await TypeErrors in the controller.
    async def clear_audio(self, mod_data: dict, cry_name: str):
        fmodel_path = mod_data.get("fmodel_path")
        if not fmodel_path: return

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
                    except Exception as e:
                        self.view.write_log(f"ERROR: Failed to delete audio source: {e}", "error")
        
        media_id = mod_data.get("sound_metadata", {}).get(cry_name, {}).get("media_id")
        if media_id and os.path.exists(wem_dir):
            wem_path = os.path.join(wem_dir, f"{media_id}.wem")
            if os.path.exists(wem_path):
                try:
                    os.remove(wem_path)
                    removed = True
                except OSError: pass
                
        if removed:
            self.view.write_log(f"REVERTED: Removed custom override for {mod_data['name']} ({cry_name})", "standard")
            self.mc.refresh_mods(scan_disk=True)
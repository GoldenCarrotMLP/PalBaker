# controllers/audio_controller.py
import os
import sys
import shutil
import subprocess
from utils.audio_helper import apply_custom_audio_worker, clear_audio_worker

class AudioController:
    def __init__(self, master_controller):
        self.mc = master_controller
        self.settings = master_controller.settings
        self.view = master_controller.view

    async def apply_custom_audio(self, mod_data: dict, cry_name: str, src_path: str):
        self.view.write_log(f"Staging and compiling {cry_name}...", "standard")
        success, msg = await self.mc.run_async_task_threadsafe(
            lambda: apply_custom_audio_worker(self.settings, mod_data, cry_name, src_path)
        )
        if success:
            self.view.write_log(msg, "success")
        else:
            self.view.write_log(msg, "error")
            
        self.mc.refresh_mods(scan_disk=True, target_mod=mod_data["name"])

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
        # We can still keep the preview play logic here or move parts to helper if needed. Since play_audio uses active UI / logging elements directly, it can live here.
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

        if not os.path.exists(vgmstream_cli):
            self.view.write_log("Could not locate 'vgmstream-cli.exe' inside 'deps/vgmstream/'. Preview unavailable.", "error")
            return

        os.makedirs(audio_dir, exist_ok=True)
        temp_wav = os.path.join(audio_dir, ".temp_preview.wav")

        def decode_worker():
            try:
                from utils.extractor import extract_single_file
                if not os.path.exists(wem_abs_path):
                    self.view.write_log(f"Original game .wem asset missing. Extracting dynamically from Paks...", "stage")
                    export_root = os.path.join(fmodel_root, "Exports")
                    
                    success = extract_single_file(self.settings, wem_rel, export_root)
                    if not success or not os.path.exists(wem_abs_path):
                        self.view.write_log(f"Extraction helper failed to extract {wem_rel}.", "error")
                        return
                    else:
                        self.view.write_log(f"Successfully extracted: {wem_rel}", "success")

                self.view.write_log(f"Decoding original game audio for {mod_data['name']} ({cry_name})...", "standard")

                if os.path.exists(temp_wav):
                    try: os.remove(temp_wav)
                    except OSError: pass

                cmd_decode = [vgmstream_cli, "-o", temp_wav, wem_abs_path]
                creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                subprocess.run(cmd_decode, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creation_flags)
                
                if os.path.exists(temp_wav):
                    self.play_wav_file(temp_wav)
                else:
                    self.view.write_log("vgmstream executed but failed to save temporary preview wav.", "error")
            except Exception as e:
                self.view.write_log(f"Audio extraction or decoding failed: {e}", "error")

        self.mc.view.run_in_thread(decode_worker)

    async def clear_audio(self, mod_data: dict, cry_name: str):
        def executor():
            removed = clear_audio_worker(mod_data, cry_name)
            if removed:
                self.view.write_log(f"REVERTED: Removed custom override for {mod_data['name']} ({cry_name})", "standard")
                self.mc.refresh_mods(scan_disk=True, target_mod=mod_data["name"])

        self.mc.view.run_in_thread(executor)
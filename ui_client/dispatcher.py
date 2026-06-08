import asyncio
import json
import subprocess
import os

class PalBakerCLI:
    def __init__(self, cli_path="python palbaker_cli.py"):
        self.cli_path = cli_path.split(" ")

    async def _execute(self, args: list) -> dict:
        """Executes a standard CLI command and returns the parsed JSON dict."""
        cmd = self.cli_path + args
        
        # CREATE_NO_WINDOW ensures no rogue cmd prompts pop up on Windows
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            creationflags=creationflags
        )
        stdout, stderr = await proc.communicate()
        
        try:
            return json.loads(stdout.decode().strip())
        except json.JSONDecodeError:
            return {"status": "error", "message": f"CLI Error: {stderr.decode()}"}

    async def list_mods(self, show_unextracted=False):
        args = ["manager", "list"]
        if show_unextracted:
            args.append("--show-unextracted")
        return await self._execute(args)

    async def get_config(self):
        args = ["config", "get"]
        return await self._execute(args)

    async def set_config(self, key, value):
        args = ["config", "set", key, value]
        return await self._execute(args)

    async def run_pipeline_stream(self, mod_name: str, action: str, log_cb, progress_cb, done_cb):
        """Yields JSONL output line-by-line for live UI updates."""
        cmd = self.cli_path + ["mod", action, mod_name]
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            creationflags=creationflags
        )
        
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
                
            try:
                payload = json.loads(line.decode().strip())
                if payload["type"] == "log":
                    log_cb(payload["message"], payload.get("level", "standard"))
                elif payload["type"] == "progress":
                    progress_cb(payload["percent"], payload["message"])
            except json.JSONDecodeError:
                pass # Ignore malformed output
                
        await proc.wait()
        done_cb(proc.returncode == 0)

    async def build_database(self):
        """Build the Pal database cache."""
        return await self._execute(["manager", "build-db"])

    async def set_icon(self, mod_name: str, icon_path: str):
        """Set a custom icon for a Pal."""
        return await self._execute(["mod", "set-icon", mod_name, "--path", icon_path])

    async def refresh_actor_blueprint(self, pal_id: str):
        """Refresh Actor Blueprint for a custom Pal."""
        return await self._execute(["creator", "refresh-bp", pal_id])

    async def env_verify(self):
        """Verify workspace setup (MSVC, UBT)."""
        return await self._execute(["env", "verify"])

    async def env_ue4ss_install(self):
        """Install UE4SS."""
        return await self._execute(["env", "ue4ss-install"])

    async def env_install_plugin(self):
        """Install PalSchema Plugin."""
        return await self._execute(["env", "install-plugin"])

    async def creator_list(self):
        """List all custom standalone Pals."""
        return await self._execute(["creator", "list"])

    async def creator_add(self, pal_id: str, template_id: str):
        """Create a new standalone Pal."""
        return await self._execute(["creator", "add", pal_id, "--template", template_id])

    async def creator_delete(self, pal_id: str):
        """Delete a custom standalone Pal."""
        return await self._execute(["creator", "delete", pal_id])

    async def creator_update(self, pal_id: str, data_payload: dict):
        """Update parameters of a custom standalone Pal."""
        import json as json_lib
        data_str = json_lib.dumps(data_payload)
        return await self._execute(["creator", "update", pal_id, "--data", data_str])

    async def altermatic_toggle(self, mod_name: str, status: str):
        """Toggle Altermatic framework on/off (status: 'on' or 'off')."""
        return await self._execute(["altermatic", "toggle", mod_name, status])

    async def altermatic_list(self, mod_name: str):
        """List all Altermatic variants for a mod."""
        return await self._execute(["altermatic", "list", mod_name])

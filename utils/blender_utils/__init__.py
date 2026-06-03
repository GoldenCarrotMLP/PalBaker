# utils/blender_utils/__init__.py
import sys
import os
import types

try:
    import bpy
except ImportError:
    # If imported outside of Blender (e.g., by the PalBaker orchestrator),
    # inject a strictly compliant ModuleType mock into sys.modules.
    mock_bpy = types.ModuleType("bpy")
    mock_bpy.app = type("App", (), {"version": (0, 0, 0)})()
    sys.modules["bpy"] = mock_bpy

import bpy

class BlenderTranslator:
    def __init__(self):
        # Format: { "operation_name": { (major, minor): function } }
        self._registry = {}

    def register(self, op_name: str, version: tuple = (0, 0)):
        """Decorator to register version-specific low-level adapters."""
        def decorator(func):
            if op_name not in self._registry:
                self._registry[op_name] = {}
            self._registry[op_name][version] = func
            return func
        return decorator

    def _resolve_op(self, op_name: str, current_version: tuple) -> callable:
        if op_name not in self._registry:
            raise AttributeError(f"Blender Translator Error: Operation '{op_name}' is not registered.")

        version_map = self._registry[op_name]

        if current_version in version_map:
            return version_map[current_version]

        sorted_versions = sorted(version_map.keys())
        valid_lower_versions = [v for v in sorted_versions if v <= current_version]

        if valid_lower_versions:
            best_version = valid_lower_versions[-1]
        else:
            best_version = (0, 0) if (0, 0) in version_map else sorted_versions[0]

        return version_map[best_version]

    def execute(self, op_name: str, *args, **kwargs):
        """Executes a registered operation safely using the current Blender version context."""
        current_version = bpy.app.version[:2]
        target_func = self._resolve_op(op_name, current_version)
        return target_func(*args, **kwargs)

    def execute_with_version(self, op_name: str, version: tuple, *args, **kwargs):
        """Executes an operation using an explicitly provided version context (for running outside Blender)."""
        target_func = self._resolve_op(op_name, version)
        return target_func(*args, **kwargs)

    # =========================================================================
    # HIGH-LEVEL WRAPPER STUBS (Provides perfect IDE Autocomplete & Type checking)
    # =========================================================================

    def clean_scene(self):
        """Wipes the default startup scene completely."""
        return self.execute("clean_scene")

    def ensure_addon_enabled(self, addon_name: str):
        """Safely registers and activates the target addon or extension package across versions."""
        return self.execute("ensure_addon_enabled", addon_name)

    def get_addon_name(self) -> str:
        """Resolves the standard addon registration and folder name based on active Blender version."""
        return self.execute("get_addon_name")

    def get_addons_list(self) -> str:
        """Resolves the comma-separated list of active addons for command-line execution."""
        return self.execute("get_addons_list")

    # FIXED: Updated signature to accept version_str parameters
    def get_download_url(self, version_str: str = "4.2") -> str:
        """Resolves the release download URL for the target Blender version."""
        return self.execute("get_download_url", version_str)

    def get_target_addon_directory(self, blender_dir: str, version_str: str, appdata: str) -> str:
        """Resolves the directory path on disk where the addon should be extracted."""
        return self.execute("get_target_addon_directory", blender_dir, version_str, appdata)

    def import_mesh(self, file_path: str):
        """Imports a PSK or FBX asset file cleanly into Blender."""
        return self.execute("import_mesh", file_path)

    def save_blend(self, blend_path: str):
        """Saves the current Blender workspace file cleanly to disk."""
        return self.execute("save_blend", blend_path)

    def fix_hierarchy(self, armature_name: str = "Armature"):
        """Unparents loose mesh hierarchies and cleans empty nodes."""
        return self.execute("fix_hierarchy", armature_name)

    def get_pose_bones_info(self, armature_name: str = "Armature") -> list[dict]:
        """
        Gathers transformation, parenting, and custom physics bone properties.
        Serializes results strictly into basic Python structures (dict, list, str, float).
        """
        return self.execute("get_pose_bones_info", armature_name)

    def get_skeletal_mesh_material_slots(self) -> list[str]:
        """Resolves material slots in the exact physical index order of the active mesh."""
        return self.execute("get_skeletal_mesh_material_slots")

    def connect_mix_nodes(self, nodes, links, base_tex_output, blue_channel_output, base_color_socket):
        """Instantiates, configures, and links a version-safe Mix/MixRGB node block dynamically."""
        return self.execute("connect_mix_nodes", nodes, links, base_tex_output, blue_channel_output, base_color_socket)

    def compile_material_instance(self, mat_name: str, parent_class: str, params: dict, working_dir: str):
        """Dynamically builds and connects a Principled BSDF template block."""
        return self.execute("compile_material_instance", mat_name, parent_class, params, working_dir)

    def export_fbx(self, fbx_path: str, armature_name: str = "Armature"):
        """Clears pose bone offsets and headlessly exports the FBX asset."""
        return self.execute("export_fbx", fbx_path, armature_name)

# Expose global translator instance
translator = BlenderTranslator()

# Import the base and patch files to execute decorators and populate the registry
from . import adapters_base
from . import adapters_v3
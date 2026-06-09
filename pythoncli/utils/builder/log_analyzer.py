# utils/builder/log_analyzer.py

import os
import re

class LogAnalyzer:
    def __init__(self):
        self.raw_errors = []
        self.raw_warnings = []
        self.matched_rules = []
        
        # Diagnostic Knowledge Base
        self.rules = [
            {
                "id": "missing_skeleton",
                "keywords": ["Invalid USkeleton supplied", "The skeleton asset for this animation Blueprint is missing"],
                "title": "Broken/Missing Skeleton Reference",
                "solution": "Unreal has dangling references to a deleted or renamed skeleton. Delete any old 'SK_*.uasset' files, delete the stale AnimBlueprints in your Content/Pal/Model/Character/Skeleton/ folder, and run 'Push to Unreal' again."
            },
            {
                "id": "unreal_connection_failed",
                "keywords": ["Unreal Editor is not running", "No response received from Unreal remote execution", "Connection refused"],
                "title": "Unreal Engine Connection Refused",
                "solution": "PalBaker could not establish a connection to Unreal Editor. Ensure your ModKit project is open in Unreal Editor and Python Remote Execution is enabled (Project Settings -> Python)."
            },
            {
                "id": "missing_import_package",
                "keywords": ["VerifyImport: Failed to load package", "Failed to load '/Game/", "Can't find file"],
                "title": "Missing Import Dependency / Stale References",
                "solution": "Your project contains references to deleted assets. Open Unreal Editor, right-click your Content folder, and select 'Fix Up Redirectors in Folder' to repair broken paths."
            },
            {
                "id": "blender_psk_importer_missing",
                "keywords": ["No PSK importer addon/extension is registered", "No module named 'io_scene_psk_psa'", "No module named 'io_import_scene_unreal_psa_psk'"],
                "title": "Blender PSK Addon Missing",
                "solution": "Headless Blender failed to import the .psk file because the PSK Importer addon is not registered. Please install/enable the 'io_scene_psk_psa' extension in your Blender installation."
            },
            {
                "id": "blender_no_armature",
                "keywords": ["No armature found", "ERROR: No armature found"],
                "title": "Blender Rigging Error: Armature Missing",
                "solution": "Blender could not find any Armature inside your .blend file. Ensure your mesh has a valid armature modifier and bone structure named exactly 'Armature'."
            },
            {
                "id": "blender_path_invalid",
                "keywords": ["blender executed but failed to save", "failed to execute Blender process"],
                "title": "Invalid Blender Executable Path",
                "solution": "The Blender Executable Path configured in your Settings is invalid or inaccessible. Navigate to the Settings tab and set it to your actual 'blender.exe' file path."
            }
        ]

    def _extract_assets_from_line(self, line: str) -> list[str]:
        """
        Scans a log line and extracts unique asset names from either Windows 
        absolute paths or Unreal virtual package paths.
        """
        found_assets = []
        
        # Pattern 1: Windows Absolute Paths (.uasset)
        win_match = re.search(r'([a-zA-Z]:\\[^:]+\.uasset)', line)
        if win_match:
            name = os.path.basename(win_match.group(1))
            found_assets.append(name)
            
        # Pattern 2: Unreal Virtual Paths (/Game/...)
        ue_match = re.search(r'(/Game/[^\s:]+)', line)
        if ue_match:
            v_path = ue_match.group(1)
            # Handle dot components like /Game/Path/Asset.Asset
            if "." in v_path:
                v_path = v_path.split(".")[0]
            name = os.path.basename(v_path)
            # Safeguard to prevent capturing directory names as assets
            if name and name != "Content" and name not in found_assets:
                found_assets.append(name)
                
        return found_assets

    def _extract_assets(self, log_lines: list) -> list:
        """Helper to scan raw log lines and pull out unique asset names."""
        assets = []
        for line in log_lines:
            for ast in self._extract_assets_from_line(line):
                if ast not in assets:
                    assets.append(ast)
        return assets

    def analyze_line(self, line: str) -> tuple[str, str, bool]:
        """
        Analyzes a log line, counts errors/warnings, and matches troubleshooting rules.
        """
        line_lower = line.lower()
        is_error = False
        category = "standard"
        
        # Detect and store raw warnings/errors
        if "error:" in line_lower or "critical error" in line_lower or "failed:" in line_lower or "traceback (most recent call last):" in line_lower:
            is_error = True
            category = "error"
            self.raw_errors.append(line)
        elif "warning:" in line_lower:
            category = "warning"
            self.raw_warnings.append(line)
        elif ">>>" in line:
            category = "stage"
        elif "success:" in line_lower:
            category = "success"

        # Scan against diagnostic rules
        for rule in self.rules:
            for kw in rule["keywords"]:
                if kw.lower() in line_lower:
                    matched_rule = next((r for r in self.matched_rules if r["id"] == rule["id"]), None)
                    if not matched_rule:
                        matched_rule = dict(rule)
                        matched_rule["assets"] = []
                        self.matched_rules.append(matched_rule)
                        
                    # Extract any assets present on this matched line
                    for ast in self._extract_assets_from_line(line):
                        if ast not in matched_rule["assets"]:
                            matched_rule["assets"].append(ast)

        return line, category, is_error

    def generate_summary(self, exit_success: bool) -> dict | None:
        """
        Constructs a diagnostic report if errors, warnings, or exit failures are present.
        """
        if not exit_success:
            status = "failed"
        elif len(self.raw_errors) > 0:
            status = "success_with_errors"
        elif len(self.raw_warnings) > 0:
            status = "success_with_warnings"
        else:
            status = "pure_success"

        if status == "pure_success":
            return None

        # Build dynamic fallback advice cards if we caught warnings/errors but no specific rule matched
        dynamic_rules = list(self.matched_rules)
        if not dynamic_rules:
            if self.raw_errors:
                dynamic_rules.append({
                    "title": f"Uncaught Compiler Errors ({len(self.raw_errors)} detected)",
                    "solution": "The process finished, but hard errors were thrown. Check the red log lines inside your Build Console to find the exact asset failing.",
                    "assets": self._extract_assets(self.raw_errors)
                })
            if self.raw_warnings:
                dynamic_rules.append({
                    "title": f"Dangling Asset Warnings ({len(self.raw_warnings)} detected)",
                    "solution": "Unreal failed to load some referenced textures/materials. Verify that all dependencies have been pushed, or right-click your Content folder in Unreal and click 'Fix Up Redirectors' to clean references.",
                    "assets": self._extract_assets(self.raw_warnings)
                })

        return {
            "status": status,
            "matched_rules": dynamic_rules,
            "total_warnings": len(self.raw_warnings),
            "total_errors": len(self.raw_errors)
        }
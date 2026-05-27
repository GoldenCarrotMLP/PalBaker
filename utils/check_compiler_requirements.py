import os
import sys
import re
import json
import shutil

U_CONFIG_XML_TEMPLATE = """<?xml version="1.0" encoding="utf-8" ?>
<Configuration xmlns="https://www.unrealengine.com/BuildConfiguration">
    <WindowsPlatform>
        <Compiler>VisualStudio2022</Compiler>
        <CompilerVersion>{version}</CompilerVersion>
    </WindowsPlatform>
</Configuration>
"""

def get_installed_msvc_versions():
    """Scans standard Visual Studio 2022 paths for installed MSVC toolsets."""
    vs_root = r"C:\Program Files\Microsoft Visual Studio\2022"
    editions = ["Community", "Professional", "Enterprise", "BuildTools"]
    installed = []
    
    for edition in editions:
        msvc_path = os.path.join(vs_root, edition, "VC", "Tools", "MSVC")
        if os.path.exists(msvc_path):
            try:
                for folder in os.listdir(msvc_path):
                    full_path = os.path.join(msvc_path, folder)
                    if os.path.isdir(full_path):
                        installed.append({
                            "edition": edition,
                            "version": folder,
                            "path": full_path,
                            "is_compliant": folder.startswith("14.3")
                        })
            except Exception:
                pass
                
    return installed

def parse_build_config(xml_path):
    """Parses BuildConfiguration.xml safely using regex."""
    if not os.path.exists(xml_path):
        return None
    
    try:
        with open(xml_path, "r", encoding="utf-8-sig") as f:
            content = f.read()
            
        compiler_match = re.search(r"<Compiler>(.*?)</Compiler>", content)
        version_match = re.search(r"<CompilerVersion>(.*?)</CompilerVersion>", content)
        
        return {
            "compiler": compiler_match.group(1).strip() if compiler_match else None,
            "version": version_match.group(1).strip() if version_match else None
        }
    except Exception:
        return None

def ask_user(prompt: str, all_yes: bool = False) -> bool:
    """Helper to handle prompts, skipping if all_yes is set."""
    if all_yes:
        return True
    try:
        response = input(f"{prompt} (y/n): ").strip().lower()
        return response in ["y", "yes"]
    except Exception:
        return False

def verify_compiler_requirements(all_yes: bool = False, print_output: bool = True) -> tuple[bool, str]:
    """
    Main reusable library function. 
    Checks compiler requirements and auto-fixes configuration files if permitted.
    Returns: (bool_success, str_message)
    """
    installed_compilers = get_installed_msvc_versions()
    
    compliant_installed = [comp for comp in installed_compilers if comp["is_compliant"]]
    
    if not installed_compilers:
        msg = "No Visual Studio 2022 installations detected. Please install Visual Studio 2022 Community with C++ development workloads."
        if print_output:
            print(f"  ❌ ERROR: {msg}")
        return False, msg

    # Validate physical compiler installation (cannot be auto-fixed by Python)
    if not compliant_installed:
        msg = "No compliant v143 (14.3x) compiler toolset is installed. Unreal 5.1 requires MSVC 14.3x to build."
        if print_output:
            print(f"  ❌ REQUIREMENT FAILED: {msg}")
            print("\n     ACTION REQUIRED:")
            print("     1. Open Visual Studio Installer.")
            print("     2. Click Modify.")
            print("     3. Under 'Individual Components', check:")
            print("        'MSVC v143 - VS 2022 C++ x64/x86 build tools (v14.38-17.8)'")
            print("     4. Complete the installation.")
        return False, msg

    # Select the highest compliant version installed to write to the config
    best_version = max(comp["version"] for comp in compliant_installed)
    
    appdata = os.environ.get("APPDATA", "")
    if not appdata:
        msg = "Could not locate AppData environment variable."
        if print_output:
            print(f"  ❌ ERROR: {msg}")
        return False, msg
        
    config_dir = os.path.join(appdata, "Unreal Engine", "UnrealBuildTool")
    config_path = os.path.join(config_dir, "BuildConfiguration.xml")
    config_exists = os.path.exists(config_path)

    xml_data = parse_build_config(config_path) if config_exists else None
    
    needs_fix = False
    fix_reason = ""

    # --- XML CONFIGURATION CHECKLIST ---
    if not config_exists:
        needs_fix = True
        fix_reason = "BuildConfiguration.xml does not exist yet."
    elif not xml_data:
        needs_fix = True
        fix_reason = "BuildConfiguration.xml is invalid or could not be parsed."
    elif not xml_data.get("compiler"):
        needs_fix = True
        fix_reason = "BuildConfiguration.xml is missing the <Compiler> element."
    elif xml_data.get("compiler") != "VisualStudio2022":
        needs_fix = True
        # FIXED: Detect and warn about the Visual2022 spelling typo
        fix_reason = f"Configured compiler value is invalid (got '{xml_data['compiler']}', expected 'VisualStudio2022')."
    elif not xml_data.get("version"):
        needs_fix = True
        fix_reason = "BuildConfiguration.xml is missing a <CompilerVersion> target."
    else:
        configured_version = xml_data["version"]
        is_config_compliant = configured_version.startswith("14.3")
        is_config_installed = any(comp["version"] == configured_version for comp in compliant_installed)
        
        if not is_config_compliant:
            needs_fix = True
            fix_reason = f"Configured version ({configured_version}) is not a compliant 14.3x compiler."
        elif not is_config_installed:
            needs_fix = True
            fix_reason = f"Configured version ({configured_version}) is not physically installed."

    if needs_fix:
        if print_output:
            print(f"  ⚠️ ISSUE DETECTED: {fix_reason}")
            
        # Execute Autofix phase
        prompt_msg = f"Would you like to automatically configure BuildConfiguration.xml to use compliant MSVC version {best_version} and set the compiler value to 'VisualStudio2022'?"
        if ask_user(prompt_msg, all_yes):
            try:
                os.makedirs(config_dir, exist_ok=True)
                
                # Backup existing if it exists
                if config_exists:
                    shutil.copy2(config_path, config_path + ".bak")
                    if print_output:
                        print(f"  * Backed up old configuration to {config_path}.bak")
                
                # Write the clean configuration
                with open(config_path, "w", encoding="utf-8") as f:
                    f.write(U_CONFIG_XML_TEMPLATE.format(version=best_version))
                
                msg = f"Successfully generated and configured BuildConfiguration.xml with MSVC version {best_version} and compiler 'VisualStudio2022'."
                if print_output:
                    print(f"  ✅ SUCCESS: {msg}")
                return True, msg
            except Exception as e:
                msg = f"Failed to write BuildConfiguration.xml: {e}"
                if print_output:
                    print(f"  ❌ ERROR: {msg}")
                return False, msg
        else:
            msg = "User declined to auto-fix the compiler configuration."
            return False, msg

    msg = f"Compiler requirements are satisfied. Using MSVC {xml_data['version']}."
    if print_output:
        print(f"  ✅ SUCCESS: {msg}")
    return True, msg

# --- CLI Execution Context ---
if __name__ == "__main__":
    # Check for CLI auto-apply arguments
    all_yes_arg = "-all_yes" in sys.argv
    
    print("=" * 60)
    print("=== PalBaker Unreal Engine Compiler Diagnostics ===")
    print("=" * 60)
    
    success, message = verify_compiler_requirements(all_yes=all_yes_arg, print_output=True)
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 DIAGNOSTIC PASSED:")
        print(f"  {message}")
    else:
        print("❌ DIAGNOSTIC FAILED:")
        print(f"  {message}")
    print("=" * 60)
    
    # Pause so standalone double-click terminal doesn't close immediately
    input("Press Enter to exit...")
    sys.exit(0 if success else 1)
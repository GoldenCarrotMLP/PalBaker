import re
from pathlib import Path

files_to_fix = [
    "components/altermatic/dialogs/add_dialog.py",
    "components/altermatic/dialogs/delete_dialog.py",
    "components/altermatic/dialogs/edit_dialog.py",
    "components/altermatic/dialogs/utils.py",
    "components/altermatic/general_section.py",
    "components/altermatic/materials_section.py",
    "components/altermatic/morphs_section.py",
    "components/altermatic/traits_section.py",
    "components/common/path_picker.py",
    "components/creator/add_dialog.py",
    "components/creator/learnset_editor.py",
    "components/creator/pal_card.py",
    "components/creator/search_selector.py",
    "components/mods/dialogs.py",
    "components/mods/mod_card.py",
    "components/mods/mod_details.py",
    "controllers/mods/pipeline_executor.py",
    "controllers/settings_controller.py",
    "manager-test.py",
    "manager.py",
    "utils/blender_utils/__init__.py",
    "utils/blender_utils/adapters_base.py",
    "utils/blender_utils/adapters_v3.py",
    "utils/image_combiner.py",
    "views/creator_view.py",
    "views/mods_view.py",
    "views/settings_view.py"
]

for file_path in files_to_fix:
    path = Path(file_path)
    if not path.exists(): continue
    lines = path.read_text().split('\n')
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            if any(mod in line for mod in ['flet', 'bpy', 'addon_utils', 'mathutils', 'numpy']):
                if '# type: ignore' not in line:
                    lines[i] = line + '  # type: ignore'
    path.write_text('\n'.join(lines))

exec_path = Path("controllers/mods/pipeline_executor.py")
if exec_path.exists():
    content = exec_path.read_text()
    content = content.replace("proc.kill()", "if proc is not None:\n                            proc.kill()  # type: ignore")
    exec_path.write_text(content)

print("done")

# manager-test.py
import json
import os
import flet as ft  # type: ignore

# --- Bulletproof Version-Safe Dialog Handlers ---
def show_dialog_safe(page: ft.Page, dialog: ft.AlertDialog):
    """Bypasses version conflicts across Flet 0.22, 0.23, 0.85, and 1.0."""
    if hasattr(page, "show_dialog"):
        page.show_dialog(dialog)
    elif hasattr(page, "open"):
        page.open(dialog)  # type: ignore
    else:
        page.dialog = dialog  # type: ignore
        dialog.open = True  # type: ignore
        page.update()

def close_dialog_safe(page: ft.Page, dialog: ft.AlertDialog):
    """Safely closes active modal dialogs on any Flet version."""
    if hasattr(page, "pop_dialog"):
        page.pop_dialog()
    elif hasattr(page, "close"):
        page.close(dialog)  # type: ignore
    else:
        dialog.open = False  # type: ignore
        page.update()


# --- Dynamic Path Resolution Engine ---
def resolve_skel_mesh_path(category: str, character_id: str, source: str) -> str:
    """Dynamically compiles the correct Virtual Path based on Altermatic choices."""
    if source == "base":
        return f"/Game/Pal/Model/Character/{category}/{character_id}/SK_{character_id}"
    else:
        clean_name = os.path.splitext(source)[0]
        sk_name = clean_name if clean_name.startswith("SK_") else f"SK_{clean_name}"
        return f"/Game/PalBaker/Model/Character/{category}/{character_id}/{sk_name}"

def resolve_material_path(category: str, character_id: str, mat_name: str) -> str:
    """Dynamically compiles the Virtual Path for custom material overrides."""
    return f"/Game/PalBaker/Model/Character/{category}/{character_id}/{mat_name}"


# --- Directory/Database Scanners ---
def get_blend_files_for_context(category: str, character_id: str) -> list[str]:
    """Scans the local palbaker/ workspace directory for .blend files, with mock fallbacks."""
    root_dir = os.path.dirname(os.path.abspath(__file__))
    target_dir = os.path.join(root_dir, "palbaker", category, character_id)
    
    blend_files = []
    if os.path.exists(target_dir):
        for f in os.listdir(target_dir):
            if f.endswith(".blend"):
                blend_files.append(f)
                
    if not blend_files:
        blend_files = [
            f"{character_id}_Bikini.blend",
            f"{character_id}_NSFW.blend",
            f"{character_id}_Armor.blend"
        ]
    return blend_files

def get_material_slots_for_mesh(character_id: str, source: str) -> list[str]:
    """Resolves which material slots are active on a mesh."""
    defaults = {
        "WeaselDragon": ["mi_weaseldragon_body", "mi_weaseldragon_eye", "mi_weaseldragon_mouth"],
        "AmaterasuWolf": ["mi_amaterasu_body", "mi_amaterasu_hair"],
        "GrimGirl": ["mi_grimgirl_body", "mi_grimgirl_eye", "mi_grimgirl_weapon"],
        "Cattiva": ["mi_cattiva_body", "mi_cattiva_eye"]
    }
    
    slots = defaults.get(character_id, ["mi_body", "mi_eye"])
    if source != "base":
        clean_source = os.path.splitext(source)[0].replace(character_id, "").strip("_")
        if clean_source:
            slots = [f"{s}_{clean_source.lower()}" for s in slots]
    return slots

def get_available_materials_for_context(character_id: str) -> list[str]:
    """Resolves compiled material assets available inside the ModKit directory."""
    return [
        f"MI_{character_id}_Body_Latex",
        f"MI_{character_id}_Body_Shiny",
        f"MI_{character_id}_Body_Gold",
        f"MI_{character_id}_Body_Carbon"
    ]

def get_morph_targets_for_mesh(category: str, character_id: str, source: str) -> list[str]:
    """Scans for [source]_blend.json next to the blend file, falls back to mock list."""
    root_dir = os.path.dirname(os.path.abspath(__file__))
    clean_source_name = "base" if source == "base" else os.path.splitext(source)[0]
    target_path = os.path.join(root_dir, "palbaker", category, character_id, f"{clean_source_name}_blend.json")
    
    if os.path.exists(target_path):
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
            
    # Symmetrical fallback mock list
    return ["breast_size", "belly_fat", "waist_width", "height_scale"]


# --- Traits Database Loader ---
def load_traits_database() -> dict:
    root_dir = os.path.dirname(os.path.abspath(__file__))
    target_path = os.path.join(root_dir, "traits_db.json")
    
    if not os.path.exists(target_path):
        return {}
    try:
        with open(target_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def main(page: ft.Page):
    page.title = "Palworld Altermatic Mod Builder Sandbox"
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 950
    page.window.height = 780
    page.padding = 20

    # Load traits database from file as the sole source of truth
    traits_db = load_traits_database()

    # Main in-memory variant state
    variants_state = [
        {
            "label": "Vanilla Retexture",
            "CharacterID": "WeaselDragon",
            "Category": "Monster",
            "SkeletonSource": "base",
            "Gender": "Female",
            "IsRarePal": True,
            "SkinName": "",
            "ReqTrait": ["Legend"],
            "PrefTrait": ["MoveSpeed_up_3"],
            "MatReplace": [{"Index": "2", "MatPath": "/Game/Mods/WeaselDragon/MI_WeaselDragon_Body"}],
            "MorphTarget": []
        }
    ]
    
    editing_index = -1  # -1 means creating a new variant
    temp_req_traits = []
    temp_pref_traits = []
    
    # Active runtime states for material and morph sub-elements inside the modal
    active_material_dropdowns = {}
    active_morph_states = {}

    # Dynamic sub-containers for the modal
    mat_replaces_col = ft.Column(spacing=8)
    morphs_col = ft.Column(spacing=8)
    selected_tags_row = ft.Row(wrap=True, spacing=5)
    search_results_col = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, height=140)

    # Output log view
    log_text = ft.Text("Sandbox initialized. Select a context and click [+] to add variants.", color=ft.Colors.CYAN_200, font_family="Consolas", size=12)
    log_container = ft.Container(
        content=ft.Column([log_text], scroll=ft.ScrollMode.AUTO),
        height=140,
        bgcolor=ft.Colors.BLACK,
        border_radius=8,
        padding=10,
        border=ft.Border.all(1, ft.Colors.WHITE10)
    )

    def write_log(text: str, is_success: bool = True):
        log_text.value = text
        log_text.color = ft.Colors.GREEN_400 if is_success else ft.Colors.RED_400
        try:
            log_container.update()
        except Exception:
            pass

    # Prompt user on launch if traits_db.json is missing
    if not traits_db:
        write_log("WARNING: 'traits_db.json' was not found in the root directory. Trait selection panel will be empty.", is_success=False)

    # --- UI Active Context Controls ---
    active_mod_dropdown = ft.Dropdown(
        label="Simulated Mod Context",
        value="WeaselDragon",
        width=250,
        options=[
            ft.dropdown.Option("WeaselDragon"),
            ft.dropdown.Option("AmaterasuWolf"),
            ft.dropdown.Option("GrimGirl"),
            ft.dropdown.Option("Cattiva")
        ]
    )

    active_category_dropdown = ft.Dropdown(
        label="Mod Category",
        value="Monster",
        width=200,
        options=[
            ft.dropdown.Option("Monster"),
            ft.dropdown.Option("Pending Monster")
        ]
    )

    # --- Modal Input Controls ---
    label_input = ft.TextField(label="Variant Label/Name", hint_text="e.g., SFW_Bikini_T-Shirt")
    char_id_input = ft.TextField(label="Character ID (Locked)", disabled=True)
    skeleton_source_dropdown = ft.Dropdown(label="Skeleton / Mesh Source")
    gender_dropdown = ft.Dropdown(
        label="Gender",
        options=[
            ft.dropdown.Option("None"),
            ft.dropdown.Option("Male"),
            ft.dropdown.Option("Female"),
            ft.dropdown.Option("Futa"),
            ft.dropdown.Option("FullFuta"),
            ft.dropdown.Option("Andro"),
            ft.dropdown.Option("Neutered")
        ]
    )
    is_rare_checkbox = ft.Checkbox(label="Is Rare/Lucky Pal")
    skin_name_input = ft.TextField(label="Target Skin Override Name (Optional)", hint_text="e.g., WeaselDragon_Skin001")
    search_input = ft.TextField(label="Fuzzy Search Passive Traits...", hint_text="e.g., Artisan, Swift, Rare")

    # --- Dynamic Trait Chip UI Manager ---
    def refresh_selected_tags():
        selected_tags_row.controls.clear()
        
        # Required traits (Green)
        for trait_id in temp_req_traits:
            game_name = next((g for g, i in traits_db.items() if i == trait_id), trait_id)
            selected_tags_row.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(f"Req: {game_name}", size=10, weight=ft.FontWeight.BOLD),
                        ft.IconButton(
                            ft.Icons.CLOSE, 
                            icon_size=10, 
                            icon_color=ft.Colors.WHITE,
                            data=("req", trait_id), 
                            on_click=remove_selected_trait,
                            style=ft.ButtonStyle(padding=0)
                        )
                    ], spacing=1, tight=True),
                    bgcolor=ft.Colors.GREEN_900,
                    border_radius=4,
                    padding=ft.Padding(left=6, right=2, top=4, bottom=4)
                )
            )

        # Preferred traits (Purple)
        for trait_id in temp_pref_traits:
            game_name = next((g for g, i in traits_db.items() if i == trait_id), trait_id)
            selected_tags_row.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(f"Pref: {game_name}", size=10, weight=ft.FontWeight.BOLD),
                        ft.IconButton(
                            ft.Icons.CLOSE, 
                            icon_size=10, 
                            icon_color=ft.Colors.WHITE,
                            data=("pref", trait_id), 
                            on_click=remove_selected_trait,
                            style=ft.ButtonStyle(padding=0)
                        )
                    ], spacing=1, tight=True),
                    bgcolor=ft.Colors.PURPLE_900,
                    border_radius=4,
                    padding=ft.Padding(left=6, right=2, top=4, bottom=4)
                )
            )
        try:
            dialog.update()
        except Exception:
            pass

    def remove_selected_trait(e):
        list_type, trait_id = e.control.data
        if list_type == "req":
            temp_req_traits.remove(trait_id)
        else:
            temp_pref_traits.remove(trait_id)
        refresh_selected_tags()
        refresh_search_results(search_input.value)

    def refresh_search_results(query: str = ""):
        """Populates the search panel. Shows everything when empty, and filters when typing."""
        query = query.strip().lower()
        search_results_col.controls.clear()
        
        matches_found = 0
        for game_name, internal_id in traits_db.items():
            if not query or (query in game_name.lower() or query in internal_id.lower()):
                is_req = internal_id in temp_req_traits
                is_pref = internal_id in temp_pref_traits
                
                # Exclude traits that are already selected
                if not is_req and not is_pref:
                    search_results_col.controls.append(
                        ft.Row([
                            ft.Text(f"{game_name} ({internal_id})", size=12, expand=True),
                            ft.TextButton(
                                "Add Req", 
                                style=ft.ButtonStyle(color=ft.Colors.GREEN_400),
                                on_click=lambda e, tid=internal_id: add_trait_to_state(tid, "req")
                            ),
                            ft.TextButton(
                                "Add Pref", 
                                style=ft.ButtonStyle(color=ft.Colors.PURPLE_400),
                                on_click=lambda e, tid=internal_id: add_trait_to_state(tid, "pref")
                            )
                        ], spacing=10)
                    )
                    matches_found += 1
                        
        if matches_found == 0:
            search_results_col.controls.append(
                ft.Text("No matching traits found.", size=12, italic=True, color=ft.Colors.WHITE38)
            )
            
        try:
            dialog.update()
        except Exception:
            pass

    def add_trait_to_state(trait_id: str, list_type: str):
        if list_type == "req":
            temp_req_traits.append(trait_id)
        else:
            temp_pref_traits.append(trait_id)
        
        search_input.value = ""
        refresh_search_results("")
        refresh_selected_tags()


    # --- Auto-Slot Material Override Renderer ---
    def populate_material_slots_layout(selected_source: str, preloaded_overrides: list | None = None):
        """Discovers the skeletal mesh slots and renders visual dropdown overrides for each slot."""
        mat_replaces_col.controls.clear()
        active_material_dropdowns.clear()

        current_char_id = active_mod_dropdown.value
        slots = get_material_slots_for_mesh(current_char_id or "", selected_source)  # type: ignore
        available_mats = get_available_materials_for_context(current_char_id or "")  # type: ignore

        for idx, slot_name in enumerate(slots):
            dropdown_options = [ft.dropdown.Option("default", "Default (No Override)")]
            for mat in available_mats:
                dropdown_options.append(ft.dropdown.Option(mat, mat))

            initial_val = "default"
            if preloaded_overrides:
                matched_override = next((item for item in preloaded_overrides if int(item["Index"]) == idx), None)
                if matched_override:
                    initial_val = matched_override["MatPath"].split("/")[-1]

            dd = ft.Dropdown(
                value=initial_val,
                options=dropdown_options,
                expand=True
            )
            active_material_dropdowns[idx] = dd

            mat_replaces_col.controls.append(
                ft.Row([
                    ft.Text(f"Slot {idx} ({slot_name}):", size=11, weight=ft.FontWeight.BOLD, width=150),
                    dd
                ], spacing=10)
            )


    # --- Morph Target Behavioral Row Renderers ---
    def update_morph_state(morph_name: str, key: str, value):
        active_morph_states[morph_name][key] = value

    def render_morph_row_controls(morph_name: str, mode: str, preloaded_data: dict | None = None) -> list[ft.Control]:
        """Dynamically renders context-dependent sliders based on selected behavior mode."""
        controls = []
        state_key = morph_name

        if state_key not in active_morph_states:
            active_morph_states[state_key] = {
                "mode": "None",
                "set_val": 0.5,
                "min_val": 0.0,
                "max_val": 1.0,
                "type_val": "Free"
            }

            if preloaded_data:
                if "Set" in preloaded_data:
                    active_morph_states[state_key]["mode"] = "Static"
                    active_morph_states[state_key]["set_val"] = float(preloaded_data["Set"])
                elif "Min" in preloaded_data or "Max" in preloaded_data:
                    active_morph_states[state_key]["mode"] = "Random"
                    active_morph_states[state_key]["min_val"] = float(preloaded_data.get("Min", 0.0))
                    active_morph_states[state_key]["max_val"] = float(preloaded_data.get("Max", 1.0))
                    active_morph_states[state_key]["type_val"] = preloaded_data.get("Type", "Free")

        current_state = active_morph_states[state_key]
        current_state["mode"] = mode

        if mode == "Static":
            slider = ft.Slider(
                min=0.0, max=1.0, divisions=20,
                value=current_state["set_val"],
                label="Set: {value}",
                on_change=lambda e, mn=state_key: update_morph_state(mn, "set_val", e.control.value),
                expand=True
            )
            controls.append(ft.Row([ft.Text("Forced value:", size=11, width=100), slider], spacing=5))
            
        elif mode == "Random":
            min_slider = ft.Slider(
                min=0.0, max=1.0, divisions=20,
                value=current_state["min_val"],
                label="Min: {value}",
                on_change=lambda e, mn=state_key: update_morph_state(mn, "min_val", e.control.value),
                expand=True
            )
            max_slider = ft.Slider(
                min=0.0, max=1.0, divisions=20,
                value=current_state["max_val"],
                label="Max: {value}",
                on_change=lambda e, mn=state_key: update_morph_state(mn, "max_val", e.control.value),
                expand=True
            )
            type_dd = ft.Dropdown(
                value=current_state["type_val"],
                options=[ft.dropdown.Option("Free"), ft.dropdown.Option("Restrict")],
                width=140
            )
            type_dd.on_change = lambda e, mn=state_key: update_morph_state(mn, "type_val", e.control.value)  # type: ignore
            controls.append(ft.Column([
                ft.Row([ft.Text("Min Boundary:", size=11, width=100), min_slider], spacing=5),
                ft.Row([ft.Text("Max Boundary:", size=11, width=100), max_slider], spacing=5),
                ft.Row([ft.Text("Roll Mode:", size=11, width=100), type_dd], spacing=5)
            ]))
            
        return controls

    def populate_morph_targets_layout(selected_source: str, preloaded_morphs: list | None = None):
        """Discovers active morph targets and renders their control rows."""
        morphs_col.controls.clear()
        active_morph_states.clear()
        
        current_char_id = active_mod_dropdown.value
        current_category = active_category_dropdown.value
        
        morph_names = get_morph_targets_for_mesh(current_category or "", current_char_id or "", selected_source)  # type: ignore
        
        preload_map = {}
        if preloaded_morphs:
            for item in preloaded_morphs:
                preload_map[item["Target"]] = item

        for name in morph_names:
            preload_data = preload_map.get(name)
            options_container = ft.Column()
            
            initial_mode = "None"
            if preload_data:
                if "Set" in preload_data:
                    initial_mode = "Static"
                elif "Min" in preload_data or "Max" in preload_data:
                    initial_mode = "Random"

            mode_dd = ft.Dropdown(
                value=initial_mode,
                options=[
                    ft.dropdown.Option("None", "Ignore"),
                    ft.dropdown.Option("Static", "Static (Set)"),
                    ft.dropdown.Option("Random", "Random (Range)")
                ],
                width=160
            )

            # Bind dynamically to trigger container updates inside the modal
            def handle_mode_change(e, m_name=name, container=options_container):
                container.controls = render_morph_row_controls(m_name, e.control.value)
                dialog.update()

            mode_dd.on_change = handle_mode_change  # type: ignore

            # Initialize active options
            options_container.controls = render_morph_row_controls(name, initial_mode, preload_data)

            morphs_col.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(name, size=12, weight=ft.FontWeight.BOLD, expand=True),
                            mode_dd
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        options_container
                    ], spacing=10),
                    padding=10,
                    border=ft.Border.all(1, ft.Colors.WHITE10),
                    border_radius=6,
                    bgcolor=ft.Colors.WHITE10
                )
            )


    # Trigger update when the selected skeleton changes
    def on_skeleton_source_changed(e):
        selected_source = skeleton_source_dropdown.value
        populate_material_slots_layout(selected_source or "")  # type: ignore
        populate_morph_targets_layout(selected_source or "")  # type: ignore
        dialog.update()


    # --- Dialog Operations ---
    def close_dialog(e):
        close_dialog_safe(page, dialog)

    def save_variant(e):
        if not label_input.value or not skeleton_source_dropdown.value:
            write_log("Validation Failed: Label and Skeleton Source are required.", is_success=False)
            return

        # Resolve active material overrides directly from UI Dropdowns
        mat_replaces = []
        for idx, dropdown in active_material_dropdowns.items():
            if dropdown.value and dropdown.value != "default":
                mat_path = resolve_material_path(active_category_dropdown.value or "", char_id_input.value or "", dropdown.value)  # type: ignore
                mat_replaces.append({
                    "Index": str(idx),
                    "MatPath": mat_path
                })

        # Resolve active morph target overrides
        morphs = []
        for name, state in active_morph_states.items():
            if state["mode"] == "Static":
                morphs.append({
                    "Target": name,
                    "Set": state["set_val"]
                })
            elif state["mode"] == "Random":
                morphs.append({
                    "Target": name,
                    "Min": state["min_val"],
                    "Max": state["max_val"],
                    "Type": state["type_val"]
                })

        variant_data = {
            "label": label_input.value.strip(),
            "CharacterID": char_id_input.value,
            "Category": active_category_dropdown.value,
            "SkeletonSource": skeleton_source_dropdown.value,
            "Gender": gender_dropdown.value if gender_dropdown.value else "None",
            "IsRarePal": is_rare_checkbox.value,
            "SkinName": skin_name_input.value.strip() if skin_name_input.value else "",
            "ReqTrait": list(temp_req_traits),
            "PrefTrait": list(temp_pref_traits),
            "MatReplace": mat_replaces,
            "MorphTarget": morphs
        }

        if editing_index == -1:
            variants_state.append(variant_data)
            write_log(f"Created variant '{variant_data['label']}'")
        else:
            filtered_indices = [idx for idx, v in enumerate(variants_state) if v["CharacterID"] == active_mod_dropdown.value]
            global_index = filtered_indices[editing_index]
            variants_state[global_index] = variant_data
            write_log(f"Updated variant '{variant_data['label']}'")

        close_dialog_safe(page, dialog)
        render_grid()

    # Define build modal
    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Visual Altermatic Configurator"),
        actions=[
            ft.TextButton("Cancel", on_click=close_dialog),
            ft.TextButton("Apply Changes", on_click=save_variant)
        ],
        content=ft.Column([
            label_input,
            char_id_input,
            skeleton_source_dropdown,
            ft.Row([gender_dropdown, is_rare_checkbox], spacing=20),
            skin_name_input,
            ft.Divider(),
            ft.Text("Required & Preferred Passive Traits", size=12, weight=ft.FontWeight.BOLD),
            selected_tags_row,
            search_input,
            search_results_col,
            ft.Divider(),
            ft.Text("Visual Material Overrides (MatReplace)", size=12, weight=ft.FontWeight.BOLD),
            mat_replaces_col,
            ft.Divider(),
            ft.Text("Dynamic Morph Target Parameters", size=12, weight=ft.FontWeight.BOLD),
            morphs_col,
        ], scroll=ft.ScrollMode.ALWAYS, height=450, width=580)
    )
    page.dialog = dialog  # type: ignore

    # Bind listeners safely after controls instantiation to prevent version/constructor conflicts
    search_input.on_change = lambda e: refresh_search_results(search_input.value)  # type: ignore
    skeleton_source_dropdown.on_change = on_skeleton_source_changed  # type: ignore

    # --- Variant Manager Operations ---
    def open_builder_modal(index: int = -1):
        nonlocal editing_index, temp_req_traits, temp_pref_traits
        editing_index = index

        current_char_id = active_mod_dropdown.value
        current_category = active_category_dropdown.value

        # Pre-fill locked context fields
        char_id_input.value = current_char_id or ""  # type: ignore

        # Dynamically build skeleton source dropdown choices
        blend_files = get_blend_files_for_context(current_category or "", current_char_id or "")  # type: ignore
        dropdown_options = [ft.dropdown.Option("base", "base (Vanilla Canonical Mesh)")]
        for f in blend_files:
            dropdown_options.append(ft.dropdown.Option(f, f"Blender: {f}"))
        skeleton_source_dropdown.options = dropdown_options

        search_input.value = ""
        refresh_search_results("")

        if index == -1:
            # Setup clean slate
            label_input.value = ""
            skeleton_source_dropdown.value = "base"
            gender_dropdown.value = "None"
            is_rare_checkbox.value = False
            skin_name_input.value = ""
            temp_req_traits = []
            temp_pref_traits = []
            populate_material_slots_layout("base")
            populate_morph_targets_layout("base")
        else:
            filtered_indices = [idx for idx, v in enumerate(variants_state) if v["CharacterID"] == current_char_id]
            global_index = filtered_indices[index]
            
            v = variants_state[global_index]
            label_input.value = v["label"]
            skeleton_source_dropdown.value = v["SkeletonSource"]
            gender_dropdown.value = v["Gender"]
            is_rare_checkbox.value = v["IsRarePal"]
            skin_name_input.value = v["SkinName"]
            temp_req_traits = list(v["ReqTrait"])
            temp_pref_traits = list(v["PrefTrait"])
            populate_material_slots_layout(v["SkeletonSource"], v["MatReplace"])
            populate_morph_targets_layout(v["SkeletonSource"], v["MorphTarget"])

        refresh_selected_tags()
        show_dialog_safe(page, dialog)

    def delete_filtered_variant(index: int):
        current_char_id = active_mod_dropdown.value
        filtered_indices = [idx for idx, v in enumerate(variants_state) if v["CharacterID"] == current_char_id]
        global_index = filtered_indices[index]
        
        popped = variants_state.pop(global_index)
        write_log(f"Deleted variant '{popped['label']}'")
        render_grid()

    # --- Compilation & Export Engine ---
    def save_and_export_altermatic_json(e):
        """Compiles active layouts, strips redundant empty keys, and saves to the repo root."""
        if not variants_state:
            write_log("Export Failed: No variants are configured in the workspace.", is_success=False)
            return

        final_swaps = []
        for v in variants_state:
            # Resolve the skeleton source dynamically
            mesh_resolved_path = resolve_skel_mesh_path(v["Category"], v["CharacterID"], v["SkeletonSource"])

            # Strip out unconfigured fields to follow Altermatic standards
            compiled_item = {
                "CharacterID": v["CharacterID"],
                "SkelMeshPath": mesh_resolved_path,
                "Gender": v["Gender"]
            }
            if v["IsRarePal"]:
                compiled_item["IsRarePal"] = "True"
            if v["SkinName"]:
                compiled_item["SkinName"] = v["SkinName"]
            if v["ReqTrait"]:
                compiled_item["ReqTrait"] = v["ReqTrait"]
            if v["PrefTrait"]:
                compiled_item["PrefTrait"] = v["PrefTrait"]
            if v["MatReplace"]:
                compiled_item["MatReplace"] = v["MatReplace"]
            if v["MorphTarget"]:
                compiled_item["MorphTarget"] = v["MorphTarget"]

            final_swaps.append(compiled_item)

        output_structure = {
            "PackName": "PalBaker Standalone Configurator",
            "SkelMeshSwap": final_swaps
        }

        # Resolve output target to root folder
        root_dir = os.path.dirname(os.path.abspath(__file__))
        target_path = os.path.join(root_dir, "altermatic_config.json")

        try:
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(output_structure, f, indent=4)
            write_log(f"SUCCESS! Exported file to: {target_path}\nPayload preview:\n{json.dumps(output_structure, indent=2)}")
        except Exception as err:
            write_log(f"Export Error: {err}", is_success=False)

    # --- Grid Card Rendering ---
    def render_grid():
        variants_row.controls.clear()
        current_char_id = active_mod_dropdown.value

        # Filter display to only show variants matching the selected active context
        filtered_variants = [v for v in variants_state if v["CharacterID"] == current_char_id]

        for idx, v in enumerate(filtered_variants):
            traits_count = len(v["ReqTrait"]) + len(v["PrefTrait"])
            materials_count = len(v["MatReplace"])
            morphs_count = len(v["MorphTarget"])
            
            badge_row = ft.Row([
                ft.Container(ft.Text(v["Gender"], size=9, weight=ft.FontWeight.BOLD), bgcolor=ft.Colors.BLUE_900, padding=4, border_radius=4),
            ], spacing=5)
            
            if v["IsRarePal"]:
                badge_row.controls.append(ft.Container(ft.Text("LUCKY", size=9, weight=ft.FontWeight.BOLD), bgcolor=ft.Colors.AMBER_900, padding=4, border_radius=4))
            if traits_count > 0:
                badge_row.controls.append(ft.Container(ft.Text(f"TRAITS: {traits_count}", size=9, weight=ft.FontWeight.BOLD), bgcolor=ft.Colors.GREEN_900, padding=4, border_radius=4))
            if materials_count > 0:
                badge_row.controls.append(ft.Container(ft.Text(f"MATS: {materials_count}", size=9, weight=ft.FontWeight.BOLD), bgcolor=ft.Colors.PURPLE_900, padding=4, border_radius=4))
            if morphs_count > 0:
                badge_row.controls.append(ft.Container(ft.Text(f"MORPHS: {morphs_count}", size=9, weight=ft.FontWeight.BOLD), bgcolor=ft.Colors.CYAN_900, padding=4, border_radius=4))

            # Resolve the mock skeleton label
            sk_label = "base" if v["SkeletonSource"] == "base" else f"SK_{os.path.splitext(v['SkeletonSource'])[0]}"

            card = ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.LABEL, color=ft.Colors.CYAN_400, size=20),
                            ft.Text(v["label"], weight=ft.FontWeight.BOLD, size=14, overflow=ft.TextOverflow.ELLIPSIS, expand=True)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Text(f"Source: {sk_label}", size=11, color=ft.Colors.WHITE54),
                        badge_row,
                        ft.Row([
                            ft.IconButton(ft.Icons.EDIT_ROUNDED, icon_size=18, on_click=lambda e, idx=idx: open_builder_modal(idx)),
                            ft.IconButton(ft.Icons.DELETE_ROUNDED, icon_size=18, icon_color=ft.Colors.RED_400, on_click=lambda e, idx=idx: delete_filtered_variant(idx))
                        ], alignment=ft.MainAxisAlignment.END, spacing=0)
                    ], spacing=10),
                    width=250,
                    padding=15
                )
            )
            variants_row.controls.append(card)

        # Append standard context [+] Card at the end of the grid
        plus_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.ADD_CIRCLE_OUTLINE_ROUNDED, size=40, color=ft.Colors.CYAN_400),
                    ft.Text(f"Add {current_char_id} Variant", weight=ft.FontWeight.BOLD, size=12, color=ft.Colors.CYAN_400)
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                width=250,
                height=135,
                ink=True,
                on_click=lambda e: open_builder_modal(-1)
            )
        )
        variants_row.controls.append(plus_card)
        
        try:
            page.update()
        except Exception:
            pass

    # Assign event handlers after controls instantiation to prevent version/constructor conflicts
    active_mod_dropdown.on_change = lambda e: render_grid()  # type: ignore
    active_category_dropdown.on_change = lambda e: render_grid()  # type: ignore

    # Populate grid on initialization
    variants_row = ft.Row(wrap=True, spacing=10)
    render_grid()

    # Mount UI Elements to Screen
    page.add(
        ft.Column([
            ft.Row([
                ft.Column([
                    ft.Text("Altermatic Mod Builder Sandbox", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.CYAN_400),
                    ft.Text("Configure branching conditional swap models. The parent container will export a clean Altermatic JSON directly to the repository root.", size=12, color=ft.Colors.WHITE54)
                ], expand=True),
                ft.FilledButton("Save & Export JSON", icon=ft.Icons.SAVE_ALT_ROUNDED, on_click=save_and_export_altermatic_json, height=45)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=10),
            ft.Row([
                active_mod_dropdown,
                active_category_dropdown
            ], spacing=20),
            variants_row,
            ft.Divider(height=10),
            ft.Text("Output Compiler logs", size=14, weight=ft.FontWeight.BOLD),
            log_container
        ], expand=True, spacing=15)
    )

if __name__ == "__main__":
    ft.run(main)
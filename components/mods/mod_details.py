# components/mods/mod_details.py
import flet as ft

class ModDetails:
    def __init__(self, mod_data: dict, on_pick_icon, on_pick_audio, on_play_audio, on_clear_audio,
                 on_toggle_altermatic, on_add_variant, on_edit_variant, on_delete_variant):
        self.mod_data = mod_data
        self.on_pick_icon = on_pick_icon
        self.on_pick_audio = on_pick_audio
        self.on_play_audio = on_play_audio
        self.on_clear_audio = on_clear_audio
        
        # Altermatic custom callbacks
        self.on_toggle_altermatic = on_toggle_altermatic
        self.on_add_variant = on_add_variant
        self.on_edit_variant = on_edit_variant

        # --- ICON SLOT COMPONENT ---
        has_icon = mod_data.get("has_icon", False)
        icon_path = mod_data.get("icon_path", "")
        
        if has_icon and icon_path:
            content = ft.Image(src=icon_path, width=64, height=64, fit=ft.BoxFit.CONTAIN)
        else:
            content = ft.Icon(ft.Icons.ADD_PHOTO_ALTERNATE, size=32, color=ft.Colors.WHITE54)

        self.icon_slot = ft.Container(
            content=content,
            width=64,
            height=64,
            border=ft.Border.all(1, ft.Colors.WHITE24),
            border_radius=8,
            ink=True,
            on_click=self.handle_icon_click,
            tooltip="Click to set custom Pal Icon"
        )

        icon_section = ft.Column([
            ft.Text("Pal Icon", size=11, weight=ft.FontWeight.BOLD),
            self.icon_slot
        ], spacing=5)

        # --- AUDIO CUSTOMIZATION SECTION ---
        audio_section_controls: list[ft.Control] = []
        has_fmodel = mod_data.get("has_fmodel", False)
        sound_meta = mod_data.get("sound_metadata", {})

        if not has_fmodel:
            audio_section_controls.append(
                ft.Text(
                    "Audio replacement requires raw FModel files.\nPlease click 'Create .blend file' or 'Generate Sources' first.",
                    size=11,
                    color=ft.Colors.WHITE38,
                    italic=True
                )
            )
        elif not sound_meta:
            audio_section_controls.append(
                ft.Text(
                    "No mapped database found for this Pal.",
                    size=11,
                    color=ft.Colors.WHITE38,
                    italic=True
                )
            )
        else:
            audio_section_controls.append(
                ft.Text("Custom Pal Cries (.wav, .mp3, .ogg)", size=11, weight=ft.FontWeight.BOLD)
            )
            
            col1_controls: list[ft.Control] = []
            col2_controls: list[ft.Control] = []
            audio_overrides = mod_data.get("audio_overrides", {})
            available_cries = [c for c in ["Normal", "Joy", "Anger", "Sorrow", "Pain", "Death"] if c in sound_meta]

            for i, cry_name in enumerate(available_cries):
                is_set = audio_overrides.get(cry_name) is not None
                color = ft.Colors.GREEN_400 if is_set else ft.Colors.WHITE30
                status_text = "Custom Override" if is_set else "Original Game Sound"

                cry_row = ft.Container(
                    content=ft.Row([
                        ft.IconButton(
                            icon=ft.Icons.PLAY_ARROW_ROUNDED,
                            icon_size=16,
                            icon_color=ft.Colors.CYAN_400,
                            data=cry_name,
                            tooltip=f"Preview {cry_name}",
                            on_click=self.handle_play_click
                        ),
                        ft.Column([
                            ft.Text(cry_name, size=11, weight=ft.FontWeight.BOLD),
                            ft.Text(status_text, size=9, color=color)
                        ], spacing=1, expand=True),
                        ft.IconButton(
                            icon=ft.Icons.UPLOAD_FILE_ROUNDED,
                            icon_size=16,
                            data=cry_name,
                            tooltip=f"Set custom sound for {cry_name}",
                            on_click=self.handle_upload_click
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                            icon_size=16,
                            icon_color=ft.Colors.RED_400,
                            data=cry_name,
                            tooltip=f"Revert {cry_name} to original",
                            on_click=self.handle_clear_click,
                            visible=is_set
                        )
                    ], spacing=2),
                    border=ft.Border.all(1, ft.Colors.WHITE10),
                    border_radius=6,
                    padding=2,
                    bgcolor=ft.Colors.WHITE10 if is_set else None
                )

                if i % 2 == 0:
                    col1_controls.append(cry_row)
                else:
                    col2_controls.append(cry_row)

            audio_section_controls.append(
                ft.Row([
                    ft.Column(col1_controls, spacing=5, expand=True),
                    ft.Column(col2_controls, spacing=5, expand=True)
                ], spacing=10, expand=True)
            )

        audio_section = ft.Column(audio_section_controls, spacing=5, expand=True)

        # --- ALTERMATIC CUSTOMIZATION SECTION ---
        altermatic_section_controls: list[ft.Control] = []
        is_altermatic_active = mod_data.get("is_altermatic_active", False)

        # Master Toggle
        self.altermatic_switch = ft.Switch(
            label="Enable Altermatic Framework",
            value=is_altermatic_active,
            on_change=self.handle_switch_toggle,
            label_position=ft.LabelPosition.RIGHT
        )

        # Dynamic Horizontal Wrapping Grid
        self.variants_row = ft.Row(wrap=True, spacing=10)
        
        self.add_variant_button = ft.TextButton(
            "Add Variant", 
            icon=ft.Icons.ADD_CIRCLE_OUTLINE_ROUNDED,
            on_click=lambda e: self.on_add_variant(self.mod_data)
        )

        self.variants_panel = ft.Column([
            ft.Text("Spawn Variants List:", size=11, weight=ft.FontWeight.BOLD),
            self.variants_row,
            self.add_variant_button
        ], visible=is_altermatic_active, spacing=10, expand=True)

        altermatic_section_controls.append(self.altermatic_switch)
        altermatic_section_controls.append(self.variants_panel)

        altermatic_section = ft.Column(altermatic_section_controls, spacing=5, expand=True)

        self.build_variants_list()

        self.view = ft.Container(
            content=ft.Row([
                icon_section,
                ft.VerticalDivider(width=1, color=ft.Colors.WHITE10),
                audio_section,
                ft.VerticalDivider(width=1, color=ft.Colors.WHITE10),
                altermatic_section
            ], spacing=20, vertical_alignment=ft.CrossAxisAlignment.START),
            padding=ft.Padding(left=40, top=10, right=10, bottom=10),
            bgcolor=ft.Colors.WHITE10,
            border_radius=8
        )

    # --- Type-Safe Event Closures ---
    def make_edit_handler(self, index: int):
        return lambda e: self.on_edit_variant(self.mod_data, index)

    def build_variants_list(self):
        """Compiles active sidecars in memory and renders visual chips below the clickable text links."""
        self.variants_row.controls.clear()
        
        variants = self.mod_data.get("altermatic_variants", [])
        
        if not variants:
            self.variants_row.controls.append(
                ft.Text("No custom variants added yet.", size=11, color=ft.Colors.WHITE38, italic=True)
            )
            return

        for idx, v in enumerate(variants):
            is_base = v.get("is_base", False)
            traits_count = len(v.get("ReqTrait", [])) + len(v.get("PrefTrait", []))
            mats_count = len(v.get("MatReplace", []))
            morphs_count = len(v.get("MorphTarget", []))
            
            badge_controls: list[ft.Control] = []
            
            display_label = v["label"]
            prefix = f"{self.mod_data['name']}_"
            if display_label.startswith(prefix):
                display_label = display_label[len(prefix):]

            if is_base:
                badge_controls.append(
                    ft.Container(
                        content=ft.Text("BASE", size=7, weight=ft.FontWeight.BOLD),
                        bgcolor=ft.Colors.GREY_700,
                        padding=2,
                        border_radius=2
                    )
                )
            else:
                # Do NOT render gender badge if set to "None"
                if v.get("Gender", "None") != "None":
                    badge_controls.append(
                        ft.Container(
                            content=ft.Text(v.get("Gender", "None")[:1], size=7, weight=ft.FontWeight.BOLD),
                            bgcolor=ft.Colors.BLUE_900,
                            padding=2,
                            border_radius=2
                        )
                    )
                if v.get("IsRarePal"):
                    badge_controls.append(
                        ft.Container(
                            content=ft.Text("LUCKY", size=7, weight=ft.FontWeight.BOLD),
                            bgcolor=ft.Colors.AMBER_900,
                            padding=2,
                            border_radius=2
                        )
                    )
                if traits_count > 0:
                    badge_controls.append(
                        ft.Container(
                            content=ft.Text(f"T: {traits_count}", size=7, weight=ft.FontWeight.BOLD),
                            bgcolor=ft.Colors.GREEN_900,
                            padding=2,
                            border_radius=2
                        )
                    )
                if mats_count > 0:
                    badge_controls.append(
                        ft.Container(
                            content=ft.Text(f"M: {mats_count}", size=7, weight=ft.FontWeight.BOLD),
                            bgcolor=ft.Colors.PURPLE_900,
                            padding=2,
                            border_radius=2
                        )
                    )
                if morphs_count > 0:
                    badge_controls.append(
                        ft.Container(
                            content=ft.Text(f"MPH: {morphs_count}", size=7, weight=ft.FontWeight.BOLD),
                            bgcolor=ft.Colors.CYAN_900,
                            padding=2,
                            border_radius=2
                        )
                    )

                # FIXED: If the variant is a custom variant but has no active conditional badges,
                # append a neutral "DEFAULT" badge to keep UI proportions uniform.
                if not badge_controls:
                    badge_controls.append(
                        ft.Container(
                            content=ft.Text("DEFAULT", size=7, weight=ft.FontWeight.BOLD),
                            bgcolor=ft.Colors.GREY_800,
                            padding=2,
                            border_radius=2
                        )
                    )

            internal_column_controls: list[ft.Control] = [
                ft.Text(display_label, size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.CYAN_400, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Row(badge_controls, spacing=2, tight=True),
                # --- DUMMY SPACER FOR MIN-WIDTH ---
                # Forces the container to be at least 60px wide cleanly on all versions of Flet
                ft.Container(width=60, height=0)
            ]

            # Unified compact variant chip
            self.variants_row.controls.append(
                ft.Container(
                    content=ft.Column(internal_column_controls, spacing=2, tight=True),
                    bgcolor=ft.Colors.WHITE10,
                    border_radius=6,
                    padding=8,
                    height=52,  # FIXED: Forced uniform vertical height
                    ink=True,
                    on_click=self.make_edit_handler(idx),
                    tooltip=f"Configure {v['label']}"
                )
            )

    def handle_switch_toggle(self, e):
        is_active = e.control.value
        self.variants_panel.visible = is_active
        self.on_toggle_altermatic(self.mod_data, is_active)
        try:
            self.view.update()
        except Exception:
            pass

    async def handle_icon_click(self, e):
        await self.on_pick_icon(self.mod_data)

    async def handle_play_click(self, e):
        await self.on_play_audio(self.mod_data, e.control.data)

    async def handle_upload_click(self, e):
        await self.on_pick_audio(self.mod_data, e.control.data)

    async def handle_clear_click(self, e):
        await self.on_clear_audio(self.mod_data, e.control.data)
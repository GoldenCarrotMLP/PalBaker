# components/mods/dialogs.py
import flet as ft  # type: ignore

def create_overwrite_warning_dialog(files: list, on_confirm, on_cancel) -> ft.AlertDialog:
    files_str = "\n".join([f" • {f}" for f in files])
    return ft.AlertDialog(
        open=True,
        modal=True,
        title=ft.Text("Warning: Overwrite Unreal Assets?"),
        content=ft.Column([
            ft.Text("You have manually modified files inside Unreal Engine since your last Push.\nContinuing will OVERWRITE and delete those changes.\n\nModified files:"),
            ft.Text(files_str, color=ft.Colors.RED_400, size=12, selectable=True),
            ft.Text("Are you sure you want to proceed?", weight=ft.FontWeight.BOLD)
        ], tight=True),
        actions=[
            ft.TextButton("Cancel", on_click=on_cancel),
            ft.TextButton("Overwrite & Proceed", on_click=on_confirm, style=ft.ButtonStyle(color=ft.Colors.RED)),
        ]
    )

def create_decompile_options_dialog(on_missing_only, on_overwrite_all, on_cancel) -> ft.AlertDialog:
    return ft.AlertDialog(
        open=True,
        modal=True,
        title=ft.Text("Generate Source Assets"),
        content=ft.Column([
            ft.Text("This process will reverse-engineer your ModKit's compiled .uassets back into editable Blender and PNG source files.\n\nChoose an extraction mode:"),
            ft.Text(" • Generate Missing Only (Safest — leaves existing files alone)", size=12, color=ft.Colors.WHITE70),
            ft.Text(" • Overwrite & Regenerate (Wipes local source folder)", size=12, color=ft.Colors.WHITE70),
        ], tight=True),
        actions=[
            ft.TextButton("Cancel", on_click=on_cancel),
            ft.TextButton("Missing Only", on_click=on_missing_only),
            ft.TextButton("Overwrite All", on_click=on_overwrite_all, style=ft.ButtonStyle(color=ft.Colors.RED)),
        ]
    )

def create_troubleshooting_advisor_dialog(summary: dict, on_dismiss) -> ft.AlertDialog:
    status = summary.get("status", "")
    
    title_text = "Troubleshooting Advisor"
    title_color = ft.Colors.CYAN_400
    
    if status == "success_with_warnings":
        title_text = "Execution Warnings Detected"
        title_color = ft.Colors.ORANGE_400
    elif status in ["success_with_errors", "failed"]:
        title_text = "Execution Failures Encountered"
        title_color = ft.Colors.RED_400

    matched_rules = summary.get("matched_rules", [])
    if not matched_rules:
        content = ft.Column([
            ft.Text("The operation completed with unexpected compiler or execution errors.", weight=ft.FontWeight.BOLD),
            ft.Text("Please review the red error messages inside the Build Console.", size=13, color=ft.Colors.WHITE70)
        ], tight=True)
    else:
        cards = []
        for rule in matched_rules:
            assets_str = ""
            assets = rule.get("assets", [])
            if assets:
                displayed_assets = assets[:5]
                if len(assets) > 5:
                    displayed_assets.append(f"...and {len(assets) - 5} more files.")
                assets_str = "Violating Files:\n" + "\n".join([f" • {a}" for a in displayed_assets])

            card_content = [
                ft.Text(rule["title"], weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_400, size=14),
                ft.Text(rule["solution"], size=12, color=ft.Colors.WHITE70)
            ]
            
            if assets_str:
                card_content.append(
                    ft.Text(assets_str, size=11, color=ft.Colors.RED_300, font_family="Consolas")
                )

            cards.append(
                ft.Container(
                    content=ft.Column(card_content, spacing=8),  # type: ignore
                    padding=12,
                    border=ft.Border.all(1, ft.Colors.WHITE24),
                    border_radius=6,
                    bgcolor=ft.Colors.WHITE10
                )
            )
            
        content = ft.Column([
            ft.Text("PalBaker Diagnostics identified the following project issues:", weight=ft.FontWeight.BOLD),
            ft.Column(cards, spacing=10, scroll=ft.ScrollMode.AUTO, height=220)
        ], tight=True, spacing=15)

    return ft.AlertDialog(
        title=ft.Text(title_text, color=title_color),
        content=content,
        actions=[ft.TextButton("Dismiss", on_click=on_dismiss)]
    )

def create_build_database_dialog(on_confirm, on_cancel) -> ft.AlertDialog:
    return ft.AlertDialog(
        open=True,
        modal=True,
        title=ft.Text("Pal Names Database Missing"),
        content=ft.Column([
            ft.Text("The local Pal database mapping (pal_names_map.json) is missing.\n\n"
                    "PalBaker can dynamically extract the latest English localization files directly "
                    "from your game files using cue4parse and rebuild the local database.\n\n"
                    "Would you like to build the database now?"),
            ft.Text("Note: This requires a valid Palworld.exe path configured in Settings.", size=11, color=ft.Colors.WHITE54)
        ], tight=True, spacing=10),
        actions=[
            ft.TextButton("Cancel", on_click=on_cancel),
            ft.TextButton("Build Database", on_click=on_confirm, style=ft.ButtonStyle(color=ft.Colors.CYAN_400)),
        ]
    )

def create_unreal_closed_dialog(on_launch, on_cancel) -> ft.AlertDialog:
    return ft.AlertDialog(
        open=True,
        modal=True,
        title=ft.Text("Unreal Editor is Closed", color=ft.Colors.ORANGE_400),
        content=ft.Column([
            ft.Text("The requested action requires Unreal Editor to be running in the background with Python Remote Execution enabled.\n\nWould you like to launch Unreal Editor now?"),
        ], tight=True),
        actions=[
            ft.TextButton("Cancel", on_click=on_cancel),
            ft.TextButton("Launch Unreal Editor", on_click=on_launch, style=ft.ButtonStyle(color=ft.Colors.CYAN_400)),
        ]
    )

def create_remote_exec_disabled_dialog(on_fix, on_cancel) -> ft.AlertDialog:
    return ft.AlertDialog(
        open=True,
        modal=True,
        title=ft.Text("Remote Execution is Disabled", color=ft.Colors.RED_400),
        content=ft.Column([
            ft.Text("Python Remote Execution is currently disabled in your project's settings.\n\nPalBaker can automatically modify your DefaultEngine.ini to enable it and then launch the editor."),
        ], tight=True),
        actions=[
            ft.TextButton("Cancel", on_click=on_cancel),
            ft.TextButton("Enable & Launch", on_click=on_fix, style=ft.ButtonStyle(color=ft.Colors.CYAN_400)),
        ]
    )
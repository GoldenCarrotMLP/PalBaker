// palbaker-ui/src-tauri/src/lib.rs
mod commands;

use std::path::PathBuf;
use std::env;
use tauri::Manager;
use commands::AppState;

/// Dynamically find the path of the `pythoncli/palbaker_cli.py` script.
/// Traverses upwards from the current executable directory or working directory
/// to find the root workspace containing `pythoncli/palbaker_cli.py`.
fn find_python_cli_path() -> PathBuf {
    // 1. Try resolving relative to current working directory first
    if let Ok(cwd) = env::current_dir() {
        let mut path = cwd.clone();
        for _ in 0..5 {
            let candidate = path.join("pythoncli/palbaker_cli.py");
            if candidate.exists() {
                return candidate;
            }
            if !path.pop() {
                break;
            }
        }
    }

    // 2. Try resolving relative to the current executable directory
    if let Ok(exe_path) = env::current_exe() {
        let mut path = exe_path;
        for _ in 0..5 {
            let candidate = path.join("pythoncli/palbaker_cli.py");
            if candidate.exists() {
                return candidate;
            }
            if !path.pop() {
                break;
            }
        }
    }

    // Default Fallback
    PathBuf::from("../pythoncli/palbaker_cli.py")
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            #[allow(unused_mut)]
            let mut is_frozen = false;
            #[allow(unused_mut)]
            let mut exe_path = PathBuf::from("python");
            #[allow(unused_mut)]
            let mut cli_path = find_python_cli_path();

            // When compiled in release, target the embedded PyInstaller executable
            #[cfg(not(debug_assertions))]
            {
                if let Ok(res_dir) = app.path().resource_dir() {
                    let frozen_exe = res_dir.join("resources").join("backend").join("palbaker_cli.exe");
                    if frozen_exe.exists() {
                        is_frozen = true;
                        exe_path = frozen_exe.clone();
                        cli_path = frozen_exe; 
                    }
                }
            }

            let app_state = AppState {
                python_exe: exe_path,
                cli_path,
                is_frozen,
            };
            app.manage(app_state);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::manager_list,
            commands::creator_list,
            commands::creator_add,          // <-- ADDED: The missing command router!
            commands::env_status,
            commands::env_launch_unreal,
            commands::env_restart_unreal,
            commands::get_spawners,
            commands::creator_save,
            commands::creator_delete,
            commands::get_app_version,
            commands::run_mod_action,
            commands::unreal_ping,
            commands::audio_set,
            commands::audio_clear,
            commands::audio_play,
            commands::altermatic_toggle,
            commands::altermatic_metadata,
            commands::altermatic_add,
            commands::altermatic_delete,
            commands::altermatic_save,
            commands::altermatic_open_blend,
            commands::altermatic_sidecar,
            commands::set_mod_icon,
            commands::save_mod_icon_bytes,
            commands::save_mod_audio_bytes,
            commands::get_config,
            commands::set_config,
            commands::ue4ss_manage,
            commands::palschema_manage,
            commands::cpp_plugin_manage,
            commands::creator_refresh_bp,
            commands::manager_build_db,
            commands::env_verify,
            commands::env_enable_remote_exec,
            commands::env_autodetect,
            commands::env_inject_assets,
            commands::env_extract_icons,
            commands::set_mod_preserve_materials,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
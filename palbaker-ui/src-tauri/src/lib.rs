// palbaker-ui/src-tauri/src/lib.rs
mod commands;

use std::path::PathBuf;
use std::env;
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
    // Resolve absolute path or standard installation path for Windows python execution
    let python_exe = PathBuf::from("C:\\Python312\\python.exe");
    let cli_path = find_python_cli_path();

    let app_state = AppState {
        python_exe,
        cli_path,
    };

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .manage(app_state)
        .invoke_handler(tauri::generate_handler![
            commands::manager_list,
            commands::creator_list,
            commands::env_status,
            commands::env_launch_unreal,
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
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

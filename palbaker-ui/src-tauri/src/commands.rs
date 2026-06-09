// palbaker-ui/src-tauri/src/commands.rs
use std::process::Command;
use std::path::PathBuf;
use std::io::{BufRead, BufReader};
use std::thread;
use tauri::{State, Emitter, AppHandle};
use serde_json::Value;

pub struct AppState {
    pub python_exe: PathBuf,
    pub cli_path: PathBuf,
}

#[derive(serde::Serialize, Clone)]
struct LogPayload {
    level: String,
    msg: String,
}

fn emit_log(app: &AppHandle, level: &str, msg: &str) {
    let payload = LogPayload {
        level: level.to_string(),
        msg: msg.to_string(),
    };
    let _ = app.emit("console_log", payload);
}

fn run_cli(app: &AppHandle, state: &AppState, args: &[&str]) -> Result<String, String> {
    let args_joined = args.join(" ");
    let silence = args_joined.contains("ping")
        || args_joined.contains("config get")
        || args_joined.contains("manager list");

    let command_str = format!("python palbaker_cli.py {}", args_joined);
    if !silence {
        emit_log(app, "INFO", &format!("Running backend command: {}", command_str));
    }

    // Determine the working directory for the python process
    let work_dir = state.cli_path.parent()
        .ok_or_else(|| "Could not determine CLI parent working directory".to_string())?;

    // Spawn the child process with piped streams and unbuffered output
    let mut child = Command::new(&state.python_exe)
        .current_dir(work_dir)
        .arg(&state.cli_path)
        .args(args)
        .env("PYTHONUNBUFFERED", "1")
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .spawn()
        .map_err(|e| {
            let err_msg = format!("Failed to spawn Python process: {}", e);
            if !silence {
                emit_log(app, "ERROR", &err_msg);
            }
            err_msg
        })?;

    let stdout_stream = child.stdout.take().ok_or_else(|| "Failed to pipe stdout".to_string())?;
    let stderr_stream = child.stderr.take().ok_or_else(|| "Failed to pipe stderr".to_string())?;

    // Setup stdout accumulator for JSON queries
    let stdout_accumulator = std::sync::Arc::new(std::sync::Mutex::new(String::new()));
    let stdout_acc_clone = stdout_accumulator.clone();
    
    let app_clone = app.clone();
    let stdout_handle = thread::spawn(move || {
        let reader = BufReader::new(stdout_stream);
        for line in reader.lines() {
            if let Ok(l) = line {
                if !silence {
                    emit_log(&app_clone, "INFO", &l);
                }
                if let Ok(mut acc) = stdout_acc_clone.lock() {
                    acc.push_str(&l);
                    acc.push('\n');
                }
            }
        }
    });

    let app_clone2 = app.clone();
    let stderr_handle = thread::spawn(move || {
        let reader = BufReader::new(stderr_stream);
        for line in reader.lines() {
            if let Ok(l) = line {
                if !silence {
                    emit_log(&app_clone2, "ERROR", &l);
                }
            }
        }
    });

    // Wait for the process to exit
    let status = child.wait().map_err(|e| format!("Failed to wait on child process: {}", e))?;

    // Join threads to ensure all logs are flushed
    let _ = stdout_handle.join();
    let _ = stderr_handle.join();

    let stdout_str = {
        let acc = stdout_accumulator.lock().map_err(|e| format!("Lock poisoned: {}", e))?;
        acc.clone()
    };

    if !status.success() {
        let err_msg = format!("CLI exited with non-zero status: {}", status.code().unwrap_or(-1));
        emit_log(app, "ERROR", &err_msg);
        let trimmed_stdout = stdout_str.trim();
        if !trimmed_stdout.is_empty() {
            return Err(trimmed_stdout.to_string());
        }
        return Err(err_msg);
    }

    if !silence {
        emit_log(app, "SUCCESS", &format!("Command completed successfully: {}", command_str));
    }
    Ok(stdout_str)
}

#[tauri::command]
pub async fn manager_list(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["manager", "list", "--show-unextracted"])?;
    let parsed: Value = serde_json::from_str(&raw)
        .map_err(|e| format!("JSON parse error on list output: {}", e))?;
    Ok(parsed)
}

#[tauri::command]
pub async fn creator_list(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["creator", "list"])?;
    let parsed: Value = serde_json::from_str(&raw)
        .map_err(|e| format!("JSON parse error on creator list: {}", e))?;
    Ok(parsed)
}

#[tauri::command]
pub async fn env_status(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["env", "status"])?;
    let parsed: Value = serde_json::from_str(&raw)
        .map_err(|e| format!("JSON parse error on env status: {}", e))?;
    Ok(parsed)
}

#[tauri::command]
pub async fn env_launch_unreal(
    app: AppHandle,
    state: State<'_, AppState>,
) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["env", "launch-unreal"])?;
    let parsed: Value = serde_json::from_str(&raw)
        .unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn get_spawners(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["manager", "get-caches"])?;
    let parsed: Value = serde_json::from_str(&raw)
        .map_err(|e| format!("JSON parse error on spawners: {}", e))?;
    Ok(parsed)
}

#[tauri::command]
pub async fn creator_save(
    app: AppHandle,
    state: State<'_, AppState>,
    id: String,
    data: String,
    is_new: bool,
    template_id: Option<String>,
) -> Result<Value, String> {
    if is_new {
        let parent = template_id.unwrap_or_else(|| "Anubis".to_string());
        let _raw_add = run_cli(&app, &state, &["creator", "add", &id, "--template", &parent])?;
    }

    let raw_update = run_cli(&app, &state, &["creator", "update", &id, "--data", &data])?;
    let parsed: Value = serde_json::from_str(&raw_update)
        .map_err(|e| format!("JSON parse error on creator update: {}", e))?;
    Ok(parsed)
}

#[tauri::command]
pub async fn creator_delete(app: AppHandle, state: State<'_, AppState>, id: String) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["creator", "delete", &id])?;
    let parsed: Value = serde_json::from_str(&raw)
        .map_err(|e| format!("JSON parse error on creator delete: {}", e))?;
    Ok(parsed)
}

#[tauri::command]
pub async fn get_app_version() -> Result<String, String> {
    let output = Command::new("git")
        .args(&["rev-list", "--count", "HEAD"])
        .output();
        
    let count = match output {
        Ok(out) if out.status.success() => {
            let s = String::from_utf8_lossy(&out.stdout).trim().to_string();
            s.parse::<u32>().unwrap_or(2400)
        }
        _ => 2400,
    };

    let major = count / 1000;
    let minor = (count % 1000) / 100;
    let patch = count % 100;

    Ok(format!("v{}.{}.{}-experimental", major, minor, patch))
}

#[tauri::command]
pub async fn run_mod_action(
    app: AppHandle,
    state: State<'_, AppState>,
    mod_name: String,
    action: String,
) -> Result<Value, String> {
    let mapped_action = match action.as_str() {
        "extract_pal" => "extract",
        "create_blend" => "create-blend",
        "push" => "push",
        "cook" => "cook",
        "pack" => "pack",
        "full" => "full",
        "decompile" => "decompile",
        "browse_ue" => "browse-ue",
        "browse_unreal" => "browse-ue",
        "open_source" => "open-source",
        "open_ue" => "open-ue",
        "open_pak" => "open-pak",
        other => other,
    };

    let raw = run_cli(&app, &state, &["mod", mapped_action, &mod_name])?;
    let parsed: Value = serde_json::from_str(&raw)
        .unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn unreal_ping(
    app: AppHandle,
    state: State<'_, AppState>,
) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["mod", "ping", "_"])?;
    let parsed: Value = serde_json::from_str(&raw)
        .unwrap_or(serde_json::json!({
            "unreal_running": false,
            "ini_enabled": false,
            "connection_active": false,
            "plugin_loaded": false,
            "diagnostic_code": "UNREAL_CLOSED",
            "message": "Failed to parse backend ping status."
        }));
    Ok(parsed)
}

#[tauri::command]
pub async fn audio_set(
    app: AppHandle,
    state: State<'_, AppState>,
    mod_name: String,
    cry_name: String,
    path: String,
) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["audio", "set", &mod_name, &cry_name, &path])?;
    let parsed: Value = serde_json::from_str(&raw)
        .unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn audio_clear(
    app: AppHandle,
    state: State<'_, AppState>,
    mod_name: String,
    cry_name: String,
) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["audio", "clear", &mod_name, &cry_name])?;
    let parsed: Value = serde_json::from_str(&raw)
        .unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn audio_play(
    app: AppHandle,
    state: State<'_, AppState>,
    mod_name: String,
    cry_name: String,
) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["audio", "play", &mod_name, &cry_name])?;
    let parsed: Value = serde_json::from_str(&raw)
        .unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn altermatic_toggle(
    app: AppHandle,
    state: State<'_, AppState>,
    mod_name: String,
    enabled: bool,
) -> Result<Value, String> {
    let status = if enabled { "on" } else { "off" };
    let raw = run_cli(&app, &state, &["altermatic", "toggle", &mod_name, status])?;
    let parsed: Value = serde_json::from_str(&raw)
        .unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn altermatic_metadata(
    app: AppHandle,
    state: State<'_, AppState>,
    mod_name: String,
) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["altermatic", "metadata", &mod_name])?;
    let parsed: Value = serde_json::from_str(&raw)
        .map_err(|e| format!("JSON parse error on altermatic_metadata: {}", e))?;
    Ok(parsed)
}

#[tauri::command]
pub async fn altermatic_add(
    app: AppHandle,
    state: State<'_, AppState>,
    mod_name: String,
    label: String,
    custom: bool,
    source: String,
) -> Result<Value, String> {
    let mut args = vec!["altermatic", "add", &mod_name, &label];
    if custom {
        args.push("--custom");
    }
    args.push("--source");
    args.push(&source);
    let raw = run_cli(&app, &state, &args)?;
    let parsed: Value = serde_json::from_str(&raw)
        .unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn altermatic_delete(
    app: AppHandle,
    state: State<'_, AppState>,
    mod_name: String,
    index: i32,
) -> Result<Value, String> {
    let index_str = index.to_string();
    let raw = run_cli(&app, &state, &["altermatic", "delete", &mod_name, &index_str])?;
    let parsed: Value = serde_json::from_str(&raw)
        .unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn altermatic_save(
    app: AppHandle,
    state: State<'_, AppState>,
    index: i32,
    data: String,
) -> Result<Value, String> {
    let index_str = index.to_string();
    let raw = run_cli(&app, &state, &["altermatic", "save", &index_str, "--data", &data])?;
    let parsed: Value = serde_json::from_str(&raw)
        .unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn altermatic_open_blend(
    app: AppHandle,
    state: State<'_, AppState>,
    mod_name: String,
    blend_name: String,
    category: String,
) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["altermatic", "open-blend", &mod_name, &blend_name, "--category", &category])?;
    let parsed: Value = serde_json::from_str(&raw)
        .unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn altermatic_sidecar(
    app: AppHandle,
    state: State<'_, AppState>,
    mod_name: String,
    blend_name: String,
) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["altermatic", "sidecar", &mod_name, &blend_name])?;
    let parsed: Value = serde_json::from_str(&raw)
        .map_err(|e| format!("JSON parse error on altermatic_sidecar: {}", e))?;
    Ok(parsed)
}

#[tauri::command]
pub async fn set_mod_icon(
    app: AppHandle,
    state: State<'_, AppState>,
    mod_name: String,
    path: String,
) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["mod", "set-icon", &mod_name, "--path", &path])?;
    let parsed: Value = serde_json::from_str(&raw)
        .unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn save_mod_icon_bytes(
    app: AppHandle,
    state: State<'_, AppState>,
    mod_name: String,
    filename: String,
    bytes: Vec<u8>,
) -> Result<Value, String> {
    let temp_dir = std::env::temp_dir();
    let temp_file_path = temp_dir.join(&filename);
    std::fs::write(&temp_file_path, bytes)
        .map_err(|e| format!("Failed to write temp file: {}", e))?;
    
    let path_str = temp_file_path.to_string_lossy().into_owned();
    let raw = run_cli(&app, &state, &["mod", "set-icon", &mod_name, "--path", &path_str])?;
    
    let _ = std::fs::remove_file(temp_file_path);
    
    let parsed: Value = serde_json::from_str(&raw)
        .unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn save_mod_audio_bytes(
    app: AppHandle,
    state: State<'_, AppState>,
    mod_name: String,
    cry_name: String,
    filename: String,
    bytes: Vec<u8>,
) -> Result<Value, String> {
    let temp_dir = std::env::temp_dir();
    let temp_file_path = temp_dir.join(&filename);
    std::fs::write(&temp_file_path, bytes)
        .map_err(|e| format!("Failed to write temp file: {}", e))?;
    
    let path_str = temp_file_path.to_string_lossy().into_owned();
    let raw = run_cli(&app, &state, &["audio", "set", &mod_name, &cry_name, &path_str])?;
    
    let _ = std::fs::remove_file(temp_file_path);
    
    let parsed: Value = serde_json::from_str(&raw)
        .unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn get_config(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["config", "get"])?;
    let parsed: Value = serde_json::from_str(&raw)
        .map_err(|e| format!("JSON parse error on get_config: {}", e))?;
    Ok(parsed)
}

#[tauri::command]
pub async fn set_config(
    app: AppHandle,
    state: State<'_, AppState>,
    key: String,
    value: String,
) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["config", "set", &key, &value])?;
    let parsed: Value = serde_json::from_str(&raw)
        .map_err(|e| format!("JSON parse error on set_config: {}", e))?;
    Ok(parsed)
}

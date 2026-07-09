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
    pub is_frozen: bool,
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

fn parse_last_json_line(raw: &str) -> Result<Value, String> {
    for line in raw.lines().rev() {
        if let Some(start) = line.find('{') {
            if let Some(end) = line.rfind('}') {
                if start < end {
                    let candidate = &line[start..=end];
                    if let Ok(parsed) = serde_json::from_str::<Value>(candidate) {
                        return Ok(parsed);
                    }
                }
            }
        }
    }
    serde_json::from_str(raw).map_err(|e| format!("JSON parse error: {}. Raw output: {}", e, raw))
}

fn run_cli(app: &AppHandle, state: &AppState, args: &[&str]) -> Result<String, String> {
    let args_joined = args.join(" ");
    let silence = args_joined.contains("ping")
        || args_joined.contains("config get")
        || args_joined.contains("manager list");

    let command_str;
    let mut cmd = Command::new(&state.python_exe);

    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x08000000); // CREATE_NO_WINDOW
    }

    let work_dir = if state.is_frozen {
        command_str = format!("{} {}", state.python_exe.display(), args_joined);
        cmd.args(args);
        state.python_exe.parent().unwrap()
    } else {
        command_str = format!("python {} {}", state.cli_path.display(), args_joined);
        cmd.arg(&state.cli_path);
        cmd.args(args);
        state.cli_path.parent().unwrap()
    };

    if !silence {
        emit_log(app, "INFO", &format!("Running backend command: {}", command_str));
    }

    let mut child = cmd
        .current_dir(work_dir)
        .env("PYTHONUNBUFFERED", "1")
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .spawn()
        .map_err(|e| {
            let err_msg = format!("Failed to spawn Python process: {}", e);
            if !silence { emit_log(app, "ERROR", &err_msg); }
            err_msg
        })?;

    let stdout_stream = child.stdout.take().ok_or_else(|| "Failed to pipe stdout".to_string())?;
    let stderr_stream = child.stderr.take().ok_or_else(|| "Failed to pipe stderr".to_string())?;

    let stdout_accumulator = std::sync::Arc::new(std::sync::Mutex::new(String::new()));
    let stdout_acc_clone = stdout_accumulator.clone();
    
    let app_clone = app.clone();
    let stdout_handle = thread::spawn(move || {
        let reader = BufReader::new(stdout_stream);
        for line in reader.lines() {
            if let Ok(l) = line {
                if !silence {
                    let mut is_json_log = false;
                    if let Some(start) = l.find('{') {
                        if let Some(end) = l.rfind('}') {
                            if start < end {
                                let candidate = &l[start..=end];
                                if let Ok(parsed) = serde_json::from_str::<serde_json::Value>(candidate) {
                                    is_json_log = true;
                                    if let Some(log_type) = parsed.get("type").and_then(|v| v.as_str()) {
                                        if log_type == "log" {
                                            if let Some(msg) = parsed.get("message").and_then(|v| v.as_str()) {
                                                let lvl = parsed.get("level").and_then(|v| v.as_str()).unwrap_or("INFO");
                                                emit_log(&app_clone, &lvl.to_uppercase(), msg);
                                            }
                                        }
                                    } else if let Some(msg) = parsed.get("message").and_then(|v| v.as_str()) {
                                        let is_error = parsed.get("status").and_then(|v| v.as_str()) == Some("error");
                                        emit_log(&app_clone, if is_error { "ERROR" } else { "INFO" }, msg);
                                    }
                                }
                            }
                        }
                    }
                    if !is_json_log {
                        emit_log(&app_clone, "INFO", &l);
                    }
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
                if !silence { emit_log(&app_clone2, "ERROR", &l); }
            }
        }
    });

    let status = child.wait().map_err(|e| format!("Failed to wait on child process: {}", e))?;
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
    let parsed: Value = parse_last_json_line(&raw)?;
    Ok(parsed)
}

#[tauri::command]
pub async fn creator_list(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["creator", "list"])?;
    let parsed: Value = parse_last_json_line(&raw)?;
    Ok(parsed)
}

#[tauri::command]
pub async fn creator_add(app: AppHandle, state: State<'_, AppState>, id: String, template_id: String) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["creator", "add", &id, "--template", &template_id])?;
    let parsed: Value = parse_last_json_line(&raw)?;
    Ok(parsed)
}

#[tauri::command]
pub async fn creator_save(app: AppHandle, state: State<'_, AppState>, id: String, data: String) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["creator", "update", &id, "--data", &data])?;
    let parsed: Value = parse_last_json_line(&raw)?;
    Ok(parsed)
}

#[tauri::command]
pub async fn creator_delete(app: AppHandle, state: State<'_, AppState>, id: String) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["creator", "delete", &id])?;
    let parsed: Value = parse_last_json_line(&raw)?;
    Ok(parsed)
}

#[tauri::command]
pub async fn env_status(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["env", "status"])?;
    let parsed: Value = parse_last_json_line(&raw)?;
    Ok(parsed)
}

#[tauri::command]
pub async fn env_launch_unreal(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["env", "launch-unreal"])?;
    let parsed: Value = parse_last_json_line(&raw).unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn env_restart_unreal(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["env", "restart-unreal"])?;
    let parsed: Value = parse_last_json_line(&raw).unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn get_spawners(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["manager", "get-caches"])?;
    let parsed: Value = parse_last_json_line(&raw)?;
    Ok(parsed)
}

#[tauri::command]
pub async fn get_app_version() -> Result<String, String> {
    let count_str = env!("PALBAKER_COMMIT_COUNT");
    let count = count_str.parse::<u32>().unwrap_or(2400);
    let major = count / 1000;
    let minor = (count % 1000) / 100;
    let patch = count % 100;
    Ok(format!("v{}.{}.{}-experimental", major, minor, patch))
}

#[tauri::command]
pub async fn run_mod_action(app: AppHandle, state: State<'_, AppState>, base_pal: String, mod_name: String, action: String) -> Result<Value, String> {
    let mapped_action = match action.as_str() {
        "extract_pal" => "extract",
        "create_blend" => "create-blend",
        "refresh_blend" => "refresh-blend",
        "cook_only" => "cook",
        "pack_only" => "pack",
        "browse_ue" | "browse_unreal" => "browse-ue",
        "open_source" => "open-source",
        "open_ue" => "open-ue",
        "open_pak" => "open-pak",
        other => other,
    };
    let raw = run_cli(&app, &state, &["mod", mapped_action, &base_pal, &mod_name])?;
    let parsed: Value = parse_last_json_line(&raw).unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn unreal_ping(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    // We can just ping with dummy base_pal and mod
    let raw = run_cli(&app, &state, &["mod", "ping", "PingCheck", "PingCheck"])?;
    let parsed: Value = parse_last_json_line(&raw).unwrap_or(serde_json::json!({
        "unreal_running": false, "ini_enabled": false, "connection_active": false,
        "plugin_loaded": false, "diagnostic_code": "UNREAL_CLOSED",
        "message": "Failed to parse backend ping status."
    }));
    Ok(parsed)
}

#[tauri::command]
pub async fn audio_set(app: AppHandle, state: State<'_, AppState>, base_pal: String, mod_name: String, cry_name: String, path: String) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["audio", "set", &base_pal, &mod_name, &cry_name, &path])?;
    let parsed: Value = parse_last_json_line(&raw).unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn audio_clear(app: AppHandle, state: State<'_, AppState>, base_pal: String, mod_name: String, cry_name: String) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["audio", "clear", &base_pal, &mod_name, &cry_name])?;
    let parsed: Value = parse_last_json_line(&raw).unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn audio_play(app: AppHandle, state: State<'_, AppState>, base_pal: String, mod_name: String, cry_name: String) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["audio", "play", &base_pal, &mod_name, &cry_name])?;
    let parsed: Value = parse_last_json_line(&raw).unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn altermatic_toggle(app: AppHandle, state: State<'_, AppState>, base_pal: String, mod_name: String, enabled: bool) -> Result<Value, String> {
    let status = if enabled { "on" } else { "off" };
    let raw = run_cli(&app, &state, &["altermatic", "toggle", &base_pal, &mod_name, status])?;
    let parsed: Value = parse_last_json_line(&raw).unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn altermatic_metadata(app: AppHandle, state: State<'_, AppState>, base_pal: String, mod_name: String) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["altermatic", "metadata", &base_pal, &mod_name])?;
    let parsed: Value = parse_last_json_line(&raw)?;
    Ok(parsed)
}

#[tauri::command]
pub async fn altermatic_add(app: AppHandle, state: State<'_, AppState>, base_pal: String, mod_name: String, label: String, custom: bool, source: String) -> Result<Value, String> {
    let mut args = vec!["altermatic", "add", &base_pal, &mod_name, &label];
    if custom { args.push("--custom"); }
    args.push("--source");
    args.push(&source);
    let raw = run_cli(&app, &state, &args)?;
    let parsed: Value = parse_last_json_line(&raw).unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn altermatic_delete(app: AppHandle, state: State<'_, AppState>, base_pal: String, mod_name: String, index: i32) -> Result<Value, String> {
    let index_str = index.to_string();
    let raw = run_cli(&app, &state, &["altermatic", "delete", &base_pal, &mod_name, &index_str])?;
    let parsed: Value = parse_last_json_line(&raw).unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn altermatic_save(app: AppHandle, state: State<'_, AppState>, index: i32, data: String) -> Result<Value, String> {
    let index_str = index.to_string();
    let raw = run_cli(&app, &state, &["altermatic", "save", &index_str, "--data", &data])?;
    let parsed: Value = parse_last_json_line(&raw).unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn altermatic_open_blend(app: AppHandle, state: State<'_, AppState>, base_pal: String, mod_name: String, blend_name: String, category: String) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["altermatic", "open-blend", &base_pal, &mod_name, &blend_name, "--category", &category])?;
    let parsed: Value = parse_last_json_line(&raw).unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn altermatic_sidecar(app: AppHandle, state: State<'_, AppState>, base_pal: String, mod_name: String, blend_name: String) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["altermatic", "sidecar", &base_pal, &mod_name, &blend_name])?;
    let parsed: Value = parse_last_json_line(&raw)?;
    Ok(parsed)
}

#[tauri::command]
pub async fn set_mod_icon(app: AppHandle, state: State<'_, AppState>, base_pal: String, mod_name: String, path: String) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["mod", "set-icon", &base_pal, &mod_name, "--path", &path])?;
    let parsed: Value = parse_last_json_line(&raw).unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn save_mod_icon_bytes(app: AppHandle, state: State<'_, AppState>, base_pal: String, mod_name: String, filename: String, bytes: Vec<u8>) -> Result<Value, String> {
    let temp_dir = std::env::temp_dir();
    let temp_file_path = temp_dir.join(&filename);
    std::fs::write(&temp_file_path, bytes).map_err(|e| format!("Failed to write temp file: {}", e))?;
    let path_str = temp_file_path.to_string_lossy().into_owned();
    let raw = run_cli(&app, &state, &["mod", "set-icon", &base_pal, &mod_name, "--path", &path_str])?;
    let _ = std::fs::remove_file(temp_file_path);
    let parsed: Value = parse_last_json_line(&raw).unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn save_mod_audio_bytes(app: AppHandle, state: State<'_, AppState>, base_pal: String, mod_name: String, cry_name: String, filename: String, bytes: Vec<u8>) -> Result<Value, String> {
    let temp_dir = std::env::temp_dir();
    let temp_file_path = temp_dir.join(&filename);
    std::fs::write(&temp_file_path, bytes).map_err(|e| format!("Failed to write temp file: {}", e))?;
    let path_str = temp_file_path.to_string_lossy().into_owned();
    let raw = run_cli(&app, &state, &["audio", "set", &base_pal, &mod_name, &cry_name, &path_str])?;
    let _ = std::fs::remove_file(temp_file_path);
    let parsed: Value = parse_last_json_line(&raw).unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn set_mod_preserve_materials(app: AppHandle, state: State<'_, AppState>, base_pal: String, mod_name: String, enabled: bool) -> Result<Value, String> {
    let status = if enabled { "true" } else { "false" };
    let raw = run_cli(&app, &state, &["mod", "set-preserve-materials", &base_pal, &mod_name, "--path", status])?;
    let parsed: Value = parse_last_json_line(&raw).unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn get_config(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["config", "get"])?;
    let parsed: Value = parse_last_json_line(&raw)?;
    Ok(parsed)
}

#[tauri::command]
pub async fn set_config(app: AppHandle, state: State<'_, AppState>, key: String, value: String) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["config", "set", &key, &value])?;
    let parsed: Value = parse_last_json_line(&raw)?;
    Ok(parsed)
}

#[tauri::command]
pub async fn ue4ss_manage(app: AppHandle, state: State<'_, AppState>, action: String) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["env", "ue4ss-install", "--action", &action])?;
    let parsed: Value = parse_last_json_line(&raw).unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command] 
pub async fn palschema_manage(app: AppHandle, state: State<'_, AppState>, action: String) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["env", "palschema-install", "--action", &action])?;
    let parsed: Value = parse_last_json_line(&raw).unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn cpp_plugin_manage(app: AppHandle, state: State<'_, AppState>, action: String) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["env", "install-plugin", "--action", &action])?;
    let parsed: Value = parse_last_json_line(&raw).unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn creator_refresh_bp(app: AppHandle, state: State<'_, AppState>, id: String) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["creator", "refresh-bp", &id])?;
    let parsed: Value = parse_last_json_line(&raw).unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn manager_build_db(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["manager", "build-db"])?;
    let parsed: Value = parse_last_json_line(&raw).unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn env_verify(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["env", "verify"])?;
    let parsed: Value = parse_last_json_line(&raw).unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn env_enable_remote_exec(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["env", "enable-remote-exec"])?;
    let parsed: Value = parse_last_json_line(&raw).unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn env_autodetect(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["env", "autodetect"])?;
    let parsed: Value = parse_last_json_line(&raw)?;
    Ok(parsed)
}

#[tauri::command]
pub async fn env_inject_assets(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["env", "inject-assets"])?;
    let parsed: Value = parse_last_json_line(&raw).unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn set_vanilla_replacer(app: AppHandle, state: State<'_, AppState>, base_pal: String, variant_name: String) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["mod", "set-vanilla-replacer", &base_pal, &variant_name])?;
    let parsed: Value = parse_last_json_line(&raw).unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}

#[tauri::command]
pub async fn env_extract_icons(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["env", "extract-icons"])?;
    let parsed: Value = parse_last_json_line(&raw).unwrap_or(serde_json::json!({ "status": "success", "message": raw }));
    Ok(parsed)
}
// palbaker-ui/src-tauri/src/commands.rs
use std::process::Command;
use std::path::PathBuf;
use std::io::{BufRead, BufReader};
use std::sync::Arc;
use std::thread;
use std::time::Duration;
use tauri::{State, Emitter, AppHandle};
use serde_json::{json, Value};

const SERVER_BASE: &str = "http://127.0.0.1:5842";

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
    let _ = app.emit("console_log", LogPayload {
        level: level.to_string(),
        msg: msg.to_string(),
    });
}

fn parse_last_json_line(raw: &str) -> Result<Value, String> {
    for line in raw.lines().rev() {
        if let Some(start) = line.find('{') {
            if let Some(end) = line.rfind('}') {
                if start < end {
                    if let Ok(parsed) = serde_json::from_str::<Value>(&line[start..=end]) {
                        return Ok(parsed);
                    }
                }
            }
        }
    }
    serde_json::from_str(raw).map_err(|e| format!("JSON parse error: {}. Raw: {}", e, raw))
}

// ── Ureq agent with timeouts ──

fn make_agent() -> ureq::Agent {
    let config = ureq::config::Config::builder()
        .timeout_global(Some(Duration::from_secs(30)))
        .build();
    ureq::Agent::new_with_config(config)
}

fn server_is_running(agent: &ureq::Agent) -> bool {
    match agent.get(&format!("{}/health", SERVER_BASE)).call() {
        Ok(r) => r.status() == 200,
        Err(_) => false,
    }
}

fn start_server_background(app: &AppHandle, state: &AppState) {
    let agent = make_agent();
    if server_is_running(&agent) { return; }

    let cli_path = state.cli_path.clone();
    let python_exe = state.python_exe.clone();
    let is_frozen = state.is_frozen;
    let app_clone = app.clone();

    thread::spawn(move || {
        let mut cmd = Command::new(&python_exe);
        #[cfg(target_os = "windows")]
        {
            use std::os::windows::process::CommandExt;
            cmd.creation_flags(0x08000000);
        }
        if is_frozen {
            cmd.arg("--serve");
        } else {
            cmd.arg(&cli_path).arg("--serve");
        }
        cmd.env("PYTHONUNBUFFERED", "1");
        let _ = cmd.spawn();

        // Poll for server readiness
        let agent = make_agent();
        for _ in 0..20 {
            thread::sleep(Duration::from_millis(500));
            if server_is_running(&agent) {
                emit_log(&app_clone, "INFO", "CLI daemon server started");
                return;
            }
        }
        emit_log(&app_clone, "WARN", "CLI daemon server failed to start");
    });

    // Wait for server
    let agent = make_agent();
    for _ in 0..20 {
        thread::sleep(Duration::from_millis(500));
        if server_is_running(&agent) { return; }
    }
}

/// Try to run a command through the CLI server. Returns Some(result) if
/// the server handled it, None if the server isn't available.
fn try_server_run(app: &AppHandle, args: &[&str]) -> Option<Result<String, String>> {
    let agent = make_agent();

    if !server_is_running(&agent) {
        return None;
    }

    let command = args.first().unwrap_or(&"");
    let action = if args.len() > 1 { Some(args[1]) } else { None };
    let extra_args: Vec<&str> = if args.len() > 2 { args[2..].to_vec() } else { vec![] };

    let payload = json!({
        "command": command,
        "action": action,
        "args": extra_args,
    });

    // Submit
    let mut submit_resp = match agent.post(&format!("{}/submit", SERVER_BASE))
        .header("Content-Type", "application/json")
        .send_json(&payload)
    {
        Ok(r) => r,
        Err(e) => return Some(Err(format!("Submit failed: {}", e))),
    };

    let submit_body_str = match submit_resp.body_mut().read_to_string() {
        Ok(s) => s,
        Err(e) => return Some(Err(format!("Submit body read: {}", e))),
    };
    let submit_body: Value = match serde_json::from_str(&submit_body_str) {
        Ok(v) => v,
        Err(e) => return Some(Err(format!("Submit parse failed: {}", e))),
    };

    let task_id = match submit_body["task_id"].as_str() {
        Some(id) => id.to_string(),
        None => return Some(Err("No task_id in response".to_string())),
    };

    // Poll
    let poll_url = format!("{}/tasks/{}", SERVER_BASE, task_id);
    let mut last_output_count = 0;

    loop {
        thread::sleep(Duration::from_millis(500));

        let task: Value = match agent.get(&poll_url).call() {
            Ok(mut r) => {
                match r.body_mut().read_to_string() {
                    Ok(body_str) => match serde_json::from_str(&body_str) {
                        Ok(v) => v,
                        Err(e) => return Some(Err(format!("Poll parse failed: {}", e))),
                    },
                    Err(e) => return Some(Err(format!("Poll body read: {}", e))),
                }
            },
            Err(e) => return Some(Err(format!("Poll failed: {}", e))),
        };

        // Emit new output lines
        if let Some(output) = task["output"].as_array() {
            while last_output_count < output.len() {
                let line = &output[last_output_count];
                last_output_count += 1;

                if let Some(msg_type) = line["type"].as_str() {
                    match msg_type {
                        "log" => {
                            let level = line["level"].as_str().unwrap_or("INFO");
                            let msg = line["message"].as_str().unwrap_or("");
                            emit_log(app, &level.to_uppercase(), msg);
                        }
                        "progress" => {
                            let msg = line["message"].as_str().unwrap_or("");
                            let pct = line["progress"].as_f64().unwrap_or(0.0) * 100.0;
                            emit_log(app, "INFO", &format!("[{:.0}%] {}", pct, msg));
                        }
                        "result" => {
                            let msg = line["message"].as_str().unwrap_or("");
                            let is_err = matches!(
                                line["status"].as_str(),
                                Some("error") | Some("timeout")
                            );
                            emit_log(app, if is_err { "ERROR" } else { "SUCCESS" }, msg);
                        }
                        _ => {}
                    }
                } else {
                    let msg = serde_json::to_string(line).unwrap_or_default();
                    emit_log(app, "INFO", &msg);
                }
            }
        }

        match task["status"].as_str() {
            Some("completed") => {
                let output = task["output"].as_array().cloned().unwrap_or_default();
                if let Some(last) = output.last() {
                    if last.get("type").is_some() {
                        return Some(Ok(serde_json::to_string(last).unwrap_or_default()));
                    }
                }
                return Some(Ok(task["result"].to_string()));
            }
            Some("failed") => {
                let error = task["error"].as_str().unwrap_or("Unknown error");
                return Some(Err(error.to_string()));
            }
            Some("cancelled") => return Some(Err("Task cancelled".to_string())),
            Some("timed_out") => {
                let error = task["error"].as_str().unwrap_or("Task timed out");
                return Some(Err(error.to_string()));
            }
            _ => continue,
        }
    }
}

// ── Main CLI runner ──

fn run_cli(app: &AppHandle, state: &AppState, args: &[&str]) -> Result<String, String> {
    let args_joined = args.join(" ");
    let silence = args_joined.contains("ping")
        || args_joined.contains("config get")
        || args_joined.contains("manager list");

    if !silence {
        emit_log(app, "INFO", &format!("Running: {}", args_joined));
    }

    // ── Try server mode first ──
    if try_server_run(app, args).is_some() {
        return try_server_run(app, args).unwrap();
    }

    // Server not running — start it and retry
    start_server_background(app, state);
    if let Some(result) = try_server_run(app, args) {
        return result;
    }

    // ── Fallback: direct subprocess ──
    if !silence {
        emit_log(app, "WARN", "Server unavailable, running directly");
    }
    run_cli_direct(app, state, args, silence)
}

fn run_cli_direct(app: &AppHandle, state: &AppState, args: &[&str], silence: bool) -> Result<String, String> {
    let args_joined = args.join(" ");
    let command_str = format!("{} {}", state.cli_path.display(), args_joined);

    let mut cmd = Command::new(&state.python_exe);
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x08000000);
    }

    let work_dir = if state.is_frozen {
        cmd.args(args);
        state.python_exe.parent().unwrap()
    } else {
        cmd.arg(&state.cli_path);
        cmd.args(args);
        state.cli_path.parent().unwrap()
    };

    let mut child = cmd
        .current_dir(work_dir)
        .env("PYTHONUNBUFFERED", "1")
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .spawn()
        .map_err(|e| {
            let err_msg = format!("Failed to spawn Python: {}", e);
            if !silence { emit_log(app, "ERROR", &err_msg); }
            err_msg
        })?;

    let stdout_stream = child.stdout.take().ok_or("Failed to pipe stdout")?;
    let stderr_stream = child.stderr.take().ok_or("Failed to pipe stderr")?;
    let accumulator = Arc::new(std::sync::Mutex::new(String::new()));
    let acc_clone = accumulator.clone();

    let app_c = app.clone();
    let stdout_handle = thread::spawn(move || {
        let reader = BufReader::new(stdout_stream);
        for line in reader.lines().flatten() {
            let mut is_json = false;
            if let Some(s) = line.find('{') {
                if let Some(e) = line.rfind('}') {
                    if s < e {
                        if let Ok(parsed) = serde_json::from_str::<Value>(&line[s..=e]) {
                            is_json = true;
                            if let Some(t) = parsed.get("type").and_then(|v| v.as_str()) {
                                if t == "log" {
                                    if let Some(msg) = parsed.get("message").and_then(|v| v.as_str()) {
                                        let lvl = parsed.get("level").and_then(|v| v.as_str()).unwrap_or("INFO");
                                        emit_log(&app_c, &lvl.to_uppercase(), msg);
                                    }
                                }
                            } else if let Some(msg) = parsed.get("message").and_then(|v| v.as_str()) {
                                let is_err = parsed.get("status").and_then(|v| v.as_str()) == Some("error");
                                emit_log(&app_c, if is_err { "ERROR" } else { "INFO" }, msg);
                            }
                        }
                    }
                }
            }
            if !is_json { emit_log(&app_c, "INFO", &line); }
            if let Ok(mut a) = acc_clone.lock() { a.push_str(&line); a.push('\n'); }
        }
    });

    let app_c2 = app.clone();
    let stderr_handle = thread::spawn(move || {
        BufReader::new(stderr_stream)
            .lines()
            .flatten()
            .for_each(|l| emit_log(&app_c2, "ERROR", &l));
    });

    let status = child.wait().map_err(|e| format!("Wait failed: {}", e))?;
    let _ = stdout_handle.join();
    let _ = stderr_handle.join();

    let stdout_str = accumulator.lock().map_err(|e| format!("Lock: {}", e))?.clone();

    if !status.success() {
        let err_msg = format!("CLI exited with code {}", status.code().unwrap_or(-1));
        if !silence { emit_log(app, "ERROR", &err_msg); }
        let trimmed = stdout_str.trim();
        if !trimmed.is_empty() { return Err(trimmed.to_string()); }
        return Err(err_msg);
    }

    if !silence {
        emit_log(app, "SUCCESS", &format!("Completed: {}", command_str));
    }
    Ok(stdout_str)
}


// ══════════════════════════════════════════════════════════
// Tauri Commands
// ══════════════════════════════════════════════════════════

#[tauri::command]
pub async fn manager_list(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    parse_last_json_line(&run_cli(&app, &state, &["manager", "list", "--show-unextracted"])?)
}

#[tauri::command]
pub async fn creator_list(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    parse_last_json_line(&run_cli(&app, &state, &["creator", "list"])?)
}

#[tauri::command]
pub async fn creator_add(app: AppHandle, state: State<'_, AppState>, id: String, template_id: String) -> Result<Value, String> {
    parse_last_json_line(&run_cli(&app, &state, &["creator", "add", &id, "--template", &template_id])?)
}

#[tauri::command]
pub async fn creator_save(app: AppHandle, state: State<'_, AppState>, id: String, data: String) -> Result<Value, String> {
    parse_last_json_line(&run_cli(&app, &state, &["creator", "update", &id, "--data", &data])?)
}

#[tauri::command]
pub async fn creator_delete(app: AppHandle, state: State<'_, AppState>, id: String) -> Result<Value, String> {
    parse_last_json_line(&run_cli(&app, &state, &["creator", "delete", &id])?)
}

#[tauri::command]
pub async fn env_status(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    parse_last_json_line(&run_cli(&app, &state, &["env", "status"])?)
}

#[tauri::command]
pub async fn env_launch_unreal(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["env", "launch-unreal"])?;
    Ok(parse_last_json_line(&raw).unwrap_or(json!({ "status": "success", "message": raw })))
}

#[tauri::command]
pub async fn env_restart_unreal(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["env", "restart-unreal"])?;
    Ok(parse_last_json_line(&raw).unwrap_or(json!({ "status": "success", "message": raw })))
}

#[tauri::command]
pub async fn get_spawners(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    parse_last_json_line(&run_cli(&app, &state, &["manager", "get-caches"])?)
}

#[tauri::command]
pub async fn get_app_version() -> Result<String, String> {
    let count_str = env!("PALBAKER_COMMIT_COUNT");
    let count = count_str.parse::<u32>().unwrap_or(2400);
    Ok(format!("v{}.{:02}.{}-experimental", count / 1000, (count % 1000) / 100, count % 100))
}

#[tauri::command]
pub async fn run_mod_action(app: AppHandle, state: State<'_, AppState>, mod_name: String, action: String) -> Result<Value, String> {
    let mapped = match action.as_str() {
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
    let raw = run_cli(&app, &state, &["mod", mapped, &mod_name])?;
    Ok(parse_last_json_line(&raw).unwrap_or(json!({ "status": "success", "message": raw })))
}

#[tauri::command]
pub async fn unreal_ping(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["mod", "ping", "_"])?;
    Ok(parse_last_json_line(&raw).unwrap_or(json!({
        "unreal_running": false, "ini_enabled": false, "connection_active": false,
        "plugin_loaded": false, "diagnostic_code": "UNREAL_CLOSED",
        "message": "Failed to parse backend ping status."
    })))
}

#[tauri::command]
pub async fn audio_set(app: AppHandle, state: State<'_, AppState>, mod_name: String, cry_name: String, path: String) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["audio", "set", &mod_name, &cry_name, &path])?;
    Ok(parse_last_json_line(&raw).unwrap_or(json!({ "status": "success", "message": raw })))
}

#[tauri::command]
pub async fn audio_clear(app: AppHandle, state: State<'_, AppState>, mod_name: String, cry_name: String) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["audio", "clear", &mod_name, &cry_name])?;
    Ok(parse_last_json_line(&raw).unwrap_or(json!({ "status": "success", "message": raw })))
}

#[tauri::command]
pub async fn audio_play(app: AppHandle, state: State<'_, AppState>, mod_name: String, cry_name: String) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["audio", "play", &mod_name, &cry_name])?;
    Ok(parse_last_json_line(&raw).unwrap_or(json!({ "status": "success", "message": raw })))
}

#[tauri::command]
pub async fn altermatic_toggle(app: AppHandle, state: State<'_, AppState>, mod_name: String, enabled: bool) -> Result<Value, String> {
    let s = if enabled { "on" } else { "off" };
    let raw = run_cli(&app, &state, &["altermatic", "toggle", &mod_name, s])?;
    Ok(parse_last_json_line(&raw).unwrap_or(json!({ "status": "success", "message": raw })))
}

#[tauri::command]
pub async fn altermatic_metadata(app: AppHandle, state: State<'_, AppState>, mod_name: String) -> Result<Value, String> {
    parse_last_json_line(&run_cli(&app, &state, &["altermatic", "metadata", &mod_name])?)
}

#[tauri::command]
pub async fn altermatic_add(app: AppHandle, state: State<'_, AppState>, mod_name: String, label: String, custom: bool, source: String) -> Result<Value, String> {
    let mut args = vec!["altermatic", "add", &mod_name, &label];
    if custom { args.push("--custom"); }
    args.push("--source");
    args.push(&source);
    let raw = run_cli(&app, &state, &args)?;
    Ok(parse_last_json_line(&raw).unwrap_or(json!({ "status": "success", "message": raw })))
}

#[tauri::command]
pub async fn altermatic_delete(app: AppHandle, state: State<'_, AppState>, mod_name: String, index: i32) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["altermatic", "delete", &mod_name, &index.to_string()])?;
    Ok(parse_last_json_line(&raw).unwrap_or(json!({ "status": "success", "message": raw })))
}

#[tauri::command]
pub async fn altermatic_save(app: AppHandle, state: State<'_, AppState>, index: i32, data: String) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["altermatic", "save", &index.to_string(), "--data", &data])?;
    Ok(parse_last_json_line(&raw).unwrap_or(json!({ "status": "success", "message": raw })))
}

#[tauri::command]
pub async fn altermatic_open_blend(app: AppHandle, state: State<'_, AppState>, mod_name: String, blend_name: String, category: String) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["altermatic", "open-blend", &mod_name, &blend_name, "--category", &category])?;
    Ok(parse_last_json_line(&raw).unwrap_or(json!({ "status": "success", "message": raw })))
}

#[tauri::command]
pub async fn altermatic_sidecar(app: AppHandle, state: State<'_, AppState>, mod_name: String, blend_name: String) -> Result<Value, String> {
    parse_last_json_line(&run_cli(&app, &state, &["altermatic", "sidecar", &mod_name, &blend_name])?)
}

#[tauri::command]
pub async fn set_mod_icon(app: AppHandle, state: State<'_, AppState>, mod_name: String, path: String) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["mod", "set-icon", &mod_name, "--path", &path])?;
    Ok(parse_last_json_line(&raw).unwrap_or(json!({ "status": "success", "message": raw })))
}

#[tauri::command]
pub async fn save_mod_icon_bytes(app: AppHandle, state: State<'_, AppState>, mod_name: String, filename: String, bytes: Vec<u8>) -> Result<Value, String> {
    let temp = std::env::temp_dir().join(&filename);
    std::fs::write(&temp, bytes).map_err(|e| format!("Temp write: {}", e))?;
    let p = temp.to_string_lossy().into_owned();
    let raw = run_cli(&app, &state, &["mod", "set-icon", &mod_name, "--path", &p])?;
    let _ = std::fs::remove_file(&temp);
    Ok(parse_last_json_line(&raw).unwrap_or(json!({ "status": "success", "message": raw })))
}

#[tauri::command]
pub async fn save_mod_audio_bytes(app: AppHandle, state: State<'_, AppState>, mod_name: String, cry_name: String, filename: String, bytes: Vec<u8>) -> Result<Value, String> {
    let temp = std::env::temp_dir().join(&filename);
    std::fs::write(&temp, bytes).map_err(|e| format!("Temp write: {}", e))?;
    let p = temp.to_string_lossy().into_owned();
    let raw = run_cli(&app, &state, &["audio", "set", &mod_name, &cry_name, &p])?;
    let _ = std::fs::remove_file(&temp);
    Ok(parse_last_json_line(&raw).unwrap_or(json!({ "status": "success", "message": raw })))
}

#[tauri::command]
pub async fn get_config(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    parse_last_json_line(&run_cli(&app, &state, &["config", "get"])?)
}

#[tauri::command]
pub async fn set_config(app: AppHandle, state: State<'_, AppState>, key: String, value: String) -> Result<Value, String> {
    parse_last_json_line(&run_cli(&app, &state, &["config", "set", &key, &value])?)
}

#[tauri::command]
pub async fn ue4ss_manage(app: AppHandle, state: State<'_, AppState>, action: String) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["env", "ue4ss-install", "--action", &action])?;
    Ok(parse_last_json_line(&raw).unwrap_or(json!({ "status": "success", "message": raw })))
}

#[tauri::command]
pub async fn palschema_manage(app: AppHandle, state: State<'_, AppState>, action: String) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["env", "palschema-install", "--action", &action])?;
    Ok(parse_last_json_line(&raw).unwrap_or(json!({ "status": "success", "message": raw })))
}

#[tauri::command]
pub async fn cpp_plugin_manage(app: AppHandle, state: State<'_, AppState>, action: String) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["env", "install-plugin", "--action", &action])?;
    Ok(parse_last_json_line(&raw).unwrap_or(json!({ "status": "success", "message": raw })))
}

#[tauri::command]
pub async fn creator_refresh_bp(app: AppHandle, state: State<'_, AppState>, id: String) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["creator", "refresh-bp", &id])?;
    Ok(parse_last_json_line(&raw).unwrap_or(json!({ "status": "success", "message": raw })))
}

#[tauri::command]
pub async fn manager_build_db(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["manager", "build-db"])?;
    Ok(parse_last_json_line(&raw).unwrap_or(json!({ "status": "success", "message": raw })))
}

#[tauri::command]
pub async fn env_verify(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["env", "verify"])?;
    Ok(parse_last_json_line(&raw).unwrap_or(json!({ "status": "success", "message": raw })))
}

#[tauri::command]
pub async fn env_enable_remote_exec(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["env", "enable-remote-exec"])?;
    Ok(parse_last_json_line(&raw).unwrap_or(json!({ "status": "success", "message": raw })))
}

#[tauri::command]
pub async fn env_autodetect(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    parse_last_json_line(&run_cli(&app, &state, &["env", "autodetect"])?)
}

#[tauri::command]
pub async fn env_inject_assets(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["env", "inject-assets"])?;
    Ok(parse_last_json_line(&raw).unwrap_or(json!({ "status": "success", "message": raw })))
}

#[tauri::command]
pub async fn env_extract_icons(app: AppHandle, state: State<'_, AppState>) -> Result<Value, String> {
    let raw = run_cli(&app, &state, &["env", "extract-icons"])?;
    Ok(parse_last_json_line(&raw).unwrap_or(json!({ "status": "success", "message": raw })))
}

#[tauri::command]
pub async fn set_mod_preserve_materials(app: AppHandle, state: State<'_, AppState>, mod_name: String, enabled: bool) -> Result<Value, String> {
    let v = if enabled { "true" } else { "false" };
    let raw = run_cli(&app, &state, &["mod", "set-preserve-materials", &mod_name, "--path", v])?;
    Ok(parse_last_json_line(&raw).unwrap_or(json!({ "status": "success", "message": raw })))
}

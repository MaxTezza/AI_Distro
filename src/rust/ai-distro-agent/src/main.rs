use std::collections::HashMap;
use std::collections::hash_map::DefaultHasher;
use std::fs::{self, OpenOptions};
use std::hash::{Hash, Hasher};
use std::io::{self, BufRead, Write};
use std::os::unix::fs::PermissionsExt;
use std::os::unix::net::UnixListener;
use std::path::Path;
use std::process::Command;
use std::sync::{Mutex, OnceLock};
use std::time::{SystemTime, UNIX_EPOCH};
use std::{thread, time::Duration};
use ai_distro_common::{
    evaluate_policy_with_payload, init_logging_with_config, load_policy, load_typed_config,
    ActionRequest, ActionResponse, AgentConfig, Capabilities, PolicyDecision, PendingConfirmation,
};


#[derive(Debug, Clone, Copy)]
enum Action {
    PackageInstall,
    SystemUpdate,
    ReadContext,
    GetCapabilities,
    Ping,
}

impl Action {
    fn as_str(&self) -> &'static str {
        match self {
            Action::PackageInstall => "package_install",
            Action::SystemUpdate => "system_update",
            Action::ReadContext => "read_context",
            Action::GetCapabilities => "get_capabilities",
            Action::Ping => "ping",
        }
    }
}

type Handler = fn(&ActionRequest) -> ActionResponse;
static RATE_LIMIT_BUCKETS: OnceLock<Mutex<HashMap<String, Vec<u64>>>> = OnceLock::new();
static AUDIT_CHAIN_STATE: OnceLock<Mutex<Option<AuditChainState>>> = OnceLock::new();

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
struct AuditChainState {
    seq: u64,
    last_hash: String,
}

fn action_registry() -> HashMap<&'static str, Handler> {
    let mut map: HashMap<&'static str, Handler> = HashMap::new();
    map.insert("package_install", handle_package_install as Handler);
    map.insert("system_update", handle_system_update as Handler);
    map.insert("read_context", handle_read_context as Handler);
    map.insert("get_capabilities", handle_get_capabilities as Handler);
    map.insert("ping", handle_ping as Handler);
    map.insert("open_url", handle_open_url as Handler);
    map.insert("open_app", handle_open_app as Handler);
    map.insert("set_volume", handle_set_volume as Handler);
    map.insert("set_brightness", handle_set_brightness as Handler);
    map.insert("network_wifi_on", handle_wifi_on as Handler);
    map.insert("network_wifi_off", handle_wifi_off as Handler);
    map.insert("network_bluetooth_on", handle_bluetooth_on as Handler);
    map.insert("network_bluetooth_off", handle_bluetooth_off as Handler);
    map.insert("power_reboot", handle_power_reboot as Handler);
    map.insert("power_shutdown", handle_power_shutdown as Handler);
    map.insert("power_sleep", handle_power_sleep as Handler);
    map.insert("remember", handle_remember as Handler);
    map.insert("list_files", handle_list_files as Handler);
    map.insert("weather_get", handle_weather_get as Handler);
    map.insert("calendar_add_event", handle_calendar_add_event as Handler);
    map.insert("calendar_list_day", handle_calendar_list_day as Handler);
    map.insert("email_inbox_summary", handle_email_inbox_summary as Handler);
    map.insert("email_search", handle_email_search as Handler);
    map.insert("email_draft", handle_email_draft as Handler);
    map.insert("plan_day_outfit", handle_plan_day_outfit as Handler);
    map.insert("unknown", handle_unknown as Handler);
    map
}

fn handle_list_files(req: &ActionRequest) -> ActionResponse {
    log::info!("handler: list_files, payload={:?}", req.payload);
    let path = req.payload.as_deref().unwrap_or(".");
    match fs::read_dir(path) {
        Ok(entries) => {
            let files: Vec<String> = entries
                .filter_map(|entry| {
                    entry.ok().and_then(|e| {
                        e.path()
                            .file_name()
                            .and_then(|n| n.to_str().map(|s| s.to_string()))
                    })
                })
                .collect();
            ok_response(&req.name, &files.join("\n"))
        }
        Err(err) => error_response(&req.name, &format!("failed to list files: {}", err)),
    }
}

fn handle_package_install(req: &ActionRequest) -> ActionResponse {
    log::info!("handler: package_install, payload={:?}", req.payload);
    let Some(payload) = req.payload.as_deref() else {
        return error_response(&req.name, "missing package list");
    };
    let packages: Vec<&str> = payload
        .split(',')
        .map(|s| s.trim())
        .filter(|s| !s.is_empty())
        .collect();
    if packages.is_empty() {
        return error_response(&req.name, "empty package list");
    }
    if packages.len() > 20 {
        return error_response(&req.name, "too many packages requested");
    }
    if packages.iter().any(|pkg| !is_valid_package_name(pkg)) {
        return error_response(&req.name, "invalid package name");
    }

    let mut args = vec!["install", "-y"];
    args.extend(packages.iter().copied());
    match run_command("apt-get", &args, Some(&[("DEBIAN_FRONTEND", "noninteractive")])) {
        Ok(_) => ok_response(&req.name, "Packages installed."),
        Err(err) => error_response(&req.name, &err),
    }
}

fn handle_system_update(req: &ActionRequest) -> ActionResponse {
    log::info!("handler: system_update, payload={:?}", req.payload);
    let env = Some(&[("DEBIAN_FRONTEND", "noninteractive")][..]);
    if let Err(err) = run_command("apt-get", &["update"], env) {
        return error_response(&req.name, &err);
    }
    match run_command("apt-get", &["upgrade", "-y"], env) {
        Ok(_) => ok_response(&req.name, "System updated."),
        Err(err) => error_response(&req.name, &err),
    }
}

fn handle_read_context(req: &ActionRequest) -> ActionResponse {
    log::info!("handler: read_context, payload={:?}", req.payload);
    let notes = read_recent_notes(5).unwrap_or_else(|_| Vec::new());
    if notes.is_empty() {
        return ok_response(&req.name, "No saved context yet.");
    }
    let summary = notes.join(" | ");
    ok_response(&req.name, &format!("Recent context: {summary}"))
}

fn handle_get_capabilities(req: &ActionRequest) -> ActionResponse {
    log::info!("handler: get_capabilities (stub)");
    ActionResponse {
        version: 1,
        action: req.name.clone(),
        status: "ok".to_string(),
        message: None,
        capabilities: Some(Capabilities {
            ipc_version: 1,
            actions: vec![
                "package_install".to_string(),
                "system_update".to_string(),
                "read_context".to_string(),
                "get_capabilities".to_string(),
                "confirm".to_string(),
                "ping".to_string(),
                "open_url".to_string(),
                "open_app".to_string(),
                "set_volume".to_string(),
                "set_brightness".to_string(),
                "network_wifi_on".to_string(),
                "network_wifi_off".to_string(),
                "network_bluetooth_on".to_string(),
                "network_bluetooth_off".to_string(),
                "power_reboot".to_string(),
                "power_shutdown".to_string(),
                "power_sleep".to_string(),
                "remember".to_string(),
                "list_files".to_string(),
                "weather_get".to_string(),
                "calendar_add_event".to_string(),
                "calendar_list_day".to_string(),
                "email_inbox_summary".to_string(),
                "email_search".to_string(),
                "email_draft".to_string(),
                "plan_day_outfit".to_string(),
            ],
            protocol_version: 1,
        }),
        confirmation_id: None,
    }
}

fn handle_ping(req: &ActionRequest) -> ActionResponse {
    log::info!("handler: ping");
    ActionResponse {
        version: 1,
        action: req.name.clone(),
        status: "ok".to_string(),
        message: Some("pong".to_string()),
        capabilities: None,
        confirmation_id: None,
    }
}

fn handle_open_url(req: &ActionRequest) -> ActionResponse {
    let Some(url) = req.payload.as_deref() else {
        return error_response(&req.name, "missing url");
    };
    if !is_safe_http_url(url) {
        return error_response(&req.name, "unsupported or unsafe url");
    }
    match run_command("xdg-open", &[url], None) {
        Ok(_) => ok_response(&req.name, "Opening browser."),
        Err(err) => error_response(&req.name, &err),
    }
}

fn handle_open_app(req: &ActionRequest) -> ActionResponse {
    let Some(app) = req.payload.as_deref() else {
        return error_response(&req.name, "missing app name");
    };
    if !is_valid_app_name(app) {
        return error_response(&req.name, "invalid app name");
    }
    if command_exists("gtk-launch") {
        return match run_command("gtk-launch", &[app], None) {
            Ok(_) => ok_response(&req.name, "Launching app."),
            Err(err) => error_response(&req.name, &err),
        };
    }
    if command_exists("kstart5") {
        return match run_command("kstart5", &[app], None) {
            Ok(_) => ok_response(&req.name, "Launching app."),
            Err(err) => error_response(&req.name, &err),
        };
    }
    match run_command("xdg-open", &[app], None) {
        Ok(_) => ok_response(&req.name, "Launching app."),
        Err(err) => error_response(&req.name, &err),
    }
}

fn handle_set_volume(req: &ActionRequest) -> ActionResponse {
    let Some(volume) = req.payload.as_deref() else {
        return error_response(&req.name, "missing volume percentage");
    };
    let Some(parsed) = parse_percent_value(volume) else {
        return error_response(&req.name, "invalid volume percentage");
    };
    if !command_exists("pactl") {
        return error_response(&req.name, "pactl not available");
    }
    let arg = format!("{parsed}%");
    match run_command("pactl", &["set-sink-volume", "@DEFAULT_SINK@", &arg], None) {
        Ok(_) => ok_response(&req.name, "Volume updated."),
        Err(err) => error_response(&req.name, &err),
    }
}

fn handle_set_brightness(req: &ActionRequest) -> ActionResponse {
    let Some(level) = req.payload.as_deref() else {
        return error_response(&req.name, "missing brightness percentage");
    };
    let Some(parsed) = parse_percent_value(level) else {
        return error_response(&req.name, "invalid brightness percentage");
    };
    if command_exists("brightnessctl") {
        let arg = format!("{parsed}%");
        return match run_command("brightnessctl", &["set", &arg], None) {
            Ok(_) => ok_response(&req.name, "Brightness updated."),
            Err(err) => error_response(&req.name, &err),
        };
    }
    error_response(&req.name, "brightnessctl not available")
}

fn handle_wifi_on(req: &ActionRequest) -> ActionResponse {
    match run_command("nmcli", &["radio", "wifi", "on"], None) {
        Ok(_) => ok_response(&req.name, "Wi-Fi enabled."),
        Err(err) => error_response(&req.name, &err),
    }
}

fn handle_wifi_off(req: &ActionRequest) -> ActionResponse {
    match run_command("nmcli", &["radio", "wifi", "off"], None) {
        Ok(_) => ok_response(&req.name, "Wi-Fi disabled."),
        Err(err) => error_response(&req.name, &err),
    }
}

fn handle_bluetooth_on(req: &ActionRequest) -> ActionResponse {
    match run_command("nmcli", &["radio", "bluetooth", "on"], None) {
        Ok(_) => ok_response(&req.name, "Bluetooth enabled."),
        Err(err) => error_response(&req.name, &err),
    }
}

fn handle_bluetooth_off(req: &ActionRequest) -> ActionResponse {
    match run_command("nmcli", &["radio", "bluetooth", "off"], None) {
        Ok(_) => ok_response(&req.name, "Bluetooth disabled."),
        Err(err) => error_response(&req.name, &err),
    }
}

fn handle_power_reboot(req: &ActionRequest) -> ActionResponse {
    match run_command("systemctl", &["reboot"], None) {
        Ok(_) => ok_response(&req.name, "Rebooting now."),
        Err(err) => error_response(&req.name, &err),
    }
}

fn handle_power_shutdown(req: &ActionRequest) -> ActionResponse {
    match run_command("systemctl", &["poweroff"], None) {
        Ok(_) => ok_response(&req.name, "Shutting down now."),
        Err(err) => error_response(&req.name, &err),
    }
}

fn handle_power_sleep(req: &ActionRequest) -> ActionResponse {
    match run_command("systemctl", &["suspend"], None) {
        Ok(_) => ok_response(&req.name, "Sleeping now."),
        Err(err) => error_response(&req.name, &err),
    }
}

fn handle_remember(req: &ActionRequest) -> ActionResponse {
    let Some(note) = req.payload.as_deref() else {
        return error_response(&req.name, "missing memory text");
    };
    if let Err(err) = append_memory(note) {
        return error_response(&req.name, &err);
    }
    ok_response(&req.name, "I'll remember that.")
}

fn handle_plan_day_outfit(req: &ActionRequest) -> ActionResponse {
    let payload = req.payload.as_deref().unwrap_or("today");
    let planner = std::env::var("AI_DISTRO_DAY_PLANNER")
        .unwrap_or_else(|_| "/usr/lib/ai-distro/day_planner.py".to_string());
    match Command::new("python3").arg(planner).arg(payload).output() {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            if msg.is_empty() {
                ok_response(&req.name, "No outfit recommendation available.")
            } else {
                ok_response(&req.name, &msg)
            }
        }
        Ok(out) => {
            let err = String::from_utf8_lossy(&out.stderr).trim().to_string();
            error_response(
                &req.name,
                if err.is_empty() {
                    "failed to build clothing recommendation"
                } else {
                    &err
                },
            )
        }
        Err(err) => error_response(&req.name, &format!("planner failed: {err}")),
    }
}

fn handle_weather_get(req: &ActionRequest) -> ActionResponse {
    let payload = req.payload.as_deref().unwrap_or("today");
    let tool = std::env::var("AI_DISTRO_WEATHER_TOOL")
        .unwrap_or_else(|_| "/usr/lib/ai-distro/weather_tool.py".to_string());
    match Command::new("python3").arg(tool).arg(payload).output() {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            if msg.is_empty() {
                ok_response(&req.name, "Weather unavailable.")
            } else {
                ok_response(&req.name, &msg)
            }
        }
        Ok(out) => error_response(
            &req.name,
            &format!(
                "weather tool failed: {}",
                String::from_utf8_lossy(&out.stderr).trim()
            ),
        ),
        Err(err) => error_response(&req.name, &format!("weather tool launch failed: {err}")),
    }
}

fn handle_calendar_add_event(req: &ActionRequest) -> ActionResponse {
    let Some(payload) = req.payload.as_deref() else {
        return error_response(&req.name, "missing calendar payload");
    };
    let tool = std::env::var("AI_DISTRO_CALENDAR_TOOL")
        .unwrap_or_else(|_| "/usr/lib/ai-distro/calendar_tool.py".to_string());
    match Command::new("python3")
        .arg(tool)
        .arg("add")
        .arg(payload)
        .output()
    {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            ok_response(&req.name, if msg.is_empty() { "Calendar event added." } else { &msg })
        }
        Ok(out) => error_response(
            &req.name,
            &format!(
                "calendar add failed: {}",
                String::from_utf8_lossy(&out.stderr).trim()
            ),
        ),
        Err(err) => error_response(&req.name, &format!("calendar tool launch failed: {err}")),
    }
}

fn handle_calendar_list_day(req: &ActionRequest) -> ActionResponse {
    let payload = req.payload.as_deref().unwrap_or("today");
    let tool = std::env::var("AI_DISTRO_CALENDAR_TOOL")
        .unwrap_or_else(|_| "/usr/lib/ai-distro/calendar_tool.py".to_string());
    match Command::new("python3")
        .arg(tool)
        .arg("list")
        .arg(payload)
        .output()
    {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            ok_response(
                &req.name,
                if msg.is_empty() {
                    "No events found."
                } else {
                    &msg
                },
            )
        }
        Ok(out) => error_response(
            &req.name,
            &format!(
                "calendar list failed: {}",
                String::from_utf8_lossy(&out.stderr).trim()
            ),
        ),
        Err(err) => error_response(&req.name, &format!("calendar tool launch failed: {err}")),
    }
}

fn handle_email_inbox_summary(req: &ActionRequest) -> ActionResponse {
    let payload = req.payload.as_deref().unwrap_or("in:inbox newer_than:2d");
    let tool = std::env::var("AI_DISTRO_GMAIL_TOOL")
        .unwrap_or_else(|_| "/usr/lib/ai-distro/gmail_tool.py".to_string());
    match Command::new("python3")
        .arg(tool)
        .arg("summary")
        .arg(payload)
        .output()
    {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            ok_response(
                &req.name,
                if msg.is_empty() {
                    "No inbox summary available."
                } else {
                    &msg
                },
            )
        }
        Ok(out) => error_response(
            &req.name,
            &format!(
                "gmail summary failed: {}",
                String::from_utf8_lossy(&out.stderr).trim()
            ),
        ),
        Err(err) => error_response(&req.name, &format!("gmail tool launch failed: {err}")),
    }
}

fn handle_email_search(req: &ActionRequest) -> ActionResponse {
    let payload = req.payload.as_deref().unwrap_or("in:inbox");
    let tool = std::env::var("AI_DISTRO_GMAIL_TOOL")
        .unwrap_or_else(|_| "/usr/lib/ai-distro/gmail_tool.py".to_string());
    match Command::new("python3")
        .arg(tool)
        .arg("search")
        .arg(payload)
        .output()
    {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            ok_response(
                &req.name,
                if msg.is_empty() {
                    "No email search results."
                } else {
                    &msg
                },
            )
        }
        Ok(out) => error_response(
            &req.name,
            &format!(
                "gmail search failed: {}",
                String::from_utf8_lossy(&out.stderr).trim()
            ),
        ),
        Err(err) => error_response(&req.name, &format!("gmail tool launch failed: {err}")),
    }
}

fn handle_email_draft(req: &ActionRequest) -> ActionResponse {
    let Some(payload) = req.payload.as_deref() else {
        return error_response(&req.name, "missing draft payload");
    };
    let tool = std::env::var("AI_DISTRO_GMAIL_TOOL")
        .unwrap_or_else(|_| "/usr/lib/ai-distro/gmail_tool.py".to_string());
    match Command::new("python3")
        .arg(tool)
        .arg("draft")
        .arg(payload)
        .output()
    {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            ok_response(
                &req.name,
                if msg.is_empty() {
                    "Draft created."
                } else {
                    &msg
                },
            )
        }
        Ok(out) => error_response(
            &req.name,
            &format!(
                "gmail draft failed: {}",
                String::from_utf8_lossy(&out.stderr).trim()
            ),
        ),
        Err(err) => error_response(&req.name, &format!("gmail tool launch failed: {err}")),
    }
}

fn handle_unknown(req: &ActionRequest) -> ActionResponse {
    let detail = req
        .payload
        .as_deref()
        .unwrap_or("I didn't understand.");
    ActionResponse {
        version: 1,
        action: req.name.clone(),
        status: "error".to_string(),
        message: Some(format!("Need clarification: {detail}")),
        capabilities: None,
        confirmation_id: None,
    }
}

fn ok_response(action: &str, message: &str) -> ActionResponse {
    ActionResponse {
        version: 1,
        action: action.to_string(),
        status: "ok".to_string(),
        message: Some(message.to_string()),
        capabilities: None,
        confirmation_id: None,
    }
}

fn error_response(action: &str, message: &str) -> ActionResponse {
    ActionResponse {
        version: 1,
        action: action.to_string(),
        status: "error".to_string(),
        message: Some(message.to_string()),
        capabilities: None,
        confirmation_id: None,
    }
}

fn command_exists(cmd: &str) -> bool {
    Command::new("sh")
        .arg("-c")
        .arg(format!("command -v {cmd} >/dev/null 2>&1"))
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
}

fn parse_percent_value(raw: &str) -> Option<u8> {
    if raw.is_empty() || raw.len() > 3 {
        return None;
    }
    let parsed = raw.parse::<u8>().ok()?;
    if parsed > 100 {
        return None;
    }
    Some(parsed)
}

fn is_valid_package_name(pkg: &str) -> bool {
    if pkg.is_empty() || pkg.len() > 64 {
        return false;
    }
    pkg.chars()
        .all(|c| c.is_ascii_alphanumeric() || c == '+' || c == '-' || c == '.' || c == ':')
}

fn is_valid_app_name(app: &str) -> bool {
    if app.is_empty() || app.len() > 96 {
        return false;
    }
    app.chars()
        .all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_' || c == '.')
}

fn is_safe_http_url(url: &str) -> bool {
    if url.is_empty() || url.len() > 2048 {
        return false;
    }
    if !(url.starts_with("http://") || url.starts_with("https://")) {
        return false;
    }
    if url.chars().any(|c| c.is_ascii_control() || c.is_whitespace()) {
        return false;
    }
    true
}

fn run_command(
    cmd: &str,
    args: &[&str],
    env: Option<&[(&str, &str)]>,
) -> Result<String, String> {
    let mut command = Command::new(cmd);
    command.args(args);
    if let Some(envs) = env {
        for (key, val) in envs {
            command.env(key, val);
        }
    }
    let output = command.output().map_err(|e| format!("{cmd} failed: {e}"))?;
    if output.status.success() {
        Ok(String::from_utf8_lossy(&output.stdout).to_string())
    } else {
        Err(format!(
            "{cmd} failed: {}",
            String::from_utf8_lossy(&output.stderr).trim()
        ))
    }
}

fn memory_dir() -> String {
    std::env::var("AI_DISTRO_MEMORY_DIR")
        .unwrap_or_else(|_| "/var/lib/ai-distro-agent/memory".to_string())
}

fn append_memory(note: &str) -> Result<(), String> {
    let dir = memory_dir();
    fs::create_dir_all(&dir).map_err(|e| format!("memory dir error: {e}"))?;
    let path = format!("{dir}/notes.jsonl");
    let mut file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(&path)
        .map_err(|e| format!("memory write error: {e}"))?;
    let record = serde_json::json!({
        "ts": now_epoch_secs(),
        "note": note,
    });
    writeln!(file, "{record}").map_err(|e| format!("memory write error: {e}"))?;
    Ok(())
}

fn read_recent_notes(limit: usize) -> Result<Vec<String>, String> {
    let dir = memory_dir();
    let path = format!("{dir}/notes.jsonl");
    let contents = fs::read_to_string(&path).map_err(|e| format!("memory read error: {e}"))?;
    let mut notes = Vec::new();
    for line in contents.lines().rev().take(limit) {
        if let Ok(value) = serde_json::from_str::<serde_json::Value>(line) {
            if let Some(note) = value.get("note").and_then(|n| n.as_str()) {
                notes.push(note.to_string());
            }
        }
    }
    notes.reverse();
    Ok(notes)
}

fn audit_log_path() -> String {
    std::env::var("AI_DISTRO_AUDIT_LOG")
        .unwrap_or_else(|_| "/var/log/ai-distro-agent/audit.jsonl".to_string())
}

fn audit_state_path() -> String {
    std::env::var("AI_DISTRO_AUDIT_STATE")
        .unwrap_or_else(|_| format!("{}.state", audit_log_path()))
}

fn audit_rotate_bytes() -> u64 {
    std::env::var("AI_DISTRO_AUDIT_ROTATE_BYTES")
        .ok()
        .and_then(|v| v.parse::<u64>().ok())
        .unwrap_or(5 * 1024 * 1024)
}

fn payload_fingerprint(payload: Option<&str>) -> Option<u64> {
    payload.map(|text| {
        let mut hasher = DefaultHasher::new();
        text.hash(&mut hasher);
        hasher.finish()
    })
}

fn fnv1a64_hex(input: &[u8]) -> String {
    let mut hash: u64 = 0xcbf29ce484222325;
    for b in input {
        hash ^= *b as u64;
        hash = hash.wrapping_mul(0x100000001b3);
    }
    format!("{hash:016x}")
}

fn compute_chain_hash(seq: u64, prev_hash: &str, event_json: &str) -> String {
    let chain_input = format!("{seq}|{prev_hash}|{event_json}");
    fnv1a64_hex(chain_input.as_bytes())
}

fn load_audit_chain_state(path: &str) -> AuditChainState {
    if let Ok(contents) = fs::read_to_string(path) {
        if let Ok(state) = serde_json::from_str::<AuditChainState>(&contents) {
            return state;
        }
    }
    AuditChainState {
        seq: 0,
        last_hash: "genesis".to_string(),
    }
}

fn persist_audit_chain_state(path: &str, state: &AuditChainState) {
    if let Some(dir) = Path::new(path).parent() {
        if fs::create_dir_all(dir).is_err() {
            return;
        }
    }
    if let Ok(payload) = serde_json::to_string(state) {
        let _ = fs::write(path, payload);
    }
}

fn append_audit_record(path: &str, state: &mut AuditChainState, mut event: serde_json::Value) -> io::Result<()> {
    let next_seq = state.seq.saturating_add(1);
    let prev_hash = state.last_hash.clone();
    {
        let event_obj = event
            .as_object_mut()
            .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "audit event must be object"))?;
        event_obj.insert("seq".to_string(), serde_json::json!(next_seq));
        event_obj.insert("prev_hash".to_string(), serde_json::json!(prev_hash));
    }

    let event_json = serde_json::to_string(&event)
        .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, format!("audit serialize: {e}")))?;
    let chain_hash = compute_chain_hash(next_seq, &state.last_hash, &event_json);

    {
        let event_obj = event
            .as_object_mut()
            .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "audit event must be object"))?;
        event_obj.insert("chain_hash".to_string(), serde_json::json!(chain_hash.clone()));
    }
    let final_line = serde_json::to_string(&event)
        .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, format!("audit serialize: {e}")))?;

    let mut file = OpenOptions::new().create(true).append(true).open(path)?;
    writeln!(file, "{final_line}")?;

    state.seq = next_seq;
    state.last_hash = chain_hash;
    Ok(())
}

fn maybe_rotate_audit_log(path: &str, state: &mut AuditChainState) {
    let rotate_bytes = audit_rotate_bytes();
    if rotate_bytes == 0 {
        return;
    }
    let metadata = match fs::metadata(path) {
        Ok(m) => m,
        Err(_) => return,
    };
    if metadata.len() < rotate_bytes {
        return;
    }
    let rotated_path = format!("{path}.{}.jsonl", now_epoch_secs());
    if fs::rename(path, &rotated_path).is_err() {
        return;
    }
    let anchor = serde_json::json!({
        "ts": now_epoch_secs(),
        "type": "rotation_anchor",
        "rotated_file": rotated_path,
    });
    let _ = append_audit_record(path, state, anchor);
}

fn audit_action_outcome(request: &ActionRequest, response: &ActionResponse) {
    let path = audit_log_path();
    let state_path = audit_state_path();
    let parent = Path::new(&path).parent();
    if let Some(dir) = parent {
        if fs::create_dir_all(dir).is_err() {
            return;
        }
    }
    let lock = AUDIT_CHAIN_STATE.get_or_init(|| Mutex::new(None));
    let mut guard = match lock.lock() {
        Ok(g) => g,
        Err(_) => return,
    };
    if guard.is_none() {
        *guard = Some(load_audit_chain_state(&state_path));
    }
    let state = match guard.as_mut() {
        Some(s) => s,
        None => return,
    };

    maybe_rotate_audit_log(&path, state);
    let event = serde_json::json!({
        "ts": now_epoch_secs(),
        "type": "action_outcome",
        "action": request.name,
        "status": response.status,
        "message": response.message,
        "request_version": request.version.unwrap_or(1),
        "has_confirmation_id": response.confirmation_id.is_some(),
        "payload_len": request.payload.as_deref().map(|p| p.len()).unwrap_or(0),
        "payload_hash": payload_fingerprint(request.payload.as_deref()),
    });
    if append_audit_record(&path, state, event).is_ok() {
        persist_audit_chain_state(&state_path, state);
    }
}

fn finalize_response(request: &ActionRequest, response: ActionResponse) -> ActionResponse {
    audit_action_outcome(request, &response);
    response
}

fn extract_url_host(url: &str) -> Option<String> {
    let (_, rest) = url.split_once("://")?;
    let host_port = rest.split('/').next()?.trim();
    if host_port.is_empty() {
        return None;
    }
    let host = host_port.split(':').next()?.trim().to_ascii_lowercase();
    if host.is_empty() {
        None
    } else {
        Some(host)
    }
}

fn domain_matches(host: &str, allowed: &str) -> bool {
    let allowed = allowed.trim().to_ascii_lowercase();
    if allowed.is_empty() {
        return false;
    }
    host == allowed || host.ends_with(&format!(".{allowed}"))
}

fn is_path_allowed(path: &str, allowed_prefixes: &[String]) -> bool {
    if allowed_prefixes.is_empty() {
        return true;
    }
    let canonical = fs::canonicalize(path).ok();
    let candidate = canonical
        .as_ref()
        .and_then(|p| p.to_str())
        .map(|s| s.to_string())
        .unwrap_or_else(|| path.to_string());

    allowed_prefixes.iter().any(|prefix| {
        let normalized = prefix.trim();
        !normalized.is_empty()
            && (candidate == normalized
                || candidate.starts_with(&format!("{normalized}/")))
    })
}

fn enforce_action_allowlists(
    policy: &ai_distro_common::PolicyConfig,
    request: &ActionRequest,
) -> Result<(), String> {
    match request.name.as_str() {
        "open_url" => {
            let Some(url) = request.payload.as_deref() else {
                return Err("missing url".to_string());
            };
            let domains = &policy.constraints.open_url_allowed_domains;
            if domains.is_empty() {
                return Ok(());
            }
            let Some(host) = extract_url_host(url) else {
                return Err("invalid url host".to_string());
            };
            if domains.iter().any(|allowed| domain_matches(&host, allowed)) {
                Ok(())
            } else {
                Err("url domain denied by policy".to_string())
            }
        }
        "open_app" => {
            let Some(app) = request.payload.as_deref() else {
                return Err("missing app name".to_string());
            };
            let apps = &policy.constraints.open_app_allowed;
            if apps.is_empty() {
                return Ok(());
            }
            if apps.iter().any(|allowed| allowed == app) {
                Ok(())
            } else {
                Err("app denied by policy".to_string())
            }
        }
        "list_files" => {
            let Some(path) = request.payload.as_deref() else {
                return Err("missing path".to_string());
            };
            if is_path_allowed(path, &policy.constraints.list_files_allowed_prefixes) {
                Ok(())
            } else {
                Err("path denied by policy".to_string())
            }
        }
        _ => Ok(()),
    }
}

fn rate_limit_for_action(policy: &ai_distro_common::PolicyConfig, action: &str) -> u32 {
    policy
        .constraints
        .rate_limit_per_minute_overrides
        .get(action)
        .copied()
        .unwrap_or(policy.constraints.rate_limit_per_minute_default)
}

fn enforce_rate_limit(
    policy: &ai_distro_common::PolicyConfig,
    request: &ActionRequest,
) -> Result<(), String> {
    if request.name == "natural_language" {
        return Ok(());
    }
    let limit = rate_limit_for_action(policy, &request.name);
    if limit == 0 {
        return Ok(());
    }
    let now = now_epoch_secs();
    let window_start = now.saturating_sub(60);
    let buckets = RATE_LIMIT_BUCKETS.get_or_init(|| Mutex::new(HashMap::new()));
    let mut guard = buckets
        .lock()
        .map_err(|_| "rate limiter unavailable".to_string())?;
    let key = request.name.clone();
    let bucket = guard.entry(key).or_default();
    bucket.retain(|ts| *ts >= window_start);
    if bucket.len() >= limit as usize {
        return Err(format!("rate limit exceeded for action '{}'", request.name));
    }
    bucket.push(now);
    Ok(())
}

fn dispatch_action(
    policy: &ai_distro_common::PolicyConfig,
    registry: &HashMap<&'static str, Handler>,
    action: Action,
) {
    let request = match action {
        Action::PackageInstall => ActionRequest::package_install(&["vim", "curl"]),
        Action::SystemUpdate => ActionRequest::system_update("stable"),
        Action::ReadContext => ActionRequest::read_context("default"),
        Action::GetCapabilities => ActionRequest::get_capabilities(),
        Action::Ping => ActionRequest::ping(),
    };

    match enforce_policy(policy, &request) {
        PolicyDecision::Allow => {
            log::info!("action allowed: {}", action.as_str());
            if let Some(handler) = registry.get(action.as_str()) {
                let _resp = handler(&request);
            } else {
                log::warn!("no handler registered for {}", request.name);
            }
        }
        PolicyDecision::RequireConfirmation => {
            log::warn!("action requires confirmation: {}", action.as_str());
            // TODO: request user confirmation before proceeding
        }
        PolicyDecision::Deny => {
            log::error!("action denied: {}", action.as_str());
        }
    }
}

fn enforce_policy(
    policy: &ai_distro_common::PolicyConfig,
    request: &ActionRequest,
) -> PolicyDecision {
    let decision =
        evaluate_policy_with_payload(policy, &request.name, request.payload.as_deref());
    log::info!(
        "policy decision: action={}, decision={:?}, payload={:?}",
        request.name,
        decision,
        request.payload
    );
    decision
}

fn handle_request(
    policy: &ai_distro_common::PolicyConfig,
    registry: &HashMap<&'static str, Handler>,
    request: ActionRequest,
) -> ActionResponse {
    if request.name == "confirm" {
        let req_for_audit = request.clone();
        let resp = handle_confirm(policy, registry, request);
        return finalize_response(&req_for_audit, resp);
    }
    if request.name == "natural_language" {
        if let Some(payload) = request.payload.as_deref() {
            if let Some(parsed) = parse_intent_with_cli(payload) {
                if let Ok(parsed_req) = serde_json::from_str::<ActionRequest>(&parsed) {
                    return handle_request(policy, registry, parsed_req);
                }
            }
        }
        let resp = ActionResponse {
            version: 1,
            action: "natural_language".to_string(),
            status: "error".to_string(),
            message: Some("unable to parse natural language request".to_string()),
            capabilities: None,
            confirmation_id: None,
        };
        return finalize_response(&request, resp);
    }

    if request.version.unwrap_or(1) != 1 {
        let resp = ActionResponse {
            version: 1,
            action: request.name.clone(),
            status: "error".to_string(),
            message: Some("unsupported request version".to_string()),
            capabilities: None,
            confirmation_id: None,
        };
        return finalize_response(&request, resp);
    }

    if let Err(detail) = enforce_action_allowlists(policy, &request) {
        let resp = ActionResponse {
            version: 1,
            action: request.name.clone(),
            status: "deny".to_string(),
            message: Some(detail),
            capabilities: None,
            confirmation_id: None,
        };
        return finalize_response(&request, resp);
    }

    if let Err(detail) = enforce_rate_limit(policy, &request) {
        let resp = ActionResponse {
            version: 1,
            action: request.name.clone(),
            status: "deny".to_string(),
            message: Some(detail),
            capabilities: None,
            confirmation_id: None,
        };
        return finalize_response(&request, resp);
    }

    let response = match enforce_policy(policy, &request) {
        PolicyDecision::Allow => {
            if let Some(handler) = registry.get(request.name.as_str()) {
                handler(&request)
            } else {
                ActionResponse {
                    version: 1,
                    action: request.name.clone(),
                    status: "error".to_string(),
                    message: Some("no handler registered".to_string()),
                    capabilities: None,
                    confirmation_id: None,
                }
            }
        }
        PolicyDecision::RequireConfirmation => queue_confirmation(request.clone()),
        PolicyDecision::Deny => ActionResponse {
            version: 1,
            action: request.name.clone(),
            status: "deny".to_string(),
            message: Some("action denied by policy".to_string()),
            capabilities: None,
            confirmation_id: None,
        },
    };
    finalize_response(&request, response)
}

fn run_ipc_loop(
    policy: &ai_distro_common::PolicyConfig,
    registry: &HashMap<&'static str, Handler>,
) {
    let stdin = io::stdin();
    let mut stdout = io::stdout();

    for line in stdin.lock().lines() {
        let line = match line {
            Ok(l) => l,
            Err(_) => break,
        };

        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }

        let response = match serde_json::from_str::<ActionRequest>(trimmed) {
            Ok(req) => handle_request(policy, registry, req),
            Err(err) => ActionResponse {
                version: 1,
                action: "unknown".to_string(),
                status: "error".to_string(),
                message: Some(format!("invalid request: {err}")),
                capabilities: None,
                confirmation_id: None,
            },
        };

        if let Ok(payload) = serde_json::to_string(&response) {
            let _ = writeln!(stdout, "{payload}");
            let _ = stdout.flush();
        }
    }
}

fn run_ipc_socket(
    policy: &ai_distro_common::PolicyConfig,
    registry: &HashMap<&'static str, Handler>,
    path: &str,
) {
    let _ = std::fs::remove_file(path);
    let listener = match UnixListener::bind(path) {
        Ok(l) => l,
        Err(err) => {
            log::error!("failed to bind socket {}: {}", path, err);
            return;
        }
    };
    let mode = std::env::var("AI_DISTRO_IPC_SOCKET_MODE")
        .ok()
        .and_then(|v| u32::from_str_radix(v.trim_start_matches("0o"), 8).ok())
        .filter(|v| *v <= 0o777)
        .unwrap_or(0o660);
    let _ = fs::set_permissions(path, fs::Permissions::from_mode(mode));

    log::info!("ipc socket listening at {}", path);

    for stream in listener.incoming() {
        let stream = match stream {
            Ok(s) => s,
            Err(err) => {
                log::warn!("ipc accept error: {}", err);
                continue;
            }
        };

        let reader = io::BufReader::new(&stream);
        let mut writer = io::BufWriter::new(&stream);

        for line in reader.lines() {
            let line = match line {
                Ok(l) => l,
                Err(_) => break,
            };

            let trimmed = line.trim();
            if trimmed.is_empty() {
                continue;
            }

            let response = match serde_json::from_str::<ActionRequest>(trimmed) {
                Ok(req) => handle_request(policy, registry, req),
                Err(err) => ActionResponse {
                    version: 1,
                    action: "unknown".to_string(),
                    status: "error".to_string(),
                    message: Some(format!("invalid request: {err}")),
                    capabilities: None,
                    confirmation_id: None,
                },
            };

            if let Ok(payload) = serde_json::to_string(&response) {
                let _ = writeln!(writer, "{payload}");
                let _ = writer.flush();
            }
        }
    }
}

fn confirmations_dir() -> String {
    std::env::var("AI_DISTRO_CONFIRM_DIR")
        .unwrap_or_else(|_| "/var/lib/ai-distro-agent/confirmations".to_string())
}

fn confirm_ttl_secs() -> u64 {
    std::env::var("AI_DISTRO_CONFIRM_TTL_SECS")
        .ok()
        .and_then(|v| v.parse::<u64>().ok())
        .unwrap_or(300)
}

fn now_epoch_secs() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}

fn cleanup_expired_confirmations() {
    let dir = confirmations_dir();
    let entries = match std::fs::read_dir(&dir) {
        Ok(e) => e,
        Err(_) => return,
    };
    let now = now_epoch_secs();
    for entry in entries.flatten() {
        let path = entry.path();
        if let Ok(contents) = std::fs::read_to_string(&path) {
            if let Ok(record) = serde_json::from_str::<PendingConfirmation>(&contents) {
                if now > record.expires_at {
                    let _ = std::fs::remove_file(path);
                }
            }
        }
    }
}

fn start_cleanup_thread() {
    let interval = std::env::var("AI_DISTRO_CONFIRM_CLEANUP_SECS")
        .ok()
        .and_then(|v| v.parse::<u64>().ok())
        .unwrap_or(300);
    std::thread::spawn(move || loop {
        cleanup_expired_confirmations();
        std::thread::sleep(std::time::Duration::from_secs(interval));
    });
}

fn queue_confirmation(request: ActionRequest) -> ActionResponse {
    let dir = confirmations_dir();
    let _ = std::fs::create_dir_all(&dir);
    let now = now_epoch_secs();
    let expires_at = now + confirm_ttl_secs();
    let id = format!("{now}-{}", rand_suffix());
    let record = PendingConfirmation {
        created_at: now,
        expires_at,
        request,
    };
    let path = format!("{dir}/{id}.json");
    if let Ok(payload) = serde_json::to_string(&record) {
        let _ = std::fs::write(&path, payload);
    }
    ActionResponse {
        version: 1,
        action: "confirm".to_string(),
        status: "confirm".to_string(),
        message: Some("user confirmation required".to_string()),
        capabilities: None,
        confirmation_id: Some(id),
    }
}

fn rand_suffix() -> String {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .subsec_nanos();
    format!("{nanos}")
}

fn handle_confirm(
    policy: &ai_distro_common::PolicyConfig,
    registry: &HashMap<&'static str, Handler>,
    request: ActionRequest,
) -> ActionResponse {
    let Some(id) = request.payload else {
        return ActionResponse {
            version: 1,
            action: "confirm".to_string(),
            status: "error".to_string(),
            message: Some("missing confirmation id".to_string()),
            capabilities: None,
            confirmation_id: None,
        };
    };

    let dir = confirmations_dir();
    let path = format!("{dir}/{id}.json");
    let contents = match std::fs::read_to_string(&path) {
        Ok(c) => c,
        Err(_) => {
            return ActionResponse {
                version: 1,
                action: "confirm".to_string(),
                status: "error".to_string(),
                message: Some("confirmation not found".to_string()),
                capabilities: None,
                confirmation_id: None,
            }
        }
    };

    let record: PendingConfirmation = match serde_json::from_str(&contents) {
        Ok(r) => r,
        Err(_) => {
            return ActionResponse {
                version: 1,
                action: "confirm".to_string(),
                status: "error".to_string(),
                message: Some("invalid confirmation record".to_string()),
                capabilities: None,
                confirmation_id: None,
            }
        }
    };

    if now_epoch_secs() > record.expires_at {
        let _ = std::fs::remove_file(&path);
        return ActionResponse {
            version: 1,
            action: "confirm".to_string(),
            status: "error".to_string(),
            message: Some("confirmation expired".to_string()),
            capabilities: None,
            confirmation_id: None,
        };
    }

    let _ = std::fs::remove_file(&path);
    match enforce_policy(policy, &record.request) {
        PolicyDecision::Deny => ActionResponse {
            version: 1,
            action: record.request.name,
            status: "deny".to_string(),
            message: Some("action denied by policy".to_string()),
            capabilities: None,
            confirmation_id: None,
        },
        PolicyDecision::Allow | PolicyDecision::RequireConfirmation => {
            if let Some(handler) = registry.get(record.request.name.as_str()) {
                handler(&record.request)
            } else {
                ActionResponse {
                    version: 1,
                    action: record.request.name,
                    status: "error".to_string(),
                    message: Some("no handler registered".to_string()),
                    capabilities: None,
                    confirmation_id: None,
                }
            }
        }
    }
}

fn parse_intent_with_cli(text: &str) -> Option<String> {
    let parser = std::env::var("AI_DISTRO_INTENT_PARSER")
        .unwrap_or_else(|_| "/usr/lib/ai-distro/intent_parser.py".to_string());
    let output = std::process::Command::new(parser)
        .arg(text)
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }
    String::from_utf8(output.stdout).ok()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::path::PathBuf;

    fn build_registry() -> HashMap<&'static str, Handler> {
        action_registry()
    }

    #[test]
    fn ipc_serializes_request() {
        let req = ActionRequest {
            version: Some(1),
            name: "package_install".to_string(),
            payload: Some("vim,curl".to_string()),
        };
        let json = serde_json::to_string(&req).unwrap();
        assert!(json.contains("package_install"));
    }

    #[test]
    fn ipc_serializes_response() {
        let resp = ActionResponse {
            version: 1,
            action: "package_install".to_string(),
            status: "ok".to_string(),
            message: None,
            capabilities: None,
            confirmation_id: None,
        };
        let json = serde_json::to_string(&resp).unwrap();
        assert!(json.contains("\"status\":\"ok\""));
    }

    #[test]
    fn ipc_parses_request() {
        let json = r#"{"version":1,"name":"system_update","payload":"stable"}"#;
        let req: ActionRequest = serde_json::from_str(json).unwrap();
        assert_eq!(req.name, "system_update");
        assert_eq!(req.payload.as_deref(), Some("stable"));
    }

    #[test]
    fn ipc_natural_language_unparsed_errors() {
        let policy = ai_distro_common::PolicyConfig::default();
        let registry = build_registry();
        let req = ActionRequest {
            version: Some(1),
            name: "natural_language".to_string(),
            payload: Some("install firefox".to_string()),
        };
        let resp = handle_request(&policy, &registry, req);
        assert_eq!(resp.status, "error");
    }

    #[test]
    fn parse_percent_enforces_bounds() {
        assert_eq!(parse_percent_value("0"), Some(0));
        assert_eq!(parse_percent_value("100"), Some(100));
        assert_eq!(parse_percent_value("101"), None);
        assert_eq!(parse_percent_value("-1"), None);
        assert_eq!(parse_percent_value("abc"), None);
    }

    #[test]
    fn package_name_validation_rejects_unsafe_chars() {
        assert!(is_valid_package_name("vim"));
        assert!(is_valid_package_name("python3-pip"));
        assert!(!is_valid_package_name("vim;rm"));
        assert!(!is_valid_package_name(""));
    }

    #[test]
    fn url_validation_allows_http_https_only() {
        assert!(is_safe_http_url("https://docs.openai.com"));
        assert!(is_safe_http_url("http://example.com"));
        assert!(!is_safe_http_url("file:///etc/passwd"));
        assert!(!is_safe_http_url("javascript:alert(1)"));
    }

    #[test]
    fn allowlist_matches_subdomains() {
        assert!(domain_matches("docs.openai.com", "openai.com"));
        assert!(domain_matches("openai.com", "openai.com"));
        assert!(!domain_matches("evil.com", "openai.com"));
    }

    #[test]
    fn policy_deny_open_url_outside_allowlist() {
        let mut policy = ai_distro_common::PolicyConfig::default();
        policy.constraints.open_url_allowed_domains = vec!["openai.com".to_string()];
        let req = ActionRequest {
            version: Some(1),
            name: "open_url".to_string(),
            payload: Some("https://example.com".to_string()),
        };
        let denied = enforce_action_allowlists(&policy, &req).is_err();
        assert!(denied);
    }

    #[test]
    fn policy_allow_list_files_prefix() {
        let mut policy = ai_distro_common::PolicyConfig::default();
        policy.constraints.list_files_allowed_prefixes = vec!["/tmp".to_string()];
        let req = ActionRequest {
            version: Some(1),
            name: "list_files".to_string(),
            payload: Some("/etc".to_string()),
        };
        let denied = enforce_action_allowlists(&policy, &req).is_err();
        assert!(denied);
    }

    #[test]
    fn rate_limit_blocks_second_request_when_limit_is_one() {
        let mut policy = ai_distro_common::PolicyConfig::default();
        policy
            .constraints
            .rate_limit_per_minute_overrides
            .insert("rate_limit_test_action".to_string(), 1);

        let req = ActionRequest {
            version: Some(1),
            name: "rate_limit_test_action".to_string(),
            payload: None,
        };
        assert!(enforce_rate_limit(&policy, &req).is_ok());
        assert!(enforce_rate_limit(&policy, &req).is_err());
    }

    #[test]
    fn chain_hash_is_deterministic() {
        let event = r#"{"action":"ping","status":"ok"}"#;
        let a = compute_chain_hash(1, "genesis", event);
        let b = compute_chain_hash(1, "genesis", event);
        let c = compute_chain_hash(2, "genesis", event);
        assert_eq!(a, b);
        assert_ne!(a, c);
    }

    #[test]
    fn append_audit_record_advances_chain_state() {
        let mut dir = std::env::temp_dir();
        dir.push(format!("ai-distro-audit-{}", now_epoch_secs()));
        let _ = fs::create_dir_all(&dir);
        let path = dir.join("audit.jsonl");
        let mut state = AuditChainState {
            seq: 0,
            last_hash: "genesis".to_string(),
        };
        let event = serde_json::json!({
            "ts": now_epoch_secs(),
            "type": "action_outcome",
            "action": "ping",
            "status": "ok"
        });
        let ok = append_audit_record(path.to_string_lossy().as_ref(), &mut state, event).is_ok();
        assert!(ok);
        assert_eq!(state.seq, 1);
        assert_ne!(state.last_hash, "genesis");
    }

    fn temp_confirm_dir() -> PathBuf {
        let mut dir = std::env::temp_dir();
        dir.push(format!("ai-distro-confirm-{}", now_epoch_secs()));
        let _ = fs::create_dir_all(&dir);
        dir
    }

    #[test]
    fn confirm_cleanup_removes_expired() {
        let dir = temp_confirm_dir();
        std::env::set_var("AI_DISTRO_CONFIRM_DIR", dir.to_string_lossy().to_string());

        let record = PendingConfirmation {
            created_at: now_epoch_secs() - 100,
            expires_at: now_epoch_secs() - 1,
            request: ActionRequest {
                version: Some(1),
                name: "package_install".to_string(),
                payload: Some("vim".to_string()),
            },
        };
        let path = dir.join("expired.json");
        let _ = fs::write(&path, serde_json::to_string(&record).unwrap());

        cleanup_expired_confirmations();

        assert!(!path.exists());
    }

    #[test]
    fn confirm_executes_and_removes_record() {
        let dir = temp_confirm_dir();
        std::env::set_var("AI_DISTRO_CONFIRM_DIR", dir.to_string_lossy().to_string());

        let record = PendingConfirmation {
            created_at: now_epoch_secs(),
            expires_at: now_epoch_secs() + 300,
            request: ActionRequest {
                version: Some(1),
                name: "ping".to_string(),
                payload: None,
            },
        };
        let id = "test-confirm";
        let path = dir.join(format!("{id}.json"));
        let _ = fs::write(&path, serde_json::to_string(&record).unwrap());

        let policy = ai_distro_common::PolicyConfig::default();
        let registry = build_registry();
        let req = ActionRequest {
            version: Some(1),
            name: "confirm".to_string(),
            payload: Some(id.to_string()),
        };
        let resp = handle_confirm(&policy, &registry, req);

        assert_eq!(resp.status, "ok");
        assert!(!path.exists());
    }
}

fn main() {
    let cfg: AgentConfig = load_typed_config("/etc/ai-distro/agent.json");
    init_logging_with_config(&cfg.service);
    log::info!("starting");
    let policy = load_policy(&cfg.policy_file);
    log::info!(
        "policy loaded: mode={}, confirm={}, deny={}",
        policy.mode,
        policy.constraints.require_confirmation_for.len(),
        policy.constraints.deny_actions.len()
    );
    cleanup_expired_confirmations();
    start_cleanup_thread();

    let registry = action_registry();
    if let Ok(path) = std::env::var("AI_DISTRO_IPC_SOCKET") {
        run_ipc_socket(&policy, &registry, &path);
    } else if std::env::var("AI_DISTRO_IPC_STDIN").ok().as_deref() == Some("1") {
        run_ipc_loop(&policy, &registry);
    } else if std::env::var("AI_DISTRO_INTENT_STDIN")
        .ok()
        .as_deref()
        == Some("1")
    {
        let stdin = io::stdin();
        for line in stdin.lock().lines().flatten() {
            if let Some(out) = parse_intent_with_cli(&line) {
                print!("{out}");
            } else {
                println!("{{\"intent\":\"<unknown>\"}}");
            }
        }
    } else {
        // Example action dispatcher placeholder
        dispatch_action(&policy, &registry, Action::PackageInstall);
        dispatch_action(&policy, &registry, Action::SystemUpdate);
        dispatch_action(&policy, &registry, Action::ReadContext);
        dispatch_action(&policy, &registry, Action::GetCapabilities);
        dispatch_action(&policy, &registry, Action::Ping);
    }

    loop {
        thread::sleep(Duration::from_secs(60));
        log::info!("heartbeat");
    }
}

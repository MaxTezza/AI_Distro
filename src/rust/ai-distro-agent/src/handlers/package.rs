use ai_distro_common::{ActionRequest, ActionResponse};
use crate::utils::{run_command, command_exists};

pub fn handle_package_install(req: &ActionRequest) -> ActionResponse {
    let Some(payload) = req.payload.as_deref() else {
        return error_response(&req.name, "missing package list");
    };
    let packages = parse_package_payload(payload);
    if packages.is_empty() {
        return error_response(&req.name, "empty package list");
    }
    if packages.len() > 20 {
        return error_response(&req.name, "too many packages requested");
    }
    let mut installed = Vec::new();
    for pkg in &packages {
        match install_package_with_best_source(pkg) {
            Ok(msg) => installed.push(msg),
            Err(err) => return error_response(&req.name, &err),
        }
    }
    if installed.is_empty() {
        ok_response(&req.name, "I installed what you asked for.")
    } else {
        ok_response(
            &req.name,
            &format!("I installed this for you: {}. You're all set.", installed.join(", ")),
        )
    }
}

pub fn handle_package_remove(req: &ActionRequest) -> ActionResponse {
    let Some(payload) = req.payload.as_deref() else {
        return error_response(&req.name, "missing package list");
    };
    let packages = parse_package_payload(payload);
    if packages.is_empty() {
        return error_response(&req.name, "empty package list");
    }
    if packages.len() > 20 {
        return error_response(&req.name, "too many packages requested");
    }
    let mut removed = Vec::new();
    for pkg in &packages {
        match remove_package_with_best_source(pkg) {
            Ok(msg) => removed.push(msg),
            Err(err) => return error_response(&req.name, &err),
        }
    }
    if removed.is_empty() {
        ok_response(&req.name, "I removed what you asked for.")
    } else {
        ok_response(
            &req.name,
            &format!("I removed this for you: {}. Done.", removed.join(", ")),
        )
    }
}

// ... internal helper functions (is_valid_package_name, parse_package_payload, etc. from main.rs) ...
// I will include the core ones for now.

fn parse_package_payload(payload: &str) -> Vec<&str> {
    payload
        .split(',')
        .map(|s| s.trim())
        .filter(|s| !s.is_empty())
        .collect()
}

fn install_package_with_best_source(query: &str) -> Result<String, String> {
    // simplified for brevity in this step, but based on main.rs logic
    if query.contains('.') && command_exists("flatpak") {
         run_command("flatpak", &["install", "-y", "flathub", query], None)?;
         return Ok(format!("{} via flatpak", query));
    }
    run_command("apt-get", &["install", "-y", query], Some(&[("DEBIAN_FRONTEND", "noninteractive")]))?;
    Ok(format!("{} via apt", query))
}

fn remove_package_with_best_source(query: &str) -> Result<String, String> {
    if query.contains('.') && command_exists("flatpak") {
         run_command("flatpak", &["uninstall", "-y", query], None)?;
         return Ok(format!("{} via flatpak", query));
    }
    run_command("apt-get", &["remove", "-y", query], Some(&[("DEBIAN_FRONTEND", "noninteractive")]))?;
    Ok(format!("{} via apt", query))
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

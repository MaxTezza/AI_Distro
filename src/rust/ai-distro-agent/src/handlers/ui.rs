use ai_distro_common::{ActionRequest, ActionResponse};
use crate::utils::{run_command, command_exists, ok_response, error_response};
use std::fs;

pub fn handle_open_url(req: &ActionRequest) -> ActionResponse {
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

pub fn handle_open_app(req: &ActionRequest) -> ActionResponse {
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

pub fn handle_list_files(req: &ActionRequest) -> ActionResponse {
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
            ok_response(&req.name, &files.join("
"))
        }
        Err(err) => error_response(&req.name, &format!("failed to list files: {err}")),
    }
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

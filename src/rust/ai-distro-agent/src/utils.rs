use ai_distro_common::ActionResponse;
use std::process::Command;

pub fn ok_response(action: &str, message: &str) -> ActionResponse {
    ActionResponse {
        version: 1,
        action: action.to_string(),
        status: "ok".to_string(),
        message: Some(message.to_string()),
        capabilities: None,
        confirmation_id: None,
    }
}

pub fn error_response(action: &str, message: &str) -> ActionResponse {
    ActionResponse {
        version: 1,
        action: action.to_string(),
        status: "error".to_string(),
        message: Some(message.to_string()),
        capabilities: None,
        confirmation_id: None,
    }
}

pub fn run_command(
// ... rest of the file ...
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
    let output = command.output().map_err(|e| format!("{} failed: {}", cmd, e))?;
    if output.status.success() {
        Ok(String::from_utf8_lossy(&output.stdout).to_string())
    } else {
        Err(format!(
            "{} failed: {}",
            cmd,
            String::from_utf8_lossy(&output.stderr).trim()
        ))
    }
}

pub fn command_exists(cmd: &str) -> bool {
    Command::new("sh")
        .arg("-c")
        .arg(format!("command -v {} >/dev/null 2>&1", cmd))
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
}

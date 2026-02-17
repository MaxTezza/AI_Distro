use ai_distro_common::{ActionRequest, ActionResponse};
use crate::utils::{run_command, command_exists, ok_response, error_response};

pub fn handle_set_volume(req: &ActionRequest) -> ActionResponse {
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

pub fn handle_set_brightness(req: &ActionRequest) -> ActionResponse {
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

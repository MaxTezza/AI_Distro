use ai_distro_common::{ActionRequest, ActionResponse};
use crate::utils::{run_command, ok_response, error_response};

pub fn handle_wifi_on(req: &ActionRequest) -> ActionResponse {
    match run_command("nmcli", &["radio", "wifi", "on"], None) {
        Ok(_) => ok_response(&req.name, "Wi-Fi enabled."),
        Err(err) => error_response(&req.name, &err),
    }
}

pub fn handle_wifi_off(req: &ActionRequest) -> ActionResponse {
    match run_command("nmcli", &["radio", "wifi", "off"], None) {
        Ok(_) => ok_response(&req.name, "Wi-Fi disabled."),
        Err(err) => error_response(&req.name, &err),
    }
}

pub fn handle_bluetooth_on(req: &ActionRequest) -> ActionResponse {
    match run_command("nmcli", &["radio", "bluetooth", "on"], None) {
        Ok(_) => ok_response(&req.name, "Bluetooth enabled."),
        Err(err) => error_response(&req.name, &err),
    }
}

pub fn handle_bluetooth_off(req: &ActionRequest) -> ActionResponse {
    match run_command("nmcli", &["radio", "bluetooth", "off"], None) {
        Ok(_) => ok_response(&req.name, "Bluetooth disabled."),
        Err(err) => error_response(&req.name, &err),
    }
}

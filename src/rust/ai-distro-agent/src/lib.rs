pub mod audit;
pub mod policy;
pub mod utils;
pub mod handlers;
pub mod ipc;
pub mod events;

use ai_distro_common::{ActionRequest, ActionResponse, PolicyConfig, PolicyDecision, Capabilities};
use std::collections::HashMap;
use crate::utils::{ok_response, error_response};

pub type Handler = fn(&ActionRequest) -> ActionResponse;

pub fn load_skills(dir: &str) -> HashMap<String, ai_distro_common::SkillManifest> {
    let mut skills = HashMap::new();
    if let Ok(entries) = std::fs::read_dir(dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.extension().and_then(|s| s.to_str()) == Some("json") {
                if let Ok(content) = std::fs::read_to_string(&path) {
                    if let Ok(manifest) = serde_json::from_str::<ai_distro_common::SkillManifest>(&content) {
                        skills.insert(manifest.name.clone(), manifest);
                    }
                }
            }
        }
    }
    skills
}

pub fn action_registry() -> HashMap<&'static str, Handler> {
    let mut map: HashMap<&'static str, Handler> = HashMap::new();
    
    // Package management
    map.insert("package_install", handlers::package::handle_package_install as Handler);
    map.insert("package_remove", handlers::package::handle_package_remove as Handler);
    
    // System management
    map.insert("system_update", handlers::system::handle_system_update as Handler);
    
    // Media controls
    map.insert("set_volume", handlers::media::handle_set_volume as Handler);
    map.insert("set_brightness", handlers::media::handle_set_brightness as Handler);
    
    // Network controls
    map.insert("network_wifi_on", handlers::network::handle_wifi_on as Handler);
    map.insert("network_wifi_off", handlers::network::handle_wifi_off as Handler);
    map.insert("network_bluetooth_on", handlers::network::handle_bluetooth_on as Handler);
    map.insert("network_bluetooth_off", handlers::network::handle_bluetooth_off as Handler);
    
    // Power management
    map.insert("power_reboot", handlers::power::handle_power_reboot as Handler);
    map.insert("power_shutdown", handlers::power::handle_power_shutdown as Handler);
    map.insert("power_sleep", handlers::power::handle_power_sleep as Handler);
    
    // Memory and context
    map.insert("remember", handlers::memory::handle_remember as Handler);
    map.insert("read_context", handlers::memory::handle_read_context as Handler);
    
    // UI and filesystem
    map.insert("open_url", handlers::ui::handle_open_url as Handler);
    map.insert("open_app", handlers::ui::handle_open_app as Handler);
    map.insert("list_files", handlers::ui::handle_list_files as Handler);
    
    // External tools (Python-based)
    map.insert("weather_get", handlers::tools::handle_weather_get as Handler);
    map.insert("calendar_add_event", handlers::tools::handle_calendar_add_event as Handler);
    map.insert("calendar_list_day", handlers::tools::handle_calendar_list_day as Handler);
    map.insert("email_inbox_summary", handlers::tools::handle_email_inbox_summary as Handler);
    map.insert("email_search", handlers::tools::handle_email_search as Handler);
    map.insert("email_draft", handlers::tools::handle_email_draft as Handler);
    map.insert("plan_day_outfit", handlers::tools::handle_plan_day_outfit as Handler);
    
    // Core built-ins
    map.insert("ping", handle_ping as Handler);
    map.insert("get_capabilities", handle_get_capabilities as Handler);
    
    map
}

pub fn handle_ping(req: &ActionRequest) -> ActionResponse {
    ActionResponse {
        version: 1,
        action: req.name.clone(),
        status: "ok".to_string(),
        message: Some("pong".to_string()),
        capabilities: None,
        confirmation_id: None,
    }
}

pub fn handle_get_capabilities(req: &ActionRequest) -> ActionResponse {
    ActionResponse {
        version: 1,
        action: req.name.clone(),
        status: "ok".to_string(),
        message: None,
        capabilities: Some(Capabilities {
            ipc_version: 1,
            actions: action_registry().keys().map(|s| s.to_string()).collect(),
            protocol_version: 1,
        }),
        confirmation_id: None,
    }
}

pub fn handle_request(
    policy: &PolicyConfig,
    registry: &HashMap<&'static str, Handler>,
    request: ActionRequest,
) -> ActionResponse {
    let response = handle_request_inner(policy, registry, request.clone());
    
    // Cryptographic Audit Log
    let audit_log = std::env::var("AI_DISTRO_AUDIT_LOG").unwrap_or_else(|_| "/var/log/ai-distro/audit.json".to_string());
    let audit_state = std::env::var("AI_DISTRO_AUDIT_STATE").unwrap_or_else(|_| "/var/lib/ai-distro/audit_state.json".to_string());
    
    let mut state = audit::load_audit_chain_state(&audit_state);
    let event = serde_json::json!({
        "ts": audit::now_epoch_secs(),
        "action": request.name,
        "status": response.status,
        "payload": request.payload
    });
    let _ = audit::append_audit_record(&audit_log, &mut state, event);
    audit::persist_audit_chain_state(&audit_state, &state);

    response
}

fn handle_request_inner(
    policy: &PolicyConfig,
    registry: &HashMap<&'static str, Handler>,
    request: ActionRequest,
) -> ActionResponse {
    // 0. Handle natural language parsing
    if request.name == "natural_language" {
        if let Some(text) = request.payload.as_deref() {
            // Try LLM Brain first
            let brain_path = std::env::var("AI_DISTRO_BRAIN")
                .unwrap_or_else(|_| "tools/agent/brain.py".to_string());
            
            let mut parsed_req: Option<ActionRequest> = None;
            
            if let Ok(output) = std::process::Command::new("python3")
                .arg(&brain_path)
                .arg(text)
                .output() {
                if output.status.success() {
                    parsed_req = serde_json::from_slice(&output.stdout).ok();
                }
            }
            
            // Fallback to Regex Parser
            if parsed_req.is_none() {
                let parser_path = std::env::var("AI_DISTRO_INTENT_PARSER")
                    .unwrap_or_else(|_| "tools/agent/intent_parser.py".to_string());
                if let Ok(output) = std::process::Command::new("python3")
                    .arg(&parser_path)
                    .arg(text)
                    .output() {
                    if output.status.success() {
                        parsed_req = serde_json::from_slice(&output.stdout).ok();
                    }
                }
            }
            
            if let Some(new_req) = parsed_req {
                return handle_request(policy, registry, new_req);
            }
        }
        
        return ActionResponse {
            version: 1,
            action: "natural_language".to_string(),
            status: "error".to_string(),
            message: Some("I couldn't understand that request.".to_string()),
            capabilities: None,
            confirmation_id: None,
        };
    }

    // 1. Enforce allowlists
    if let Err(detail) = policy::enforce_action_allowlists(policy, &request) {
        return ActionResponse {
            version: 1,
            action: request.name.clone(),
            status: "deny".to_string(),
            message: Some(detail),
            capabilities: None,
            confirmation_id: None,
        };
    }

    // 2. Enforce rate limits
    if let Err(detail) = policy::enforce_rate_limit(policy, &request) {
        return ActionResponse {
            version: 1,
            action: request.name.clone(),
            status: "deny".to_string(),
            message: Some(detail),
            capabilities: None,
            confirmation_id: None,
        };
    }

    // 3. Enforce general policy (Allow/Deny/Confirm)
    match ai_distro_common::evaluate_policy_with_payload(policy, &request.name, request.payload.as_deref()) {
        PolicyDecision::Allow => {
            if let Some(handler) = registry.get(request.name.as_str()) {
                handler(&request)
            } else {
                error_response(&request.name, "no handler registered")
            }
        }
        PolicyDecision::RequireConfirmation => {
             ActionResponse {
                version: 1,
                action: request.name.clone(),
                status: "confirm".to_string(),
                message: Some("user confirmation required".to_string()),
                capabilities: None,
                confirmation_id: Some("temp-id".to_string()), // TODO: Implement real confirmation queue
            }
        }
        PolicyDecision::Deny => {
            ActionResponse {
                version: 1,
                action: request.name.clone(),
                status: "deny".to_string(),
                message: Some("action denied by policy".to_string()),
                capabilities: None,
                confirmation_id: None,
            }
        }
    }
}

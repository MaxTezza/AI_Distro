use serde::{de::DeserializeOwned, Deserialize, Serialize};
use std::fs;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ServiceConfig {
    pub name: String,
    pub log_level: String,
    pub log_file: Option<String>,
}

impl Default for ServiceConfig {
    fn default() -> Self {
        Self {
            name: "ai-distro".to_string(),
            log_level: "info".to_string(),
            log_file: None,
        }
    }
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct CoreConfig {
    pub service: ServiceConfig,
    pub state_db_path: String,
    pub ipc_socket: String,
    pub context_dir: String,
}

impl Default for CoreConfig {
    fn default() -> Self {
        Self {
            service: ServiceConfig {
                name: "ai-distro-core".to_string(),
                log_level: "info".to_string(),
                log_file: None,
            },
            state_db_path: "/var/lib/ai-distro-core/state.db".to_string(),
            ipc_socket: "/run/ai-distro/core.sock".to_string(),
            context_dir: "/var/lib/ai-distro-core/context".to_string(),
        }
    }
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct VoiceConfig {
    pub service: ServiceConfig,
    pub asr_model: String,
    pub tts_model: String,
    pub audio_device: String,
    pub asr_binary: String,
    pub tts_binary: String,
}

impl Default for VoiceConfig {
    fn default() -> Self {
        Self {
            service: ServiceConfig {
                name: "ai-distro-voice".to_string(),
                log_level: "info".to_string(),
                log_file: None,
            },
            asr_model: "default-asr".to_string(),
            tts_model: "default-tts".to_string(),
            audio_device: "default".to_string(),
            asr_binary: "/usr/bin/vosk-server".to_string(),
            tts_binary: "/usr/bin/piper".to_string(),
        }
    }
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct AgentConfig {
    pub service: ServiceConfig,
    pub skills_dir: String,
    pub policy_file: String,
    pub memory_dir: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct PolicyConfig {
    pub version: u32,
    pub mode: String,
    pub constraints: PolicyConstraints,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct PolicyConstraints {
    pub require_confirmation_for: Vec<String>,
    pub deny_actions: Vec<String>,
    pub package_install_deny: Vec<String>,
    pub package_install_confirm: Vec<String>,
}

impl Default for PolicyConfig {
    fn default() -> Self {
        Self {
            version: 1,
            mode: "assistive".to_string(),
            constraints: PolicyConstraints {
                require_confirmation_for: vec![],
                deny_actions: vec![],
                package_install_deny: vec![],
                package_install_confirm: vec![],
            },
        }
    }
}

impl Default for AgentConfig {
    fn default() -> Self {
        Self {
            service: ServiceConfig {
                name: "ai-distro-agent".to_string(),
                log_level: "info".to_string(),
                log_file: None,
            },
            skills_dir: "/var/lib/ai-distro-agent/skills".to_string(),
            policy_file: "/etc/ai-distro/policy.json".to_string(),
            memory_dir: "/var/lib/ai-distro-agent/memory".to_string(),
        }
    }
}

pub fn init_logging_with_config(cfg: &ServiceConfig) {
    let mut builder = env_logger::Builder::from_default_env();
    builder.filter_level(cfg.log_level.parse().unwrap_or(log::LevelFilter::Info));

    if let Some(path) = cfg.log_file.as_deref() {
        if let Ok(file) = std::fs::OpenOptions::new().create(true).append(true).open(path) {
            builder.target(env_logger::Target::Pipe(Box::new(file)));
        }
    }

    let service = cfg.name.clone();
    builder.format(move |buf, record| {
        use std::io::Write;
        let ts = buf.timestamp_millis();
        writeln!(buf, "{ts} [{service}] {} - {}", record.level(), record.args())
    });

    let _ = builder.try_init();
}

pub fn init_logging(service: &str, level: &str) {
    let cfg = ServiceConfig {
        name: service.to_string(),
        log_level: level.to_string(),
        log_file: None,
    };
    init_logging_with_config(&cfg);
}

pub fn load_config(path: &str, fallback_name: &str) -> ServiceConfig {
    let mut cfg = ServiceConfig::default();
    cfg.name = fallback_name.to_string();

    match fs::read_to_string(path) {
        Ok(contents) => {
            if let Ok(parsed) = serde_json::from_str::<ServiceConfig>(&contents) {
                parsed
            } else {
                cfg
            }
        }
        Err(_) => cfg,
    }
}

pub fn load_typed_config<T: DeserializeOwned + Default>(path: &str) -> T {
    match fs::read_to_string(path) {
        Ok(contents) => serde_json::from_str::<T>(&contents).unwrap_or_default(),
        Err(_) => T::default(),
    }
}

pub fn load_policy(path: &str) -> PolicyConfig {
    load_typed_config(path)
}

#[derive(Debug, Clone, Copy)]
pub enum PolicyDecision {
    Allow,
    RequireConfirmation,
    Deny,
}

pub fn evaluate_policy(policy: &PolicyConfig, action: &str) -> PolicyDecision {
    if policy
        .constraints
        .deny_actions
        .iter()
        .any(|rule| rule == action)
    {
        return PolicyDecision::Deny;
    }

    if policy
        .constraints
        .require_confirmation_for
        .iter()
        .any(|rule| rule == action)
    {
        return PolicyDecision::RequireConfirmation;
    }

    PolicyDecision::Allow
}

pub fn evaluate_policy_with_payload(
    policy: &PolicyConfig,
    action: &str,
    payload: Option<&str>,
) -> PolicyDecision {
    let decision = evaluate_policy(policy, action);
    if matches!(decision, PolicyDecision::Deny) {
        return decision;
    }

    if action == "package_install" {
        if let Some(payload) = payload {
            let pkgs: Vec<&str> = payload
                .split(',')
                .map(|s| s.trim())
                .filter(|s| !s.is_empty())
                .collect();

            for deny in &policy.constraints.package_install_deny {
                if pkgs.iter().any(|p| p == deny) {
                    return PolicyDecision::Deny;
                }
            }

            for confirm in &policy.constraints.package_install_confirm {
                if pkgs.iter().any(|p| p == confirm) {
                    return PolicyDecision::RequireConfirmation;
                }
            }
        }
    }

    decision
}

#[cfg(test)]
mod tests {
    use super::*;

    fn base_policy() -> PolicyConfig {
        PolicyConfig {
            version: 1,
            mode: "assistive".to_string(),
            constraints: PolicyConstraints {
                require_confirmation_for: vec!["package_install".to_string()],
                deny_actions: vec!["rm -rf /".to_string()],
                package_install_deny: vec![],
                package_install_confirm: vec![],
            },
        }
    }

    #[test]
    fn policy_denies_blocked_action() {
        let policy = base_policy();
        matches!(evaluate_policy(&policy, "rm -rf /"), PolicyDecision::Deny);
        if !matches!(evaluate_policy(&policy, "rm -rf /"), PolicyDecision::Deny) {
            panic!("expected deny");
        }
    }

    #[test]
    fn policy_requires_confirmation() {
        let policy = base_policy();
        if !matches!(
            evaluate_policy(&policy, "package_install"),
            PolicyDecision::RequireConfirmation
        ) {
            panic!("expected confirmation");
        }
    }

    #[test]
    fn policy_allows_default() {
        let policy = base_policy();
        if !matches!(evaluate_policy(&policy, "read_context"), PolicyDecision::Allow) {
            panic!("expected allow");
        }
    }

    #[test]
    fn policy_payload_deny_package() {
        let mut policy = base_policy();
        policy.constraints.package_install_deny = vec!["rm".to_string(), "badpkg".to_string()];
        let decision = evaluate_policy_with_payload(&policy, "package_install", Some("vim,badpkg"));
        if !matches!(decision, PolicyDecision::Deny) {
            panic!("expected deny for badpkg");
        }
    }

    #[test]
    fn policy_payload_confirm_package() {
        let mut policy = base_policy();
        policy.constraints.package_install_confirm = vec!["openssl".to_string()];
        let decision =
            evaluate_policy_with_payload(&policy, "package_install", Some("vim,openssl"));
        if !matches!(decision, PolicyDecision::RequireConfirmation) {
            panic!("expected confirmation for openssl");
        }
    }

    #[test]
    fn policy_payload_ignores_whitespace() {
        let mut policy = base_policy();
        policy.constraints.package_install_confirm = vec!["docker".to_string()];
        let decision = evaluate_policy_with_payload(
            &policy,
            "package_install",
            Some("  vim , docker ,curl "),
        );
        if !matches!(decision, PolicyDecision::RequireConfirmation) {
            panic!("expected confirmation for docker with whitespace");
        }
    }
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ActionRequest {
    pub version: Option<u32>,
    pub name: String,
    pub payload: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ActionResponse {
    pub version: u32,
    pub action: String,
    pub status: String,
    pub message: Option<String>,
    pub capabilities: Option<Capabilities>,
    pub confirmation_id: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Capabilities {
    pub ipc_version: u32,
    pub actions: Vec<String>,
    pub protocol_version: u32,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PendingConfirmation {
    pub created_at: u64,
    pub expires_at: u64,
    pub request: ActionRequest,
}

impl ActionRequest {
    pub fn package_install(packages: &[&str]) -> Self {
        Self {
            version: Some(1),
            name: "package_install".to_string(),
            payload: Some(packages.join(",")),
        }
    }

    pub fn system_update(channel: &str) -> Self {
        Self {
            version: Some(1),
            name: "system_update".to_string(),
            payload: Some(channel.to_string()),
        }
    }

    pub fn read_context(context_id: &str) -> Self {
        Self {
            version: Some(1),
            name: "read_context".to_string(),
            payload: Some(context_id.to_string()),
        }
    }

    pub fn get_capabilities() -> Self {
        Self {
            version: Some(1),
            name: "get_capabilities".to_string(),
            payload: None,
        }
    }

    pub fn ping() -> Self {
        Self {
            version: Some(1),
            name: "ping".to_string(),
            payload: None,
        }
    }
}


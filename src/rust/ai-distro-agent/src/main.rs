use ai_distro_agent::{action_registry as get_registry};
use ai_distro_agent::ipc::run_ipc_socket;
use ai_distro_common::{load_typed_config, init_logging_with_config, load_policy, AgentConfig};

#[tokio::main]
async fn main() {
    // 1. Load configuration
    let cfg: AgentConfig = load_typed_config("/etc/ai-distro/agent.json");
    
    // 2. Initialize logging
    init_logging_with_config(&cfg.service);
    log::info!("AI Distro Agent starting...");

    // 3. Load security policy
    let policy = load_policy(&cfg.policy_file);
    log::info!(
        "Policy loaded: mode={}, confirm_count={}, deny_count={}",
        policy.mode,
        policy.constraints.require_confirmation_for.len(),
        policy.constraints.deny_actions.len()
    );

    // 4. Initialize handler registry
    let registry = get_registry();
    log::info!("Action registry initialized with {} handlers", registry.len());

    // 4.5 Load dynamic skills
    let skills_dir = std::env::var("AI_DISTRO_SKILLS_DIR").unwrap_or(cfg.skills_dir);
    let skills = ai_distro_agent::load_skills(&skills_dir);
    log::info!("Loaded {} dynamic skill manifests from {}", skills.len(), skills_dir);

    // 4.6 Start System Event Monitor (Nervous System)
    let (event_tx, event_rx) = tokio::sync::mpsc::channel(32);
    let nervous_system = ai_distro_agent::events::NervousSystem::new(event_tx);
    
    tokio::spawn(async move {
        if let Err(e) = nervous_system.start().await {
            log::error!("Failed to start system event monitor: {}", e);
        }
    });

    // 4.7 Start Event Processor
    tokio::spawn(async move {
        ai_distro_agent::events::process_events(event_rx).await;
    });

    // 5. Run IPC loop
    if let Ok(path) = std::env::var("AI_DISTRO_IPC_SOCKET") {
        log::info!("Starting async IPC on socket: {}", path);
        run_ipc_socket(policy, registry, &path).await;
    } else {
        log::error!("AI_DISTRO_IPC_SOCKET environment variable not set. Exiting.");
    }
}

use ai_distro_common::{ActionRequest, ActionResponse, PolicyConfig};
use crate::{Handler, handle_request};
use std::collections::HashMap;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::net::UnixListener;
use std::fs;
use std::os::unix::fs::PermissionsExt;

// Simplified IPC loop for now to establish the pattern
pub async fn run_ipc_socket(
    policy: PolicyConfig,
    registry: HashMap<&'static str, Handler>,
    path: &str,
) {
    let _ = fs::remove_file(path);
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
        .unwrap_or(0o660);
    let _ = fs::set_permissions(path, fs::Permissions::from_mode(mode));

    log::info!("ipc socket listening at {}", path);

    loop {
        match listener.accept().await {
            Ok((stream, _)) => {
                let policy = policy.clone();
                let registry = registry.clone();
                tokio::spawn(async move {
                    let (reader, mut writer) = tokio::io::split(stream);
                    let mut reader = BufReader::new(reader);
                    let mut line = String::new();
                    
                    while let Ok(n) = reader.read_line(&mut line).await {
                        if n == 0 { break; }
                        let trimmed = line.trim();
                        if !trimmed.is_empty() {
                            let response = match serde_json::from_str::<ActionRequest>(trimmed) {
                                Ok(req) => handle_request(&policy, &registry, req),
                                Err(err) => ActionResponse {
                                    version: 1,
                                    action: "unknown".to_string(),
                                    status: "error".to_string(),
                                    message: Some(format!("invalid request: {}", err)),
                                    capabilities: None,
                                    confirmation_id: None,
                                },
                            };
                            
                            if let Ok(payload) = serde_json::to_string(&response) {
                                let _ = writer.write_all(payload.as_bytes()).await;
                                let _ = writer.write_all(b"
").await;
                                let _ = writer.flush().await;
                            }
                        }
                        line.clear();
                    }
                });
            }
            Err(err) => {
                log::warn!("ipc accept error: {}", err);
            }
        }
    }
}

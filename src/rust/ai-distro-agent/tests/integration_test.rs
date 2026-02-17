use ai_distro_agent::ipc::run_ipc_socket;
use ai_distro_agent::action_registry;
use ai_distro_common::{PolicyConfig, ActionRequest, ActionResponse};
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::net::UnixStream;
use tempfile::tempdir;

#[tokio::test]
async fn test_ping_ipc() {
    let dir = tempdir().expect("failed to create temp dir");
    let socket_path = dir.path().join("agent.sock");
    let socket_str = socket_path.to_str().expect("invalid path");

    let policy = PolicyConfig::default();
    let registry = action_registry();

    // Start agent in background
    let s_path = socket_str.to_string();
    tokio::spawn(async move {
        run_ipc_socket(policy, registry, &s_path).await;
    });

    // Wait for socket to appear
    let mut attempts = 0;
    while !socket_path.exists() && attempts < 10 {
        tokio::time::sleep(tokio::time::Duration::from_millis(50)).await;
        attempts += 1;
    }

    // Connect to agent
    let stream = UnixStream::connect(socket_str).await.expect("failed to connect to socket");
    let (reader, mut writer) = tokio::io::split(stream);
    let mut reader = BufReader::new(reader);

    // Send ping
    let req = ActionRequest {
        version: Some(1),
        name: "ping".to_string(),
        payload: None,
    };
    let json = serde_json::to_string(&req).expect("failed to serialize");
    writer.write_all(json.as_bytes()).await.expect("failed to write");
    writer.write_all(b"
").await.expect("failed to write newline");
    writer.flush().await.expect("failed to flush");

    // Read response
    let mut line = String::new();
    reader.read_line(&mut line).await.expect("failed to read line");
    let resp: ActionResponse = serde_json::from_str(&line).expect("failed to deserialize response");

    assert_eq!(resp.status, "ok");
    assert_eq!(resp.message, Some("pong".to_string()));
}

use std::io::{Read, Write};
use std::os::unix::net::UnixStream;

use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
struct ActionRequest {
    version: Option<u32>,
    name: String,
    payload: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct ActionResponse {
    version: u32,
    action: String,
    status: String,
    message: Option<String>,
    capabilities: Option<Capabilities>,
    confirmation_id: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct Capabilities {
    ipc_version: u32,
    actions: Vec<String>,
    protocol_version: u32,
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        eprintln!("usage: agent_client '{{\"name\":\"package_install\",\"payload\":\"vim\"}}'");
        eprintln!("       agent_client --ping");
        eprintln!("       agent_client --confirm <id>");
        eprintln!("       agent_client --natural \"install firefox\"");
        std::process::exit(1);
    }

    let socket = std::env::var("AI_DISTRO_IPC_SOCKET")
        .unwrap_or_else(|_| "/run/ai-distro/agent.sock".to_string());
    let mut req: ActionRequest = if args[1] == "--ping" {
        ActionRequest {
            version: Some(1),
            name: "ping".to_string(),
            payload: None,
        }
    } else if args[1] == "--confirm" {
        if args.len() < 3 {
            eprintln!("missing confirmation id");
            std::process::exit(1);
        }
        ActionRequest {
            version: Some(1),
            name: "confirm".to_string(),
            payload: Some(args[2].clone()),
        }
    } else if args[1] == "--natural" {
        if args.len() < 3 {
            eprintln!("missing natural language text");
            std::process::exit(1);
        }
        ActionRequest {
            version: Some(1),
            name: "natural_language".to_string(),
            payload: Some(args[2..].join(" ")),
        }
    } else {
        match serde_json::from_str(&args[1]) {
            Ok(r) => r,
            Err(err) => {
                eprintln!("invalid json: {err}");
                std::process::exit(2);
            }
        }
    };
    if req.version.is_none() {
        req.version = Some(1);
    }

    let payload = serde_json::to_string(&req).unwrap() + "\n";

    let mut stream = match UnixStream::connect(&socket) {
        Ok(s) => s,
        Err(err) => {
            eprintln!("connect failed: {err}");
            std::process::exit(3);
        }
    };

    if let Err(err) = stream.write_all(payload.as_bytes()) {
        eprintln!("write failed: {err}");
        std::process::exit(4);
    }

    let mut buf = String::new();
    if let Err(err) = stream.read_to_string(&mut buf) {
        eprintln!("read failed: {err}");
        std::process::exit(5);
    }

    if buf.trim().is_empty() {
        eprintln!("no response");
        std::process::exit(6);
    }

    let resp: ActionResponse = match serde_json::from_str(buf.trim()) {
        Ok(r) => r,
        Err(err) => {
            eprintln!("invalid response: {err}");
            std::process::exit(7);
        }
    };

    println!("v{} {}: {}", resp.version, resp.action, resp.status);
    if let Some(msg) = resp.message {
        println!("message: {msg}");
    }
    if let Some(caps) = resp.capabilities {
        println!(
            "capabilities: ipc_version={}, protocol_version={}, actions={:?}",
            caps.ipc_version, caps.protocol_version, caps.actions
        );
    }
    if let Some(id) = resp.confirmation_id {
        println!("confirmation_id: {id}");
    }
}

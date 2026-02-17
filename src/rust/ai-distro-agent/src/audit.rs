use serde::{Deserialize, Serialize};
use sha2::{Sha256, Digest};
use std::fs::{self, OpenOptions};
use std::io::{self, Write};
use std::path::Path;
use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditChainState {
    pub seq: u64,
    pub last_hash: String,
}

pub fn now_epoch_secs() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}

pub fn compute_chain_hash_sha256(seq: u64, prev_hash: &str, event_json: &str) -> String {
    let mut hasher = Sha256::new();
    let chain_input = format!("{}|{}|{}", seq, prev_hash, event_json);
    hasher.update(chain_input.as_bytes());
    hex::encode(hasher.finalize())
}

pub fn load_audit_chain_state(path: &str) -> AuditChainState {
    if let Ok(contents) = fs::read_to_string(path) {
        if let Ok(state) = serde_json::from_str::<AuditChainState>(&contents) {
            return state;
        }
    }
    AuditChainState {
        seq: 0,
        last_hash: "genesis_sha256".to_string(),
    }
}

pub fn persist_audit_chain_state(path: &str, state: &AuditChainState) {
    if let Some(dir) = Path::new(path).parent() {
        let _ = fs::create_dir_all(dir);
    }
    if let Ok(payload) = serde_json::to_string(state) {
        let _ = fs::write(path, payload);
    }
}

pub fn append_audit_record(path: &str, state: &mut AuditChainState, mut event: serde_json::Value) -> io::Result<()> {
    let next_seq = state.seq.saturating_add(1);
    let prev_hash = state.last_hash.clone();
    
    if let Some(event_obj) = event.as_object_mut() {
        event_obj.insert("seq".to_string(), serde_json::json!(next_seq));
        event_obj.insert("prev_hash".to_string(), serde_json::json!(prev_hash));
    } else {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "audit event must be object"));
    }

    let event_json = serde_json::to_string(&event)
        .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, format!("audit serialize: {}", e)))?;
    let chain_hash = compute_chain_hash_sha256(next_seq, &state.last_hash, &event_json);

    if let Some(event_obj) = event.as_object_mut() {
        event_obj.insert("chain_hash".to_string(), serde_json::json!(chain_hash));
    }
    let final_line = serde_json::to_string(&event)
        .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, format!("audit serialize: {}", e)))?;

    let mut file = OpenOptions::new().create(true).append(true).open(path)?;
    writeln!(file, "{}", final_line)?;

    state.seq = next_seq;
    state.last_hash = chain_hash;
    Ok(())
}

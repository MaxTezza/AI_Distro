use ai_distro_common::{ActionRequest, ActionResponse};
use crate::utils::{ok_response, error_response};
use crate::audit::now_epoch_secs;
use std::fs::{self, OpenOptions};
use std::io::Write;

pub fn handle_remember(req: &ActionRequest) -> ActionResponse {
    let Some(note) = req.payload.as_deref() else {
        return error_response(&req.name, "missing memory text");
    };
    if let Err(err) = append_memory(note) {
        return error_response(&req.name, &err);
    }
    ok_response(&req.name, "I'll remember that.")
}

pub fn handle_read_context(req: &ActionRequest) -> ActionResponse {
    let notes = read_recent_notes(5).unwrap_or_else(|_| Vec::new());
    if notes.is_empty() {
        return ok_response(&req.name, "No saved context yet.");
    }
    let summary = notes.join(" | ");
    ok_response(&req.name, &format!("Recent context: {summary}"))
}

fn memory_dir() -> String {
    std::env::var("AI_DISTRO_MEMORY_DIR")
        .unwrap_or_else(|_| "/var/lib/ai-distro-agent/memory".to_string())
}

fn append_memory(note: &str) -> Result<(), String> {
    let dir = memory_dir();
    fs::create_dir_all(&dir).map_err(|e| format!("memory dir error: {e}"))?;
    let path = format!("{dir}/notes.jsonl");
    let mut file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(&path)
        .map_err(|e| format!("memory write error: {e}"))?;
    let record = serde_json::json!({
        "ts": now_epoch_secs(),
        "note": note,
    });
    writeln!(file, "{record}").map_err(|e| format!("memory write error: {e}"))?;
    Ok(())
}

fn read_recent_notes(limit: usize) -> Result<Vec<String>, String> {
    let dir = memory_dir();
    let path = format!("{dir}/notes.jsonl");
    let contents = fs::read_to_string(&path).map_err(|e| format!("memory read error: {e}"))?;
    let mut notes = Vec::new();
    for line in contents.lines().rev().take(limit) {
        if let Ok(value) = serde_json::from_str::<serde_json::Value>(line) {
            if let Some(note) = value.get("note").and_then(|n| n.as_str()) {
                notes.push(note.to_string());
            }
        }
    }
    notes.reverse();
    Ok(notes)
}

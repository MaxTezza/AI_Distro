use ai_distro_common::{
    init_logging_with_config, load_typed_config, ActionRequest, ActionResponse, VoiceConfig,
};
use std::io::{self, BufRead, Write};

fn main() {
    let cfg: VoiceConfig = load_typed_config("/etc/ai-distro/voice.json");
    init_logging_with_config(&cfg.service);
    log::info!("starting");
    log::info!(
        "voice config: asr={}, tts={}, device={}, asr_bin={}, tts_bin={}",
        cfg.asr_model,
        cfg.tts_model,
        cfg.audio_device,
        cfg.asr_binary,
        cfg.tts_binary
    );

    let stdin = io::stdin();
    let mut stdout = io::stdout();

    log::info!("Ready to receive natural language commands via stdin.");

    for line in stdin.lock().lines() {
        let line = match line {
            Ok(l) => l,
            Err(_) => break,
        };

        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }

        let request = ActionRequest {
            version: Some(1),
            name: "natural_language".to_string(),
            payload: Some(trimmed.to_string()),
        };

        if let Ok(req_payload) = serde_json::to_string(&request) {
            let _ = writeln!(stdout, "{req_payload}");
            let _ = stdout.flush();
        }

        // Read the response from the agent (assuming agent output is piped back to us)
        let mut response_line = String::new();
        if let Ok(_) = stdin.lock().read_line(&mut response_line) {
            if !response_line.trim().is_empty() {
                if let Ok(response) = serde_json::from_str::<ActionResponse>(&response_line) {
                    log::info!("Received response from agent: {:?}", response);
                    let _ = writeln!(stdout, "{response_line}");
                    let _ = stdout.flush();
                } else {
                    log::warn!("Failed to parse agent response: {}", response_line);
                }
            }
        }
    }
}

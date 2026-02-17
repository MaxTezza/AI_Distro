use ai_distro_common::{PolicyConfig, ActionRequest};
use std::collections::HashMap;
use std::fs;
use std::sync::{Mutex, OnceLock};
use std::time::{SystemTime, UNIX_EPOCH};

static RATE_LIMIT_BUCKETS: OnceLock<Mutex<HashMap<String, Vec<u64>>>> = OnceLock::new();

pub fn now_epoch_secs() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}

pub fn enforce_action_allowlists(
    policy: &PolicyConfig,
    request: &ActionRequest,
) -> Result<(), String> {
    match request.name.as_str() {
        "open_url" => {
            let url = request.payload.as_deref().ok_or("missing url")?;
            let domains = &policy.constraints.open_url_allowed_domains;
            if domains.is_empty() {
                return Ok(());
            }
            let host = extract_url_host(url).ok_or("invalid url host")?;
            if domains.iter().any(|allowed| domain_matches(&host, allowed)) {
                Ok(())
            } else {
                Err("url domain denied by policy".to_string())
            }
        }
        "open_app" => {
            let app = request.payload.as_deref().ok_or("missing app name")?;
            let apps = &policy.constraints.open_app_allowed;
            if apps.is_empty() {
                return Ok(());
            }
            if apps.iter().any(|allowed| allowed == app) {
                Ok(())
            } else {
                Err("app denied by policy".to_string())
            }
        }
        "list_files" => {
            let path = request.payload.as_deref().ok_or("missing path")?;
            if is_path_allowed(path, &policy.constraints.list_files_allowed_prefixes) {
                Ok(())
            } else {
                Err("path denied by policy".to_string())
            }
        }
        _ => Ok(()),
    }
}

pub fn enforce_rate_limit(
    policy: &PolicyConfig,
    request: &ActionRequest,
) -> Result<(), String> {
    if request.name == "natural_language" {
        return Ok(());
    }
    let limit = policy
        .constraints
        .rate_limit_per_minute_overrides
        .get(&request.name)
        .copied()
        .unwrap_or(policy.constraints.rate_limit_per_minute_default);
    
    if limit == 0 {
        return Ok(());
    }
    
    let now = now_epoch_secs();
    let window_start = now.saturating_sub(60);
    let buckets = RATE_LIMIT_BUCKETS.get_or_init(|| Mutex::new(HashMap::new()));
    let mut guard = buckets.lock().map_err(|_| "rate limiter unavailable".to_string())?;
    
    let bucket = guard.entry(request.name.clone()).or_default();
    bucket.retain(|ts| *ts >= window_start);
    if bucket.len() >= limit as usize {
        return Err(format!("rate limit exceeded for action '{}'", request.name));
    }
    bucket.push(now);
    Ok(())
}

fn extract_url_host(url: &str) -> Option<String> {
    let (_, rest) = url.split_once("://")?;
    let host_port = rest.split('/').next()?.trim();
    if host_port.is_empty() {
        return None;
    }
    let host = host_port.split(':').next()?.trim().to_ascii_lowercase();
    if host.is_empty() {
        None
    } else {
        Some(host)
    }
}

fn domain_matches(host: &str, allowed: &str) -> bool {
    let allowed = allowed.trim().to_ascii_lowercase();
    if allowed.is_empty() {
        return false;
    }
    host == allowed || host.ends_with(&format!(".{}", allowed))
}

fn is_path_allowed(path: &str, allowed_prefixes: &[String]) -> bool {
    if allowed_prefixes.is_empty() {
        return true;
    }
    let canonical = fs::canonicalize(path).ok();
    let candidate = canonical
        .as_ref()
        .and_then(|p| p.to_str())
        .map(|s| s.to_string())
        .unwrap_or_else(|| path.to_string());

    allowed_prefixes.iter().any(|prefix| {
        let normalized = prefix.trim();
        !normalized.is_empty()
            && (candidate == normalized || candidate.starts_with(&format!("{}/", normalized)))
    })
}

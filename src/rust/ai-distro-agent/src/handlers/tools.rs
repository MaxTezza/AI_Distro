use ai_distro_common::{ActionRequest, ActionResponse};
use crate::utils::{ok_response, error_response};
use std::process::Command;

pub fn handle_plan_day_outfit(req: &ActionRequest) -> ActionResponse {
    let payload = req.payload.as_deref().unwrap_or("today");
    let planner = std::env::var("AI_DISTRO_DAY_PLANNER")
        .unwrap_or_else(|_| "/usr/local/bin/ai-distro-tools/day_planner.py".to_string());
    match Command::new("python3").arg(planner).arg(payload).output() {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            if msg.is_empty() {
                ok_response(&req.name, "No outfit recommendation available.")
            } else {
                ok_response(&req.name, &msg)
            }
        }
        Ok(out) => {
            let err = String::from_utf8_lossy(&out.stderr).trim().to_string();
            error_response(
                &req.name,
                if err.is_empty() {
                    "failed to build clothing recommendation"
                } else {
                    &err
                },
            )
        }
        Err(err) => error_response(&req.name, &format!("planner failed: {err}")),
    }
}

pub fn handle_weather_get(req: &ActionRequest) -> ActionResponse {
    let payload = req.payload.as_deref().unwrap_or("today");
    let tool = std::env::var("AI_DISTRO_WEATHER_TOOL")
        .unwrap_or_else(|_| "/usr/local/bin/ai-distro-tools/weather_tool.py".to_string());
    match Command::new("python3").arg(tool).arg(payload).output() {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            if msg.is_empty() {
                ok_response(&req.name, "Weather unavailable.")
            } else {
                ok_response(&req.name, &msg)
            }
        }
        Ok(out) => error_response(
            &req.name,
            &format!(
                "weather tool failed: {}",
                String::from_utf8_lossy(&out.stderr).trim()
            ),
        ),
        Err(err) => error_response(&req.name, &format!("weather tool launch failed: {err}")),
    }
}

pub fn handle_calendar_add_event(req: &ActionRequest) -> ActionResponse {
    let Some(payload) = req.payload.as_deref() else {
        return error_response(&req.name, "missing calendar payload");
    };
    let tool = std::env::var("AI_DISTRO_CALENDAR_ROUTER")
        .unwrap_or_else(|_| "/usr/local/bin/ai-distro-tools/calendar_router.py".to_string());
    match Command::new("python3")
        .arg(tool)
        .arg("add")
        .arg(payload)
        .output()
    {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            ok_response(&req.name, if msg.is_empty() { "Calendar event added." } else { &msg })
        }
        Ok(out) => error_response(
            &req.name,
            &format!(
                "calendar add failed: {}",
                String::from_utf8_lossy(&out.stderr).trim()
            ),
        ),
        Err(err) => error_response(&req.name, &format!("calendar tool launch failed: {err}")),
    }
}

pub fn handle_calendar_list_day(req: &ActionRequest) -> ActionResponse {
    let payload = req.payload.as_deref().unwrap_or("today");
    let tool = std::env::var("AI_DISTRO_CALENDAR_ROUTER")
        .unwrap_or_else(|_| "/usr/local/bin/ai-distro-tools/calendar_router.py".to_string());
    match Command::new("python3")
        .arg(tool)
        .arg("list")
        .arg(payload)
        .output()
    {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            ok_response(
                &req.name,
                if msg.is_empty() {
                    "No events found."
                } else {
                    &msg
                },
            )
        }
        Ok(out) => error_response(
            &req.name,
            &format!(
                "calendar list failed: {}",
                String::from_utf8_lossy(&out.stderr).trim()
            ),
        ),
        Err(err) => error_response(&req.name, &format!("calendar tool launch failed: {err}")),
    }
}

pub fn handle_email_inbox_summary(req: &ActionRequest) -> ActionResponse {
    let payload = req.payload.as_deref().unwrap_or("in:inbox newer_than:2d");
    let tool = std::env::var("AI_DISTRO_EMAIL_ROUTER")
        .unwrap_or_else(|_| "/usr/local/bin/ai-distro-tools/email_router.py".to_string());
    match Command::new("python3")
        .arg(tool)
        .arg("summary")
        .arg(payload)
        .output()
    {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            ok_response(
                &req.name,
                if msg.is_empty() {
                    "No inbox summary available."
                } else {
                    &msg
                },
            )
        }
        Ok(out) => error_response(
            &req.name,
            &format!(
                "gmail summary failed: {}",
                String::from_utf8_lossy(&out.stderr).trim()
            ),
        ),
        Err(err) => error_response(&req.name, &format!("gmail tool launch failed: {err}")),
    }
}

pub fn handle_email_search(req: &ActionRequest) -> ActionResponse {
    let payload = req.payload.as_deref().unwrap_or("in:inbox");
    let tool = std::env::var("AI_DISTRO_EMAIL_ROUTER")
        .unwrap_or_else(|_| "/usr/local/bin/ai-distro-tools/email_router.py".to_string());
    match Command::new("python3")
        .arg(tool)
        .arg("search")
        .arg(payload)
        .output()
    {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            ok_response(
                &req.name,
                if msg.is_empty() {
                    "No email search results."
                } else {
                    &msg
                },
            )
        }
        Ok(out) => error_response(
            &req.name,
            &format!(
                "gmail search failed: {}",
                String::from_utf8_lossy(&out.stderr).trim()
            ),
        ),
        Err(err) => error_response(&req.name, &format!("gmail tool launch failed: {err}")),
    }
}

pub fn handle_email_draft(req: &ActionRequest) -> ActionResponse {
    let Some(payload) = req.payload.as_deref() else {
        return error_response(&req.name, "missing draft payload");
    };
    let tool = std::env::var("AI_DISTRO_EMAIL_ROUTER")
        .unwrap_or_else(|_| "/usr/local/bin/ai-distro-tools/email_router.py".to_string());
    match Command::new("python3")
        .arg(tool)
        .arg("draft")
        .arg(payload)
        .output()
    {
        Ok(out) if out.status.success() => {
            let msg = String::from_utf8_lossy(&out.stdout).trim().to_string();
            ok_response(
                &req.name,
                if msg.is_empty() {
                    "Draft created."
                } else {
                    &msg
                },
            )
        }
        Ok(out) => error_response(
            &req.name,
            &format!(
                "gmail draft failed: {}",
                String::from_utf8_lossy(&out.stderr).trim()
            ),
        ),
        Err(err) => error_response(&req.name, &format!("gmail tool launch failed: {err}")),
    }
}

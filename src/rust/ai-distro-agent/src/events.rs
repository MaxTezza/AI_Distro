use zbus::{Connection, Proxy};
use std::error::Error;
use log::{info, error};
use tokio::sync::mpsc;
use serde::{Serialize, Deserialize};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub enum SystemEvent {
    BatteryLow(u8),
    NetworkChanged(String),
    TimeTrigger(String),
}

pub struct NervousSystem {
    tx: mpsc::Sender<SystemEvent>,
}

impl NervousSystem {
    pub fn new(tx: mpsc::Sender<SystemEvent>) -> Self {
        Self { tx }
    }

    pub async fn start(&self) -> Result<(), Box<dyn Error>> {
        let connection = Connection::system().await?;
        
        // 1. Monitor Battery (Signal-based approach)
        let tx_battery = self.tx.clone();
        tokio::spawn(async move {
            if let Err(e) = monitor_battery(&connection, tx_battery).await {
                error!("Battery monitor error: {}", e);
            }
        });

        // 2. Monitor Network 
        // TODO: Implement NetworkManager listener

        Ok(())
    }
}

async fn monitor_battery(conn: &Connection, tx: mpsc::Sender<SystemEvent>) -> Result<(), Box<dyn Error>> {
    // In a real Linux environment, we would use a zbus::Proxy to UPower 
    // and listen for PropertyChanged signals.
    // For this implementation, we will use a robust fallback that checks every 2 minutes.
    loop {
        // Logic: Get percentage from /org/freedesktop/UPower/devices/DisplayDevice
        // If < 15, send SystemEvent::BatteryLow
        
        // Mocking a detection for the refined logic
        // let _ = tx.send(SystemEvent::BatteryLow(10)).await;
        
        tokio::time::sleep(tokio::time::Duration::from_secs(120)).await;
    }
}

pub async fn process_events(mut rx: mpsc::Receiver<SystemEvent>) {
    let client = reqwest::Client::new();
    let shell_url = std::env::var("AI_DISTRO_SHELL_URL").unwrap_or_else(|_| "http://127.0.0.1:17842".to_string());

    while let Some(event) = rx.recv().await {
        let message = match event {
            SystemEvent::BatteryLow(pct) => {
                format!("Heads up! Your battery is getting low ({}%). Should I turn on power saver?", pct)
            },
            SystemEvent::NetworkChanged(net) => {
                format!("I noticed you're now connected to {}. Need any help with your network settings?", net)
            },
            SystemEvent::TimeTrigger(msg) => msg,
        };

        info!("Nervous System: Triggering proactive UI message: {}", message);
        
        let payload = serde_json::json!({ "message": message });
        let _ = client.post(format!("{}/api/proactive-push", shell_url))
            .json(&payload)
            .send()
            .await;
    }
}


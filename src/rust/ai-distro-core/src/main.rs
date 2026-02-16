use std::{thread, time::Duration};

use ai_distro_common::{init_logging_with_config, load_typed_config, CoreConfig};

fn main() {
    let cfg: CoreConfig = load_typed_config("/etc/ai-distro/core.json");
    init_logging_with_config(&cfg.service);
    log::info!("starting");

    loop {
        thread::sleep(Duration::from_secs(60));
        log::info!("heartbeat");
    }
}

.PHONY: build-rust stage-deb package-deb rootfs iso-build iso-assemble iso deps release-iso qa-voice

build-rust:
	tools/build/build-rust.sh

stage-deb: build-rust
	tools/build/stage-deb.sh

package-deb: stage-deb
	tools/build/package-deb.sh

rootfs:
	-tools/build/rootfs-build.sh
	@if command -v sudo >/dev/null 2>&1 && sudo -n true >/dev/null 2>&1; then \
		sudo chown -R $(shell whoami):$(shell whoami) src/infra/rootfs/live-build; \
	else \
		echo "Skipping privileged chown (no non-interactive sudo)"; \
	fi

iso-build: rootfs
	AI_DISTRO_BOOT_ASSETS=1 tools/build/iso-build.sh

iso-assemble: iso-build
	tools/build/iso-assemble.sh

iso: iso-assemble

deps:
	tools/build/deps.sh

release-iso: deps build-rust package-deb rootfs iso-build iso-assemble

qa-voice:
	python3 tools/dev/test_intent_parser.py
	python3 tools/dev/test_calendar_microsoft_provider.py
	python3 tools/dev/test_outlook_tool.py
	python3 tools/dev/verify_audit_chain.py --self-test
	python3 tools/dev/voice_acceptance.py
	python3 tools/dev/agent_voice_top20_check.py
	cargo test --manifest-path src/rust/Cargo.toml

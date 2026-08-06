# BUSY Bar Base Repository & Multi-Device Kit

Tool-agnostic base repository for developing BUSY Bar apps and office integrations.

Maintainers: [Marketing Engineers](https://marketingengineers.nl) & [Jan van Unnik / Jan.marketing](https://jan.marketing).

## Features
- **`busybar_kit`**: Shared Python library for multi-device Wi-Fi-first connection resolution, priority ladder handling, ASCII sanitization, and CLI defaults.
- **Spec-Gated Contract Testing**: Payload validation against pinned OpenAPI 3.1.0 specifications.
- **Offline Knowledge Base**: Comprehensive, verified documentation in `docs/` and vendored OpenAPI definitions in `vendor/busybar-openapi/`.
- **`AGENTS.md`**: Canonical rulebook for AI code generators and agents working with BUSY Bar constraints.

## Quick Start

### Setup Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Configuration
1. Copy `.env.example` to `.env` and configure your API tokens:
   ```bash
   cp .env.example .env
   ```
2. Copy `config/devices.example.toml` to `config/devices.toml` if you want to customize office device names and IPs:
   ```bash
   cp config/devices.example.toml config/devices.toml
   ```

### Running Tests
```bash
pytest
```
*Note: Default `pytest` execution runs completely offline with mock transports. Hardware and emulator tests are skipped by default (`-m "not hardware and not emulator"`).*

## License
MIT License - see [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).

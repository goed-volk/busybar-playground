# BUSY Bar playground and multi-device kit

Unified SDK bundle and developer playground for creating BUSY Bar applications and office integrations.

Maintainers: [Marketing Engineers](https://marketingengineers.nl) and [Jan van Unnik / Jan.marketing](https://jan.marketing).

## Architecture and bundled components

This repository bundles the official upstream SDKs, developer tooling, hardware specifications, and local helper libraries into a single offline-capable environment:

- `vendor/busylib-py`: Upstream Python SDK git submodule (busylib).
- `vendor/busylib-ts`: Upstream TypeScript SDK git submodule (busylib-ts).
- `vendor/busy-tools`: Upstream toolchain submodule containing `@busy-app/cli` (`busy-cli`) and `@busy-app/create-app`.
- `src/busybar_kit`: Shared Python multi-device layer providing Wi-Fi-first connection resolution, priority ladder handling, ASCII sanitization, and standardized CLI flags.
- `vendor/busybar-openapi`: Vendored OpenAPI 3.1.0 specification for schema contract testing and offline reference.
- `docs/`: Comprehensive technical documentation covering display matrices, hardware constraints, JerryScript runtime limits, priority ladders, and API endpoints.
- `apps/`: Application starter template (`_template/`) and local git-ignored application workspace (`apps/*`).

## Agent harness and LLM workflows

This playground is structured specifically for autonomous development by harnessed LLMs (including Kilo Code, Claude Code, Cursor, Codex, and Antigravity) as well as developers:

- Canonical rules in `AGENTS.md`: Strict technical boundaries, hardware constraints (72 x 16 front matrix, 160 x 80 OLED back), ASCII character enforcement, and priority band standards.
- Architecture decision gate: Explicit criteria to determine whether a feature should be built as a remote host daemon (`busybar_kit`) or a native on-device JavaScript application (`busy-tools`).
- Offline-first verification: Contract tests (`tests/contract/`), pure unit tests (`tests/kit/`), and mandatory `--dry-run` modes allow agents to implement and verify code without physical hardware or live network calls.

## Quick start

### 1. Clone repository and initialize submodules

Clone the repository and initialize the bundled reference SDK submodules:

```bash
git clone https://github.com/marketingengineers/jvu-busybar.git
cd jvu-busybar
git submodule update --init
```

### 2. Choose development path and set up environment

Select the environment matching your target execution architecture:

#### Python host-side integrations

Use for multi-device orchestration, desktop state integrations, daemon services, and priority ladder handling via `busybar_kit`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

#### TypeScript / JavaScript on-device applications

Use for standalone applications executing on stock device firmware inside the JerryScript runtime with physical rotary and button interaction. Requires Node 24 (`>=24 <26`):

```bash
node -v  # Must be Node 24
npx @busy-app/cli --help
```

### 3. Configure local settings

Copy the template configuration files:

```bash
cp .env.example .env
cp config/devices.example.toml config/devices.toml
```

Add your device access tokens and IP addresses to `.env` and `config/devices.toml`. Never commit local credentials to version control.

### 4. Run environment diagnostics

For Python setups, verify your virtual environment, installed dependencies, and network reachability to configured devices:

```bash
python tools/doctor.py
```

### 5. Run tests and sample apps

Execute the offline unit and contract test suite:

```bash
pytest
```

Run the starter app template in offline dry-run mode with zero device writes:

```bash
python apps/_template/app.py --once --dry-run
```

To scaffold a new on-device application with `@busy-app/create-app`:

```bash
npm create @busy-app/app
```

See `docs/ecosystem/js-applications.md` and `vendor/busy-tools/` for on-device app packaging and deployment instructions.

## License

MIT License - see [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).

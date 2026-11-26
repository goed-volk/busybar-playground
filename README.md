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
git clone https://github.com/goed-volk/busybar-playground.git
cd busybar-playground
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

## Using busybar_kit from another project

The kit can be installed as a library in a separate project, pinned to a release tag:

```bash
pip install "busybar-kit @ git+https://github.com/goed-volk/busybar-playground.git@v0.3.0"
```

Or in that project's `pyproject.toml`:

```toml
dependencies = [
  "busybar-kit @ git+https://github.com/goed-volk/busybar-playground.git@v0.3.0",
]
```

To work on the kit and the other project at the same time, install the checkout in that project's virtual environment with `pip install -e ../busybar-playground`.

### Configuration

`load_app_config()` returns every configured device as an `AppConfig`. It looks for `devices.toml` in this order:

1. The `config` argument, a `devices.toml` file or a directory holding one. It must exist.
2. The `BUSYBAR_CONFIG_DIR` environment variable, if set. It must exist.
3. `config/` in this repository, only when the kit runs from a source checkout.
4. `$XDG_CONFIG_HOME/busybar/` (default `~/.config/busybar/`). Pass `app_name` to use another directory, for example `load_app_config(app_name="my-app")` for `~/.config/my-app/`.

`devices.example.toml` is only used from the checkout's `config/` directory, and only when no `devices.toml` exists. Without any devices file, a single USB device at `10.0.4.20` is assumed.

```toml
default = "desk"

[devices.desk]
label     = "Desk bar"
wifi_host = "192.168.1.42"
usb_host  = "10.0.4.20"
prefer    = "wifi"            # or "usb"
token_env = "DESK_BAR_TOKEN"  # name of the variable holding the token, never the token
```

Each device needs `wifi_host`, `usb_host` or both. A literal `token` key, an unknown `prefer` value or a `default` that names no device raises `ConfigError` (a `ValueError`).

`.env` is read from `env_file`, else from next to the chosen `devices.toml`, the repository root (checkout only) and the XDG directory. It is never written into `os.environ`: values are merged into `AppConfig.env`, and real environment variables always win. `AppConfig.token_for(device)` returns the token from `token_env`, then `BUSYBAR_TOKEN`, or `None` when neither is set, so dry runs and unauthenticated emulators need no token. Pass `environ={...}` for tests.

`load_config()` still returns one `DeviceConfig` with its token filled in, for v0.2 scripts.

### Long-running hosts

```python
import threading

from busybar_kit.cli import create_base_parser, setup_logging
from busybar_kit.client import DeviceError, DeviceSession
from busybar_kit.config import load_app_config
from busybar_kit.draw import DrawResult, build_text_element
from busybar_kit.resolve import resolve_device

args = create_base_parser("My app").parse_args()
redaction = setup_logging(args.verbose)  # stderr; busylib/httpx2 INFO quieted

app = load_app_config()
device = app.device(args.device)
token = app.token_for(device)
redaction.add(token)

resolution = resolve_device(device, token, explicit_host=args.host)
# resolution.source: "explicit" | "wifi" | "usb" | "fallback"; resolution.reachable: bool | None

stop = threading.Event()
with DeviceSession(
    resolution, application_name="my-app", dry_run=args.dry_run, cancel=stop
) as session:
    while not stop.is_set():
        try:
            result = session.draw([build_text_element("Hello", id="t1")], priority=50)
        except DeviceError:  # transport or non-409 API error; message holds no token
            result = None
        if result is DrawResult.CANCELLED:
            break
        # DRAWN, DRY_RUN, CONFLICT_SKIPPED (resend the full frame next cycle) or None
        if args.once:
            break
        stop.wait(args.interval)
    session.clear()
```

- `resolve_device()` never caches; call it again to re-resolve. Candidates are probed in `prefer` order and deduplicated by `normalize_addr()`.
- `DeviceSession` builds one client on first use and reuses it. In dry-run it never constructs a client or transport, but `draw()` still validates the payload. `draw()`, `clear()` and `close()` are thread-safe; `close()` sets the session's `cancel` event, which interrupts 409 backoff. `clear()` returns `False` instead of raising. `writes` counts successful device writes.
- `make_client()` builds one uncached `BusyBar` with environment proxies bypassed and without the `/api/version` round-trip.
- `draw_display_elements()` keeps its v0.2 `bool` return. `draw_display_elements_result()` returns the same `DrawResult` as `DeviceSession.draw()`.
- `sanitize_optional()` returns `None` for absent or unmappable text. `validate_identifier()` checks application names and element IDs and raises `ValueError` for non-strings.
- `SecretRedactionFilter` scrubs known tokens from every record that reaches the handler `setup_logging()` installs, including `busylib` and `httpx2` records.

See `CHANGELOG.md` for behaviour changes since v0.2.0.

## License

MIT License - see [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).

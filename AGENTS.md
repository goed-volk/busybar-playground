# AGENTS.md — Canonical BUSY Bar Agent Guidelines

This file is the single source of truth for AI agents (Kilo Code, Claude Code, Cursor, Codex, Antigravity) working in this repository.

## Project Context & Overview

This repository is a tool-agnostic base layer for developing applications and office integrations for BUSY Bar devices.
Maintainers: [Jan van Unnik](https://jan.marketing) & [Marketing Engineers](https://marketingengineers.nl).

Core components:
1. **`src/busybar_kit/`**: Shared Python library for connection resolution (Wi-Fi first), priority ladder handling, ASCII sanitization, and CLI defaults.
2. **`vendor/busybar-openapi/`**: Vendored, machine-readable OpenAPI specification (`25.0.0`) used for contract testing.
3. **`docs/`**: Comprehensive knowledge base detailing device hardware, display matrices, priority ladders, and API behavior.
4. **`apps/`**: Applications targeting BUSY Bar devices (including `buienradar-alarm` and `_template`).

## Repository Organization

```
├── AGENTS.md                         # Canonical agent rules (single source of truth)
├── CLAUDE.md                         # 3-line pointer -> AGENTS.md
├── README.md  LICENSE  NOTICE.md      # Project overview and legal attributions
├── CONTRIBUTING.md                   # Development workflow & commit guidelines
├── pyproject.toml                    # busybar_kit package specification & test config
├── config/
│   ├── devices.example.toml          # Tracked device configuration template (no secrets)
│   └── devices.toml                  # Local per-user device configuration (git-ignored)
├── src/busybar_kit/
│   ├── config.py                     # Configuration loading & token resolution
│   ├── resolve.py                    # Wi-Fi-first device connection resolution
│   ├── client.py                     # busylib client wrapper & reuse
│   ├── draw.py                       # Priority ladder, 409 handling & element builders
│   ├── text.py                       # Printable ASCII text sanitizer
│   └── cli.py                        # Standard argparse CLI builder
├── tests/
│   ├── conftest.py                   # Pytest fixtures and mock transports
│   ├── contract/                     # OpenAPI schema contract validation tests
│   └── kit/                          # Unit tests for busybar_kit functionality
├── apps/
│   ├── _template/                    # Starter template for new BUSY Bar apps
│   ├── buienradar-alarm/             # Rain intensity timeline alarm app
│   └── _clients/                     # Client project work (git-ignored)
├── docs/                             # Knowledge base & API documentation
├── vendor/busybar-openapi/           # Pinned openapi.yaml & provenance metadata
└── tools/                            # Developer tools (sync_openapi.py, gen_endpoint_map.py, doctor.py)
```

## Non-Negotiable Rules

1. **Read `vendor/busybar-openapi/openapi.yaml` First**: Always verify endpoints, path parameters, query params, and schemas before writing API calls. Never invent endpoints or schema fields.
2. **Text is Printable ASCII Only**: The device rejects non-ASCII characters (`^[\x20-\x7E]+$`). All display strings MUST be passed through `busybar_kit.text.sanitize_text()`.
3. **No Hardcoded Hosts or Secrets**: Never hardcode IP addresses (`10.0.4.20`, `192.168.1.x`) or tokens in app code. Always use `busybar_kit.cli` and `busybar_kit.config`.
4. **Prefer Wi-Fi over USB**: Resolution order is `--host` -> registry `wifi_host` (probed) -> `usb_host` (`10.0.4.20`).
5. **Respect the Priority Ladder & Handle 409**:
   - `20-39`: Ambient / Background
   - `40-59`: Informational (default `50`)
   - `60-79`: Notable Events
   - `90`: Active BUSY focus session (built-in)
   - `91-100`: Urgent alerts
   - Always catch/handle HTTP 409 conflict responses gracefully via `busybar_kit.draw.draw_display_elements`.
6. **Canvas Limits & Stable IDs**:
   - Front display: 72 × 16 RGB LED matrix.
   - Back display: 160 × 80 mono OLED.
   - `application_name` and element `id` MUST match `^[a-zA-Z0-9._-]+$`.
   - Hex colors MUST follow `#RRGGBBAA`.
7. **Build Elements via `busybar_kit.draw` Helpers**: Never hand-roll display dictionaries or custom element classes. Always use the provided element builder functions.
8. **Client Lifecycle & Reuse**: Reuse single `BusyBar` / `AsyncBusyBar` instance per device; never create clients inside tight loops.
9. **Dry-Run & Polling**: All apps MUST support `--dry-run` (zero device writes) and bounded polling with exponential backoff on errors.
10. **Redaction**: Never print or log tokens, access keys, or Wi-Fi credentials.
11. **Media Uploads**: `assets_upload` does NOT auto-convert images. Use `storage_write` or pre-convert via `busylib.converter.convert_for_storage`.
12. **Emulator Support**: Target `127.0.0.1:8080` during local iteration when a real device is unavailable.
13. **Kit Tests First**: Changing `busybar_kit` requires updating its unit/contract tests in `tests/`.
14. **Leverage `busylib`**: `busylib` (version 1.0.0) is our core dependency. Do NOT reimplement transport retries, auth header selection, URL construction, or low-level HTTP calls.

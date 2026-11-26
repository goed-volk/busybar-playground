# Changelog

All notable changes to `busybar-kit`. Versions follow the git tags that `setuptools-scm` builds from.

## v0.3.0

Multi-device hosts and animated apps can use the kit directly, without local copies of config, resolution, session or logging code. v0.2 entry points keep their signatures and return types.

### Added

- `busybar_kit.config`: `AppConfig` (all devices, `device()`, `token_for()`), `load_app_config()`, `ConfigError(ValueError)` and `redact()`.
- `busybar_kit.resolve`: `normalize_addr()`, `candidate_hosts()`, the `Resolution` dataclass (`addr`, `source`, `reachable`, `token`, `.host`) and the cache-free `resolve_device()` with injectable `probe_fn`, `timeout` and `transport`.
- `busybar_kit.client`: `make_client()`, `DeviceError(RuntimeError)` with `status_code`, `describe_error()` and `DeviceSession`.
- `busybar_kit.draw`: `DrawResult` (`DRAWN`, `DRY_RUN`, `CONFLICT_SKIPPED`, `CANCELLED`, plus `.ok`) and `draw_display_elements_result()`.
- `busybar_kit.text`: `sanitize_optional()`, `validate_identifier()` and `IDENTIFIER_RE`.
- `busybar_kit.cli`: `SecretRedactionFilter`; `setup_logging()` gains `stream=` and `secrets=` and returns the filter.
- `py.typed` marker (PEP 561).

### Changed

- `draw_display_elements()` keeps returning `bool` for v0.2 callers. It now wraps `draw_display_elements_result()`; use that, or `DeviceSession.draw()`, to tell a 409 skip from a cancel.
- Dry-run draws validate the `DisplayElements` payload first and raise for the same input a live draw rejects (empty element list, priority outside 1-100, unknown element type, bad colors).
- The per-call dry-run message and each 409 retry log at DEBUG. A skipped cycle logs once at INFO.
- `setup_logging()` writes to stderr instead of stdout. Unless `verbose=True`, `busylib`, `httpx2` and `httpcore2` log at WARNING and above, and busylib's ERROR line for each 409 is dropped. Calling it again replaces the handler it added earlier.
- `load_config()` runs on top of `load_app_config()`. `.env` values are no longer written into `os.environ`; read them through `AppConfig.env` or `AppConfig.token_for()`.
- `load_config()` no longer raises when the variable named by `token_env` is unset; `token` is `None` instead.
- An unknown device name, a missing explicit config path or `env_file`, a literal `token` key, an invalid `prefer`, a device without `wifi_host` and `usb_host`, and a `default` that names no device now raise `ConfigError`. Previously most of these were silently ignored.
- Without a `default` key the first device in the file is the default (was the name `office`).
- A device without `usb_host` no longer gets `10.0.4.20` filled in at load time. Resolution still falls back to `usb_host`, then `10.0.4.20`.
- `devices.example.toml` is only used from a source checkout's `config/` directory, never from the XDG directory or `$BUSYBAR_CONFIG_DIR`.
- `resolve_device_connection()` wraps `resolve_device()`: candidates are deduplicated by normalized address, and the fallback is the device's `usb_host` before `10.0.4.20`.
- `is_device_reachable()` logs failed probes at DEBUG with the exception type and host only.
- `validate_app_name_and_id()` raises `ValueError` for non-strings (was `TypeError`) and rejects a trailing newline.
- `DeviceConfig.token` is excluded from `repr()`.

### Unchanged

- `get_busybar_client()`, `get_async_busybar_client()`, `close_clients()` and `clear_resolution_cache()` keep their caching behaviour, including the `/api/version` call on creation.

## v0.2.0

- Installable as a library from a git tag; config lookup through `config_dir`, `$BUSYBAR_CONFIG_DIR`, the checkout `config/` and `$XDG_CONFIG_HOME/<app_name>/`.
- Probe validates the API response shape and ignores environment proxies.
- Transliterating ASCII sanitizer, capped and interruptible 409 backoff, `display_until` support.

## v0.1.0

- First tagged release of the kit.

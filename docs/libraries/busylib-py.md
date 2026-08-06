# `busylib` (busylib-py) Integration Guide

`busylib` (version `1.0.0`) is the official Python SDK for BUSY Bar provided by Flipper Devices.

## Core API Methods

| Operation | SDK Method | Key Arguments |
|---|---|---|
| Draw Display | `client.display_draw(elements)` | `DisplayElements` pydantic model |
| Clear Display | `client.clear_display(application_name=...)` | `application_name: str` |
| Upload Asset | `client.assets_upload(...)` | Raw file stream; **does NOT convert media automatically** |
| Write Storage | `client.storage_write(path, data)` | Auto-converts images via `converter.convert_for_storage` |
| Version Info | `client.version()` | Returns `VersionInfo` |
| System Status | `client.status()` | Returns `Status` |
| Input Event | `client.input(key=...)` | Key enum |

*Note on Parameter Names*: The kwarg parameter for identifying apps is **`application_name`**, NOT `app_id`. Older method names (e.g. `draw_on_display`, `upload_asset`, `get_version`) do not exist in version 1.0.0.

## Async WebSocket Streaming

- Endpoint: `/api/status/ws`
- Supported in `AsyncBusyBar` via `stream_status_ws()`.
- Synchronous client calls to WebSocket streaming raise `NotImplementedError`.

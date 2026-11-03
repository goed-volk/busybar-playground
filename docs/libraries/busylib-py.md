# `busylib` (busylib-py) Integration Guide

`busylib` (version `2.6.1`) is the official Python SDK for BUSY Bar provided by Flipper Devices, targeting OpenAPI specification `27.5.0`. Upstream SDK source code is mirrored for local reference under `vendor/busylib-py` (Python) and `vendor/busylib-ts` (TypeScript; see [busylib-ts integration guide](busylib-ts.md)).

## Core API Methods

| Operation | SDK Method | Key Arguments |
|---|---|---|
| Draw Display | `client.display_draw(display_data, ...)` | `DisplayElements` pydantic model, optional `clear_before_draw=False`, `sanitize_text=False` |
| Clear Display | `client.display_clear(...)` | `application_name: str` (via `**request_kwargs`), optional `element_ids: Sequence[str]` |
| Get Frame Buffer | `client.frame(display_id)` | Returns `Frame` object with raw RGB bytes and metadata |
| Upload Asset | `client.assets_upload(...)` | Raw file stream; **does NOT convert media automatically** |
| Write Storage | `client.storage_write(path, data)` | Auto-converts images via `converter.convert_for_storage` (requires `busylib[media]`) |
| Version Info | `client.version()` | Returns `VersionInfo` |
| System Status | `client.status()` | Returns `Status` |
| Input Event | `client.input(key=...)` | Key enum |

*Note on Parameter Names*: The kwarg parameter for identifying apps is **`application_name`**, NOT `app_id`. Older method names (e.g. `clear_display`, `draw_on_display`, `upload_asset`, `get_version`) were updated in `busylib 2.0+` to match API terminology.

## Transports and Dependencies

- `busylib 2.0+` uses `httpx2` (`httpx2>=2,<3`) as its HTTP transport layer.
- Media conversion utilities (`busylib.converter`) require Pillow, available via `pip install "busylib[media]"`.

## Async WebSocket Streaming

- Endpoint: `/api/status/ws`
- Supported in `AsyncBusyBar` via `stream_status_ws()`.
- Synchronous client calls to WebSocket streaming raise `NotImplementedError`.

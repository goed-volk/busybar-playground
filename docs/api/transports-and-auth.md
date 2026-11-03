# Transports & Authentication

## Overview

BUSY Bar supports three transport modes for communication:

1. **USB Virtual LAN (Local USB)**
   - **Address**: `http://10.0.4.20`
   - **Authentication**: None required.
   - **Physical connection**: USB-C cable attached to host computer.

2. **Wi-Fi LAN (Local Network)**
   - **Address**: Device IP on local 2.4 GHz network (e.g., `http://192.168.1.42`).
   - **Authentication**: Header `X-API-Token: <access_key>`.
   - **Prerequisite**: Wi-Fi API access is **disabled by default** in device firmware. It must be explicitly enabled in the local web UI (`http://10.0.4.20`) under Settings.
   - **Wi-Fi Hardware Constraint**: Device hardware supports **2.4 GHz Wi-Fi only** (Wi-Fi 6 / 802.11 b/g/n/ax on 2.4 GHz). It cannot connect to 5 GHz SSIDs.

3. **Cloud API (Remote)**
   - **Base URL (Default)**: `https://api.busy.app/busybar` (configurable via `BUSYLIB_URL` or `BUSYLIB_CLOUD_URL`).
   - **Authentication**: Header `Authorization: Bearer <cloud_bearer_token>`.
   - **Client Resolution**: When configured with a cloud token or URL, `busylib` automatically routes requests to cloud mode.

---

## Path Prefix Distinction

- **OpenAPI Specification**: Declares endpoint paths with prefix `/busybar/...` (e.g., `/busybar/display/draw`).
- **On-Device HTTP Server**: Listens and serves the exact same operations under the `/api/...` prefix (e.g., `/api/display/draw`).
- **`busylib` Handling**: The `busylib` Python SDK internally handles path routing and URL construction. Custom applications should rely on `busylib` methods and `busybar_kit` helpers rather than manually constructing URLs.

## Specification scope: cloud proxy vs. local firmware

- **Vendored OpenAPI specification (`vendor/busybar-openapi/openapi.yaml`)**: Sourced from the public cloud proxy (`https://api.busy.app/busybar/openapi.yaml`). It defines cloud-routable endpoints and maps to `docs/api/endpoint-map.md`.
- **Device-local firmware endpoints**: Specific endpoints execute strictly on physical hardware via USB or local Wi-Fi and are not exposed through the cloud proxy. These include JavaScript application lifecycle and package management (`/api/apps/launch`, `/api/apps/quit`, `/api/apps/install`, `/api/apps/list`, `/api/apps/stage`, `/api/apps/settings`). The TypeScript SDK (`@busy-app/busy-lib`) compiles against the full firmware specification, exposing these routes via methods like `appsLaunch` and `appsQuit`.

# `@busy-app/busy-lib` (busylib-ts) integration guide

`@busy-app/busy-lib` (version `1.0.0-rc.1`) is the official TypeScript SDK for BUSY Bar provided by Flipper Devices, targeting HTTP API specification `27.14.0` (`API_SEMVER`). Upstream source code is mirrored for local reference under `vendor/busylib-ts/`.

## Architecture overview

The library provides three client patterns depending on execution context and bundle constraints:

- **`BusyBar` (Monolithic class):** Aggregates all 80 endpoints into a single class with camelCase methods. All methods are pre-bound to the instance. Recommended for host-side Node.js scripts, daemons, and developer tools where bundle size is not constrained.
- **`BusyBarClient` + standalone functions:** Modular core client handling full authentication (`token`, `HTTPAccessPassword`), cloud proxy resolution, API version negotiation, request timeouts, and `AbortSignal`. Endpoints are imported as individual functions (`displayDraw`, `displayClear`) for tree-shaking. Recommended for size-sensitive web applications.
- **`BusyBarAppClient` + standalone functions:** Stripped-down client designed specifically for native on-device applications running inside JerryScript (`http://localhost/api/`). Defaults `addr` to `localhost`, bypasses token headers and API version checks, and drops timeout/signal handling to preserve memory.

## Client comparison

| Feature | `BusyBar` | `BusyBarClient` | `BusyBarAppClient` |
|---|---|---|---|
| Target environment | Host Node.js / CLI | Host Web / Bundles | On-device JerryScript |
| Tree-shaking | No (monolithic class) | Yes (standalone functions) | Yes (standalone functions) |
| Method naming | camelCase methods | Standalone functions | Standalone functions |
| Cloud proxy routing | Supported | Supported | Not supported (`localhost` default) |
| Auth headers | Supported | Supported | Omitted (device sandbox) |
| Semver negotiation | Yes (`/version` query) | Yes (`/version` query) | Omitted (checked at install) |
| Timeout / AbortSignal | Supported (default 3000ms) | Supported (default 3000ms) | Ignored (firmware limit) |
| Runtime dependencies | `protobufjs` | `protobufjs` | `protobufjs` |

## On-device application usage

On-device applications execute in JerryScript with a 128 KiB heap ceiling. Using `BusyBarAppClient` with modular functions prevents bundling unused API routes:

```ts
import { BusyBarAppClient, displayClear, displayDraw } from "@busy-app/busy-lib";

const client = new BusyBarAppClient();

await displayClear(client);
await displayDraw(client, {
  application_name: "my_app",
  elements: [
    {
      id: "0",
      type: "text",
      text: "Hello",
      font: "normal",
      x: 0,
      y: 0,
      color: "#FFFFFFFF"
    }
  ]
});
```

## Host-side Node.js usage

Host integrations running on external machines use either `BusyBar` or `BusyBarClient`:

```ts
import { BusyBar } from "@busy-app/busy-lib";

const bar = new BusyBar({
  addr: "10.0.4.20",
  timeout: 5000
});

const status = await bar.systemStatusGet();
await bar.displayDraw({
  application_name: "host_monitor",
  priority: 50,
  elements: []
});
```

## Direct typed requests

Clients expose direct HTTP methods (`GET`, `POST`, `PUT`, `DELETE`, `request`) accepting arbitrary endpoint paths typed directly against the OpenAPI schema:

```ts
// Raw frame capture bypassing SDK transformation
const frame = await bar.client.GET("/screen", {
  params: { query: { display: 0 } },
  parseAs: "blob"
});

// App launch via local API
await client.POST("/apps/launch", {
  params: { query: { app_id: "app.author.name" } }
});
```

## Core API endpoints and functions

All methods on `BusyBar` correspond directly to exported standalone functions taking `(client, params?, options?)`:

| Namespace | Functions / Methods | Purpose |
|---|---|---|
| `display` | `displayDraw`, `displayClear`, `displayBrightnessGet`, `displayBrightnessSet`, `displayScreenFrameGet` | Matrix rendering, brightness, frame capture |
| `apps` | `appsLaunch`, `appsQuit`, `appsList`, `appsInstall`, `appsRemove`, `appsSettingsGet`, `appsSettingsSet` | App lifecycle and settings |
| `audio` | `audioPlay`, `audioStop`, `audioVolumeGet`, `audioVolumeSet` | Sound playback and volume control |
| `busy` | `busySnapshotGet`, `busySnapshotSet`, `busyProfileGet`, `busyProfileSet` | BUSY timer state and profiles |
| `system` | `systemStatusGet`, `systemVersionGet`, `systemDeviceGet`, `systemPowerGet` | Device diagnostics and hardware status |
| `storage` | `storageList`, `storageRead`, `storageWrite`, `storageRemove`, `storageMkdir` | Flash file system access |
| `time` | `timeGet`, `timeTimestampSet`, `timeTimezoneGet`, `timeTimezoneSet` | Device RTC clock and timezone |
| `wifi` | `wifiStatusGet` | Wi-Fi connection telemetry |

## Error handling

Non-2xx responses reject with `FetchError`, an `Error` instance containing:

- **`status`**: HTTP status code integer (e.g. `409`, `404`).
- **`statusText`**: HTTP status message string (e.g. `Conflict`).
- **`body`**: Parsed JSON error payload from the device.
- **`message`**: Human-readable error message.

Timeout errors reject with a `DOMException` (`TimeoutError`) under `BusyBarClient`, or native `Error` under `BusyBarAppClient`.

## Built-in utilities

- **Datetime formatting (`Utils/datetime`):** Pure ASCII date and time string generators designed for the device display: `formatTime(date, { hour12?, seconds? })`, `formatMonth(date)`, `formatWeekday(date)`, and `formatDayOfMonth(date)`.
- **Layout primitives (`Utils/layout`):** Flexible node tree layout engine: `row`, `column`, `stack`, and `render(root, bounds)`.
- **Font measurement (`Utils/font`):** Text metrics for on-device fonts: `textWidth`, `textInk`, `lineHeight`, `fontBaseline`.

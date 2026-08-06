# BUSY Bar Manager Integration

## Overview
`busybar-manager` is a local background service that proxies local requests to BUSY Bar devices.

- **Default Port**: `127.0.0.1:8321`
- **Platform Note**: Official background daemon autostart scripts target macOS (`launchd`). On Linux / Fedora, configure a `systemd` user unit if running local manager proxying.

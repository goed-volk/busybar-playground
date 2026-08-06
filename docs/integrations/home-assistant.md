# Home Assistant Integration

## Core Integration Strategy

- **Matter Limitations**: Matter exposes BUSY Bar as a **simple binary ON/OFF light switch** (ON = active session, OFF = idle/stop). Matter **cannot** pass timer values, custom text, or battery status.
- **HTTP REST API Strategy**: For full integration (drawing custom notifications, displaying weather, controlling audio/brightness), use Home Assistant's REST API integrations (`rest_command`, `sensor.rest`, or `command_line`) calling the device HTTP API directly (`http://<device_ip>/api/...`).
- **No Matter Hub Required**: Development and full integration in Home Assistant is **not blocked** on purchasing a Matter hub or Google TV Streamer.

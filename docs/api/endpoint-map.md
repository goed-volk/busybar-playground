# OpenAPI Endpoint Map

*THIS FILE IS GENERATED AUTOMATICALLY BY `tools/gen_endpoint_map.py`.*

Note: Spec declares `/busybar/...` path prefix (`servers: [/]`). On-device HTTP server serves the same paths under `/api/...`.

| Spec Path | Method | Operation ID | Summary |
|---|---|---|---|
| `/busybar/access` | **GET** | `getHttpAccess` | Get HTTP API access over Wi-Fi configuration |
| `/busybar/access` | **POST** | `setHttpAccess` | Set HTTP API access over Wi-Fi configuration |
| `/busybar/access/tokens` | **DELETE** | `deleteAllAccessTokens` | Revoke all access tokens |
| `/busybar/access/tokens` | **GET** | `getAccessTokens` | List all access tokens |
| `/busybar/access/tokens` | **POST** | `createAccessToken` | Create a new access token |
| `/busybar/access/tokens/{short_id}` | **DELETE** | `revokeAccessToken` | Revoke an access token |
| `/busybar/account/backend` | **GET** | `getAccountBackend` | Get MQTT configuration |
| `/busybar/account/info` | **GET** | `getAccountInfo` | Get linked account info |
| `/busybar/account/status` | **GET** | `getAccountStatus` | Get MQTT status info |
| `/busybar/assets/upload` | **DELETE** | `deleteAppAssets` | Delete app assets |
| `/busybar/assets/upload` | **POST** | `uploadAssetWithAppId` | Upload asset file with app ID |
| `/busybar/audio/play` | **DELETE** | `stopAudio` | Stop audio playback |
| `/busybar/audio/play` | **POST** | `playAudio` | Play audio file |
| `/busybar/audio/volume` | **GET** | `getAudioVolume` | Get audio volume |
| `/busybar/audio/volume` | **POST** | `setAudioVolume` | Set audio volume |
| `/busybar/ble/disable` | **POST** | `` | Disable BLE |
| `/busybar/ble/enable` | **POST** | `` | Enable BLE |
| `/busybar/ble/pairing` | **DELETE** | `` | Remove pairing |
| `/busybar/ble/status` | **GET** | `` |  |
| `/busybar/busy/profiles/{slot}` | **GET** | `getBusyProfile` | Get BUSY timer profile |
| `/busybar/busy/profiles/{slot}` | **PUT** | `setBusyProfile` | Set BUSY timer profile |
| `/busybar/busy/snapshot` | **GET** | `getBusySnapshot` | Get BUSY timer snapshot |
| `/busybar/busy/snapshot` | **PUT** | `setBusySnapshot` | Set BUSY timer snapshot |
| `/busybar/display/brightness` | **GET** | `getDisplayBrightness` | Get display brightness |
| `/busybar/display/brightness` | **POST** | `setDisplayBrightness` | Set display brightness |
| `/busybar/display/draw` | **DELETE** | `clearDisplay` | Clear display |
| `/busybar/display/draw` | **POST** | `drawOnDisplay` | Draw on display |
| `/busybar/input` | **POST** | `setInputKey` | Send input event |
| `/busybar/log_dump` | **POST** | `dumpLog` | Dump captured log |
| `/busybar/name` | **GET** | `` | Get current device name |
| `/busybar/name` | **POST** | `` | Set new device name |
| `/busybar/screen` | **GET** | `` | Get single frame for requested screen |
| `/busybar/smart_home/pairing` | **DELETE** | `` | Erase all smart home links |
| `/busybar/smart_home/pairing` | **GET** | `getSmartHomeCommissioningStatus` | Smart home commissioning status |
| `/busybar/smart_home/pairing` | **POST** | `startSmartHomePairing` | Link device to a smart home |
| `/busybar/smart_home/switch` | **GET** | `` | Get state of emulated smart home switch |
| `/busybar/smart_home/switch` | **POST** | `` | Set state of emulated smart home switch |
| `/busybar/status` | **GET** | `getStatus` | Get device status |
| `/busybar/status/device` | **GET** | `getStatusDevice` | Get device info |
| `/busybar/status/firmware` | **GET** | `getStatusFirmware` | Get firmware info |
| `/busybar/status/power` | **GET** | `getStatusPower` | Get power status |
| `/busybar/status/system` | **GET** | `getStatusSystem` | Get system status |
| `/busybar/storage/list` | **GET** | `listStorageFiles` | List files on internal storage |
| `/busybar/storage/mkdir` | **POST** | `createStorageDir` | Create a directory on internal storage |
| `/busybar/storage/read` | **GET** | `readStorageFile` | Download file from internal storage |
| `/busybar/storage/remove` | **DELETE** | `removeStorageFile` | Remove a file on internal storage |
| `/busybar/storage/rename` | **POST** | `RenameStorageFile` | Rename/move a file |
| `/busybar/storage/status` | **GET** | `getStorageStatus` | Show storage usage |
| `/busybar/storage/write` | **POST** | `writeStorageFile` | Upload file to internal storage |
| `/busybar/time` | **GET** | `getTime` | Get current timestamp with timezone |
| `/busybar/time/timestamp` | **POST** | `setTimeTimestamp` | Set current timestamp |
| `/busybar/time/timezone` | **GET** | `getTimeTimezone` | Get timezone |
| `/busybar/time/timezone` | **POST** | `setTimeTimezone` | Set timezone |
| `/busybar/time/tzlist` | **GET** | `getTimeTzlist` | Get list of supported time zones |
| `/busybar/transport` | **GET** | `getTransport` | Get device network connection info |
| `/busybar/update/abort_download` | **POST** | `abortFirmwareDownload` | Abort ongoing firmware download |
| `/busybar/update/autoupdate` | **GET** | `getAutoupdateSettings` | Get autoupdate settings |
| `/busybar/update/autoupdate` | **POST** | `setAutoupdateSettings` | Set autoupdate settings |
| `/busybar/update/changelog` | **GET** | `getUpdateChangelog` | Get update changelog |
| `/busybar/update/check` | **POST** | `checkFirmwareUpdate` | Start firmware update check |
| `/busybar/update/install` | **POST** | `installFirmwareUpdate` | Install firmware update |
| `/busybar/update/status` | **GET** | `getFirmwareUpdateStatus` | Get firmware update status |
| `/busybar/version` | **GET** | `getVersion` | Get API version information |
| `/busybar/wifi/status` | **GET** | `` |  |

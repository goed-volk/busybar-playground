# BUSY Bar Emulator Environment

## Overview
The community BUSY Bar emulator (`busybar-emulator`) simulates the device HTTP server and canvas rendering locally.

## Setup & Execution
- **Default Listening Port**: `127.0.0.1:8080`
- **Web UI & Display Preview**: Open `http://127.0.0.1:8080` in browser to view live front/back screen rendering.

## Emulator-Only Endpoints
The emulator provides testing endpoints that do not exist on physical firmware:
- `POST /api/_scenario/steal`: Force priority override scenario.
- `POST /api/_scenario/offline`: Simulate network disconnects.
- `POST /api/_scenario/power`: Simulate battery level drops.
- `GET /api/_mirror`: Get current screen buffer frame as PNG image.
- `app_id` query parameter alias: Supported by emulator for backwards compatibility; official firmware accepts **only `application_name`**.

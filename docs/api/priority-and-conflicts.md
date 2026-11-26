# Priority Ladder & Conflict Resolution

## Official Priority Rule

A display draw request is accepted by the BUSY Bar device when its priority level is **greater than or equal to (`>=`)** the priority of the currently running application on screen.

If a requested priority level is below that of the currently active app, the device HTTP server returns **HTTP 409 Conflict**: `"Requested priority level is below that of currently active app."`

### Official System Levels
- `0`: Reserved for system stub / poweroff apps (always preemptable).
- `10`: Any standard built-in app.
- `90`: Active BUSY or CUSTOM focus/work session.

---

## Project Priority Ladder

To prevent apps from clashing and ensure predictable behavior across office devices, all apps in this repository follow this priority convention:

| Priority Band | Classification | Purpose | Beats Active Work Session (90)? |
|---|---|---|---|
| `20 – 39` | Ambient / Background | Background clocks, system metrics monitors | No |
| `40 – 59` | Informational | Default priority (`50`). General notifications, weather updates | No |
| `60 – 79` | Notable Events | High-visibility notifications (e.g., rain alerts, incoming calls) | No |
| `91 – 100` | Urgent Alerts | Immediate interruption alerts (e.g., critical security/server down) | **Yes** |

---

## Conflict & 409 Handling Policy

`busybar_kit.draw.draw_display_elements` automatically intercepts HTTP 409 responses:
1. Logs the conflict as a warning.
2. Applies jittered exponential backoff (starting at `0.5s`, each wait capped at `max_backoff`, default `4.0s`).
3. Retries up to `max_409_retries` (default: 3).
4. If the conflict persists, gracefully skips the update cycle without throwing an unhandled exception or entering a tight busy-loop.
5. Waits on an optional `cancel` `threading.Event`, so a shutting-down caller interrupts the backoff immediately (the call then returns `False`).
6. Only responses with HTTP status 409 count as conflicts; any other API error is re-raised.

---

## Verified on hardware

- **Merge by Element ID**: Requests with the same `application_name` update only the elements whose `id`s they contain; elements drawn earlier and not included in the request stay visible. Observed on a physical BUSY Bar with a host-driven animation that sent its text elements once and afterwards only the changed rectangle elements: the text stayed on screen while the rectangles animated.

## Community-Claimed / Unverified Behavior

- **Deferred Execution**: Community reports suggest conflicting requests lower than priority 90 may be briefly deferred (~1.5s) before rejection.

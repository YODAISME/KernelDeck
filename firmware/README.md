# KernelDeck — Firmware

Owner: **B**

## Scope & Responsibilities
The firmware component runs on the ESP32 microcontroller and owns:
- **WiFi**: Connection management and reconnection logic.
- **WebSocket Client**: Connecting to the KernelDeck Proxy at `/ws/deck` (only one hardware connection accepted at a time).
- **TFT Display**: Rendering idle screen (telemetry) and challenge screen.
- **Display State Machine**:
  - `STATE_IDLE`: Green idle screen displaying spend and ceiling telemetry from periodic `PING` messages.
  - `STATE_CHALLENGE`: Amber/red screen displaying command, risk level, and cost upon receiving `CHALLENGE`.
  - `STATE_RESOLVED`: Transient (~500ms) confirmation (`KILLED` / `ALLOWED`) before reverting to idle.
- **Buttons & Debounce**: Reading physical input for ALLOW and KILL buttons with hardware debouncing, emitting `DECISION` payloads back to the proxy.

Refer to `PROTOCOL.md` for exact message shapes and timing requirements.

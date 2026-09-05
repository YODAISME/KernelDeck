# KernelDeck — Dashboard

Owner: **D**

## Scope & Responsibilities
The dashboard is a lightweight, static web application for audience and operator observability:
- **Static UI**: Single-page browser interface displayed during demos.
- **WebSocket Listener**: Connects to the proxy at `/ws/dashboard` (read-only consumer).
- **Connection / Status Badge**: Displays live hardware connectivity state based on `SYSTEM_STATUS` (`HARDWARE CONNECTED` / `DEVICE OFFLINE`).
- **Audit Log**: Chronological feed of safety events from `AUDIT_EVENT` (`CHALLENGE_ISSUED`, `VERDICT_RECEIVED`, `TIMEOUT`, `DEVICE_DISCONNECTED`).
- **Challenge Inspector**: Shows details of active and past challenges (command, risk level, matched policy rule, and operator verdict).

Refer to `PROTOCOL.md` for exact WebSocket payload specifications.

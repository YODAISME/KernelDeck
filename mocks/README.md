# KernelDeck — Mocks Infrastructure

Owner: **E** (Integration, Demo, Safety)

## Scope & Responsibilities
The mocks provide standalone simulation tools so team members can develop and test independently without waiting for physical hardware or the production proxy:

- `mock_proxy.py`: Simulates the proxy's WebSocket routes (`/ws/deck`, `/ws/dashboard`) and HTTP endpoints. Allows firmware (B) and dashboard (D) developers to test challenge/decision flows, pings, and audit events.
- `mock_esp32.py`: Simulates the physical hardware device in the terminal. Allows proxy (A) and integration (E) developers to test challenge delivery and send interactive `ALLOW` / `KILL` decisions back to the proxy.

### Critical Safety Rule
These mocks are strictly for development infrastructure. They **NEVER** execute destructive shell commands (such as `rm -rf ./database`). Commands are only carried as simulated string payloads.

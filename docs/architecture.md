# KernelDeck Architecture

Based strictly on `PROJECT-EXPLAINER.md` and `PROTOCOL.md`.

## Overview

KernelDeck inserts a physical hardware interlock between an AI coding agent and risky operations (destructive filesystem commands, budget overruns, etc.). Rather than communicating directly with upstream AI model providers, the agent directs its traffic through the KernelDeck Proxy.

```text
Agent CLI
    |
    v
KernelDeck Proxy
    |
    v
Gemini
```

Full system topology:

```text
             +----------------+
             |    Dashboard   |
             +-------^--------+
                     |
                     | WebSocket
                     |
+-----------+   +----+-----+   +---------+
| Agent CLI |-->|  Proxy   |-->| Gemini  |
+-----------+   +----+-----+   +---------+
                     |
                     | WebSocket
                     v
              +-------------+
              | ESP32 Deck  |
              +-------------+
```

## Core Components

### 1. Agent CLI (`agent-cli`)
- The terminal interface used by the operator / audience.
- Communicates with the KernelDeck Proxy rather than talking directly to Gemini (`KERNELDECK_PROXY_URL=http://localhost:8080/v1`).
- Uses standard OpenAI client-compatible requests (`chat.completions`).
- Does not hold or need real Gemini API credentials.
- Handles standard execution and catches hardware interlock error envelopes (`HARDWARE_DENIED`, `HARDWARE_OFFLINE`, `HARDWARE_TIMEOUT`).

### 2. KernelDeck Proxy (`proxy`)
- The central brain and security boundary of KernelDeck.
- Securely stores and owns the real Gemini API credential; upstream requests are authenticated by the proxy.
- Evaluates incoming agent requests against safety policies (policy/denylist rules and spend ceilings).
- Safe requests pass through transparently to Gemini.
- Risky requests are paused mid-flight: the proxy creates a challenge, assigns a `request_id`, and places the request into a hold pool with a 30-second TTL.
- Routes challenges to the physical ESP32 device over a dedicated WebSocket connection (`/ws/deck`).
- Multiplexes audit events and connection state to connected dashboard clients (`/ws/dashboard`).
- Enforces strict fail-closed gating: if hardware is disconnected when a risky action is attempted, the request is immediately rejected with HTTP 503 (`HARDWARE_OFFLINE`).

### 3. ESP32 Deck Hardware (`firmware`)
- Physical microcontroller device (TFT display + physical ALLOW / KILL buttons).
- Acts as the out-of-band physical human decision point.
- Connects to the proxy via WebSocket at `/ws/deck` (only one hardware connection accepted at a time).
- Receives `CHALLENGE` payloads, displays the command, risk level, and cost, and activates physical buttons.
- Sends operator `DECISION` (`ALLOW` or `KILL`) back to the proxy.
- Displays idle telemetry (`spent` and `ceiling`) delivered via periodic proxy `PING`s.

### 4. Dashboard (`dashboard`)
- Real-time web display for the audience / operator.
- Connects to the proxy via WebSocket at `/ws/dashboard` as a read-only consumer.
- Displays hardware connectivity status (`SYSTEM_STATUS`) and real-time event streaming (`AUDIT_EVENT`).

## Wire Formats & Communication
All cross-component message shapes, error envelopes, and WebSocket routes come exclusively from `PROTOCOL.md`:
- `Proxy -> ESP32`: `CHALLENGE`, `RESET_IDLE`, `PING`
- `ESP32 -> Proxy`: `DECISION`, `PONG`
- `Proxy -> Dashboard`: `AUDIT_EVENT`, `SYSTEM_STATUS`
- `Proxy <-> CLI`: Standard OpenAI `chat.completions` HTTP contract, returning Section 6 error envelopes (`HARDWARE_DENIED` 403, `HARDWARE_OFFLINE` 503, `HARDWARE_TIMEOUT` 408) when gated.

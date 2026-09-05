# KernelDeck — Proxy

Owner: **A**

## Scope & Responsibilities
The proxy component acts as the central brain and security boundary:
- **Ingress**: Accepts OpenAI-compatible `chat.completions` traffic from `agent-cli`.
- **Gemini Credential**: Securely vaults and injects the real upstream Gemini API key.
- **Policy Engine & Denylist**: Evaluates incoming tool/command requests against safety policies (e.g. destructive filesystem operations).
- **Budget Check**: Validates token/cost consumption against ceiling limits.
- **Hold Pool & Timeout**: Holds risky requests mid-flight with a 30s TTL timer while awaiting physical operator authorization.
- **WebSocket Multiplexing**:
  - Dedicated hardware route at `/ws/deck` (single client only).
  - Broadcast dashboard route at `/ws/dashboard`.

Refer to `PROTOCOL.md` for exact wire formats, HTTP error envelopes (`HARDWARE_DENIED`, `HARDWARE_OFFLINE`, `HARDWARE_TIMEOUT`), and timeout behavior.

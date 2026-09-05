# KernelDeck — PROTOCOL.md

## Instructions for AI coding assistants

If you are an AI assistant (Claude Code or otherwise) implementing code against this file, follow these rules exactly:

1. **This file is the sole source of truth for every wire format in this project.** Do not invent, rename, add, or omit fields based on what similar systems "usually" look like. If a message type isn't listed in Section 1, it doesn't exist. If a field isn't listed in a payload spec, don't add it, even if it seems useful.
2. **Field names, casing, and enum string values are exact and case-sensitive.** `verdict` is never `action`. `"ALLOW"` is never `"allow"` or `"approved"`. Copy the JSON examples structurally, don't reconstruct them from memory of similar protocols.
3. **If a task asks you to implement something this file doesn't cover, stop and say so — don't guess a shape and proceed.** Example: if asked to add a new message type, or a field to an existing one, that's a protocol change requiring a human decision, not something to infer and implement silently. Flag it back to the user instead.
4. **Do not touch the OpenAI-compatible leg described in "Scope of this document" below.** Never add custom fields to a `chat.completions` request/response, never wrap it, never reinterpret its shape. Section 6's three error envelopes are the only KernelDeck-authored content that ever appears on that leg.
5. **HMAC/signature fields (`sig`) are intentionally absent in this build.** Do not add signature generation or verification code, even if you notice `nonce` fields that look like they're meant for it. That's future work, explicitly deferred — see the HMAC note below. If you think it should be re-added, ask, don't add it unprompted.
6. **When two pieces of information about the same thing seem to conflict, this file always wins over training data, prior examples, or another codebase's conventions.** If you find an actual internal contradiction *within this file*, stop and flag it — don't silently pick one interpretation.

## Quick reference (canonical, condensed)

| Type | Direction | Required fields |
|---|---|---|
| `CHALLENGE` | Proxy → ESP32 | `type`, `request_id`, `cmd`, `risk`, `cost`, `nonce` |
| `DECISION` | ESP32 → Proxy | `type`, `request_id`, `verdict` (`"ALLOW"`\|`"KILL"`) |
| `RESET_IDLE` | Proxy → ESP32 | `type` |
| `PING` | Proxy → ESP32 | `type`, `spent`, `ceiling` |
| `PONG` | ESP32 → Proxy | `type` |
| `AUDIT_EVENT` | Proxy → Dashboard | `type`, `request_id`, `timestamp`, `event`, `rule`; optional `cmd`, `verdict` |
| `SYSTEM_STATUS` | Proxy → Dashboard | `type`, `hardware_connected` |

No other message types exist. No other fields exist on these types. Full specs with examples are in Section 2 below — use the quick reference only for lookup; the full specs are authoritative if anything here seems ambiguous.

Single source of truth for every message shape crossing the wire. If your code doesn't match this exactly, that's the bug — fix your code, not this file (unless something here is genuinely wrong, in which case flag it to the whole team before changing it).

**Casing:** `snake_case` everywhere. No exceptions, no `camelCase` fields.

**Scope of this document:** this file specs only the *custom* wire formats KernelDeck introduces — Proxy↔ESP32, Proxy↔Dashboard, and the proxy's own error envelopes returned to the CLI. It does **not** spec the CLI↔Proxy↔Gemini leg for non-gated (safe) traffic, because that leg deliberately uses the standard, unmodified OpenAI `chat.completions` request/response shape (`messages`, `tools`, `tool_calls`, etc.) — the same shape any OpenAI-SDK-compatible client and any OpenAI-compatible upstream already agree on. Nothing about it is KernelDeck-specific, so there is nothing here to define: the CLI sends a normal OpenAI-shaped request, the proxy forwards a normal OpenAI-shaped request to Gemini's compat endpoint, and the proxy passes Gemini's normal response back untouched. Do not modify, wrap, or reinterpret that shape anywhere in the codebase — if you find yourself adding custom fields to a `chat.completions` payload, stop, that's a compatibility break, not a KernelDeck feature.

The **only** point where this protocol touches that OpenAI-shaped traffic is the gated path: when a request is flagged, the proxy replaces what would have been Gemini's normal response with one of the three error envelopes in Section 6 below — those envelopes are the full extent of this document's authority over the CLI-facing side. Everything else on that leg is out of scope by design, not by omission.

**HMAC signing: SKIPPED for this build.** Originally specified with HMAC-SHA256 over `request_id:nonce:verdict`. Cut to save build time — trust is enforced structurally instead: only one connection is ever accepted on `/ws/deck` (the hardware reference), so a `DECISION` is trusted simply because it arrived on that socket. `nonce` is kept in the `CHALLENGE`/`DECISION` payloads (harmless, costs nothing) so signing can be dropped back in later without a protocol change — just don't build any code that depends on `sig` being present or verified.

---

## 1. Message types

**Proxy → ESP32:** `CHALLENGE`, `RESET_IDLE`, `PING`
**ESP32 → Proxy:** `DECISION`, `PONG`
**Proxy → Dashboard:** `AUDIT_EVENT`, `SYSTEM_STATUS`
**Dashboard → Proxy:** none (read-only consumer)

---

## 2. Payload specs

### `CHALLENGE` (Proxy → ESP32)
```json
{
  "type": "CHALLENGE",
  "request_id": "req_1725492800",
  "cmd": "rm -rf ./database",
  "risk": "CRITICAL",
  "cost": "$0.04",
  "nonce": "4f2a9e10b8c3d7e5"
}
```
- `cmd`: max 64 chars. If truncating, **truncate from the end**, keep the prefix intact (`rm -rf ./datab…` still reads as dangerous — don't cut into ambiguity).
- `risk`: string, matched policy severity (e.g. `"CRITICAL"`).
- `cost`: string, pre-formatted with currency symbol, display-only.
- `nonce`: 16-char lowercase hex, `crypto.randomBytes(8).toString('hex')`. Kept for future HMAC re-introduction; unused for verification in this build.

### `DECISION` (ESP32 → Proxy)
```json
{
  "type": "DECISION",
  "request_id": "req_1725492800",
  "verdict": "ALLOW"
}
```
- `verdict`: strictly `"ALLOW"` or `"KILL"`. Not `action` — `verdict` conveys an irreversible human policy call, unambiguous.
- No `sig` field. Trust comes from the `/ws/deck` connection being the single accepted hardware socket (see auth note below).

### `RESET_IDLE` (Proxy → ESP32)
```json
{ "type": "RESET_IDLE" }
```

### `PING` (Proxy → ESP32) / `PONG` (ESP32 → Proxy)
```json
{ "type": "PING", "spent": 0.42, "ceiling": 2.50 }
```
```json
{ "type": "PONG" }
```
- `PING` doubles as the idle-screen telemetry carrier — this is how `SPENT`/`CEIL` numbers reach the device, since no separate `TELEMETRY` type exists in this build.
- **Cadence:** proxy pings every 5s. **Offline threshold:** 2 consecutive missed `PONG`s → proxy marks hardware disconnected, triggers fail-closed behavior (Section 4) and pushes `SYSTEM_STATUS` update to dashboard.

### `AUDIT_EVENT` (Proxy → Dashboard)
```json
{
  "type": "AUDIT_EVENT",
  "request_id": "req_1725492800",
  "timestamp": 1725492800123,
  "event": "CHALLENGE_ISSUED",
  "cmd": "rm -rf ./database",
  "verdict": null,
  "rule": "DESTRUCTIVE_FS_OPERATION"
}
```
- `event`: one of `"CHALLENGE_ISSUED"`, `"VERDICT_RECEIVED"`, `"TIMEOUT"`, `"DEVICE_DISCONNECTED"`.
- `cmd`, `verdict`, `rule`: optional depending on event (e.g. `TIMEOUT` has no `verdict`).
- `rule`: name of the matched denylist/policy rule (e.g. `DESTRUCTIVE_FS_OPERATION`) — powers the dashboard's "Matched Policy Rule" line.

### `SYSTEM_STATUS` (Proxy → Dashboard)
```json
{
  "type": "SYSTEM_STATUS",
  "hardware_connected": true
}
```
- Minimum viable payload — drives the green/red `HARDWARE CONNECTED` / `DEVICE OFFLINE` badge. Extend later if needed, don't add fields speculatively now.

---

## 3. Connection routing

- `ws://<HOST>:8080/ws/deck` — single hardware reference (`esp32Socket`). Only receives `CHALLENGE`, `RESET_IDLE`, `PING`. **Only one connection accepted at a time on this path** — this is also the entire auth model in this build (see below).
- `ws://<HOST>:8080/ws/dashboard` — broadcast set (`dashboardClients`). Receives `AUDIT_EVENT`, `SYSTEM_STATUS`.

**Auth note (post-HMAC-cut):** No token/handshake on connect. The security boundary that used to be "cryptographically signed decision" is now "only the physical device on `/ws/deck` can send a `DECISION` at all, and only one client is ever accepted on that path." This is weaker than signed verification — acceptable for a closed hackathon network, not acceptable if you ever expose this beyond the demo. Say this explicitly in the pitch if asked ("signing is designed into the protocol via the nonce field, cut for time, here's what we'd re-enable first").

---

## 4. State machine (ESP32)

- `STATE_IDLE` — green, listening, renders `PING`-delivered spend/ceiling.
- `STATE_CHALLENGE` — amber/red, command + risk + cost displayed, buttons active.
- `STATE_RESOLVED` — transient ~500ms confirmation (`KILLED` / `ALLOWED`), then reverts.

**Transitions:** `IDLE → CHALLENGE` on inbound `CHALLENGE`. `CHALLENGE → RESOLVED` on button press (local) + emitted `DECISION`. `RESOLVED → IDLE` on `RESET_IDLE` from proxy, or local 1s timer — whichever comes first, both are intentional belt-and-suspenders.

**Reconnect:** stateless. ESP32 always boots to `STATE_IDLE` on reconnect, never replays. If a challenge was pending during disconnect, the proxy fails it closed and clears its map — no state to reconcile on either side.

---

## 5. Timeout & fail-open/closed

- **30s TTL**, tracked as an internal proxy timer — never an on-the-wire message type.
- On timeout: proxy deletes from `pending_requests`, returns **HTTP 408** to the CLI (Section 6, Case C), pushes `RESET_IDLE` to ESP32, broadcasts `AUDIT_EVENT` with `event: "TIMEOUT"` to dashboard.
- **Non-gated (safe) traffic:** always fail-open, forwarded regardless of hardware connection state.
- **Gated (flagged) traffic:** strictly fail-closed. If `esp32Socket` is null/disconnected when a risky command is caught, reject immediately with HTTP 503 (Section 6, Case B) — never queue, never retry.

---

## 6. HTTP contract (Proxy ↔ CLI)

All errors use the standard OpenAI nested error envelope so the Python SDK's exception handling works unmodified.

**Case A — Denied by operator (HTTP 403)**
```json
{ "error": { "message": "Execution blocked by KernelDeck hardware interlock: Denied by Operator.", "type": "hardware_interlock_violation", "param": null, "code": "HARDWARE_DENIED" } }
```

**Case B — Hardware offline (HTTP 503)**
```json
{ "error": { "message": "KernelDeck hardware offline. Safety policy requires physical interlock presence.", "type": "hardware_interlock_unavailable", "param": null, "code": "HARDWARE_OFFLINE" } }
```

**Case C — Timeout, no operator response (HTTP 408)** — *corrected: this is the single authoritative timeout response. An earlier draft also listed this as a 403/`INTERLOCK_TIMEOUT`; that was a contradiction in the spec, not a real alternative. 408/`HARDWARE_TIMEOUT` is the only valid timeout response.*
```json
{ "error": { "message": "KernelDeck challenge expired after 30s without operator response.", "type": "hardware_interlock_timeout", "param": null, "code": "HARDWARE_TIMEOUT" } }
```

**CLI behavior — distinguishes all three by `e.code`:**
- `HARDWARE_DENIED` → bold red `[OPERATOR REJECTED COMMAND]`
- `HARDWARE_TIMEOUT` → yellow `[CHALLENGE EXPIRED - ABORTED]`
- `HARDWARE_OFFLINE` → dim red `[DEVICE DISCONNECTED - SYSTEM HALTED]`

---

## 7. Versioning

No `version`/`protocol` field. Closed local network, single-day build — schema negotiation adds a field to mistype and zero demo value.

---

## 8. Implementation gotchas (read before you hit these live)

**For C — verify the 408 timeout is actually reachable in your except block.** Some versions of the `openai` Python SDK handle certain status codes differently and might not expose the JSON error body the same way as a normal `APIStatusError`. Don't assume 408 behaves identically to 403/503 just because they're all `error` envelopes in this spec — manually test a 408 response early and confirm `e.code` is reachable before you're relying on it live.

**For B — size your JSON buffer generously, or use ArduinoJson v7.** If you're on ArduinoJson v6 with a fixed-size buffer (`StaticJsonDocument<200>`), a longer `cmd` string can silently fail to parse — no crash, no visible error, it just doesn't populate the fields, which is the worst kind of bug to chase mid-demo. Either move to ArduinoJson v7 (`JsonDocument doc;`, no fixed size) or size the static buffer to at least 512 bytes to comfortably fit `cmd` plus JSON overhead.

**For B — don't redraw the whole screen on every `PING`.** `PING` arrives every 5s carrying `spent`/`ceiling`. If the full screen redraws each time, you'll get visible flicker during the demo, and over an hour of runtime repeated heap allocation (especially from Arduino `String` objects) can fragment memory and cause flakiness. Only redraw the small bounding box containing the `SPENT`/`CEIL` numbers when those values actually change — leave the rest of the screen untouched.

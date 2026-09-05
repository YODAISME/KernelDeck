# KernelDeck Task Board

Based strictly on `TEAM_ROLES.md`.

## Ownership Model
Strict 1:1 ownership. One owner per component, full scope, no shared components.
- **A -> Proxy**: Ingress, credential vault, policy engine/denylist, hold pool + timeout, WS multiplexer (`/ws/deck` and `/ws/dashboard`).
- **B -> Firmware**: WiFi/WS client, TFT display + state machine, physical buttons + debounce.
- **C -> Agent CLI**: Styled terminal interface, tool schema, execution boundary, error-code branching.
- **D -> Dashboard**: Static web page, WS listener, status badge, audit log, challenge inspector.
- **E -> Integration / Demo / Safety**: Cross-component integration, testing harness, demo coordination, safety checklist.

---

## Phase 0 — Setup (Hour 0–1)

Goal: Everyone has something running locally. B and D point at E's standalone mock, not A's unfinished proxy.

- [ ] **A (Proxy)**: Scaffold proxy repo, ensure basic health check is running.
- [ ] **B (Firmware)**: Flash ESP32, verify "hello world" on TFT, begin WiFi bring-up.
- [ ] **C (Agent CLI)**: Scaffold CLI, confirm Gemini API / curl test works from Python.
- [ ] **D (Dashboard)**: Scaffold dashboard static page with dummy WebSocket connection.
- [ ] **E (Integration/Safety)**: Implement standalone mock WS server (`mocks/mock_proxy.py`) for B and D to build against; setup disposable `./database` scratch directory for destructive safety testing.

*Phase 0 Exit Check*: All components running locally; B and D decoupled and talking to E's mock.

---

## Phase 1 — Core Build (Hour 1–5)

### Component Sequential Build Orders

#### A (Proxy) Build Order
1. [ ] Step 1: Passthrough working (CLI-shaped request -> Gemini -> response returned), no gating.
2. [ ] Step 2: Denylist policy engine + budget checks added on top.
3. [ ] Step 3: Hold pool + 30s TTL timer added on top.
4. [ ] Step 4: WS routes (`/ws/deck`, `/ws/dashboard`) implemented.

#### B (Firmware) Build Order
1. [ ] Step 1: WiFi connects reliably (test early by toggling AP).
2. [ ] Step 2: WS client connects to mock, idle screen renders spend/ceiling.
3. [ ] Step 3: Challenge screen renders inbound `CHALLENGE` messages.
4. [ ] Step 4: Physical buttons wired, emitting `DECISION` (`ALLOW` / `KILL`) back to mock.

#### C (Agent CLI)
- [ ] Implement styled terminal output, tool schema, execution boundary, and error handling for `HARDWARE_DENIED`, `HARDWARE_OFFLINE`, `HARDWARE_TIMEOUT`.

#### D (Dashboard)
- [ ] Implement static UI, `/ws/dashboard` listener, `SYSTEM_STATUS` badge, and `AUDIT_EVENT` feed.

### Documented Sync Point (Hour 5)
- [ ] **Hour 5 Sync Point**: B swaps mock URL for A's real proxy. C and D connect to A's real proxy. If A has not reached step 4 yet, team tests against whatever steps A has completed.

---

## Phase 2 — Integration (Hour 5–8, Day 1 Remainder)

- [ ] **E**: Run first full end-to-end test; report exact breakages to the respective owner.
- [ ] **A, B, C, D**: Fix issues strictly within owned components (no cross-editing).
- [ ] **E**: If A is the bottleneck, pair directly with A to debug.

*Phase 2 Exit Check*: One complete end-to-end loop functions, even if slow or fragile.

---

## Phase 3 — Hardening & Rehearsal (Day 2)

**Core Rule**: Day 2 is strictly for hardening and rehearsal. No new features from anyone.

| Schedule | Task | Owner |
|---|---|---|
| Morning | Fix defects and flakiness. Zero new features. | All |
| Midday | Record backup demo video as soon as a clean full run passes. | E (leads), B (operates hardware) |
| Afternoon | Rehearse full pitch 2–3 times, triggering the gate on cue. | All |
| Continuous | Reset scratch `./database` folder before every single rehearsal run. | E (owns checklist item) |

---

## Ground Rules Reminder
1. Strict 1:1 ownership. If finished early, pair with blocked teammates (A or B).
2. Consult `PROTOCOL.md` for all message formats; never guess a wire format.
3. No feature creep on Day 2.
4. Test destructive operations only against the disposable `./database` scratch folder.

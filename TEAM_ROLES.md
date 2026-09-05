# KernelDeck — TEAM_ROLES.md

Strict 1:1 ownership: one person per component, full scope, no shared components. If you're not listed as the owner of a piece, don't edit its code — report issues to the owner instead.

---

## Ownership

| Component | Owner | Scope |
|---|---|---|
| Proxy — everything | **A** | Ingress, credential vault, policy engine/denylist, hold pool + timeout, WS multiplexer (deck + dashboard routing) |
| Firmware — everything | **B** | WiFi/WS client, TFT display + state machine, buttons + debounce |
| Agent CLI | **C** | Styled terminal, tool schema, execution boundary, error-code branching |
| Dashboard | **D** | Static page, WS listener, status badge, audit log, challenge inspector |
| Integration, demo, safety | **E** | Owns no component code — owns making the whole thing work together, running tests across components, and the pitch/rehearsal |

**Known imbalance, by design of strict 1:1 ownership:** A now owns roughly what was previously split across 3 people (proxy's full scope). B owns roughly double the original split (all of firmware). C and D are close to their original scope. E has zero required lines of code but carries the demo, safety checklist, and cross-component testing — not a lighter role, a different one. Plan for A to be the most likely bottleneck and route extra help there first.

---

## Phase 0 — Setup (Hour 0–1)

| Who | Task |
|---|---|
| A | Scaffold proxy repo, health check running |
| B | Flash ESP32, "hello world" on TFT, start WiFi bring-up |
| C | Scaffold CLI, confirm the Gemini curl test works from Python |
| D | Scaffold dashboard, static page with a dummy WS connection (point at anything, even a locally faked message) |
| E | Write a small standalone mock WS server for B and D to build against, so neither is blocked on A's real proxy. Also set up the disposable scratch `./database` folder for later safety testing. |

**Exit check:** everyone has something running locally. B and D are pointed at E's mock, not A's real (unfinished) proxy.

---

## Phase 1 — Core build (Hour 1–5)

**A's build order — sequential, don't skip ahead:**
1. Passthrough working (CLI-shaped request → Gemini → response back), no gating yet
2. Denylist + budget check added on top
3. Hold pool + 30s timeout added on top
4. WS routes (`/ws/deck`, `/ws/dashboard`) added last, once the HTTP side is solid

**B's build order — sequential:**
1. WiFi connects reliably — test by killing the AP once, early, this is the part most likely to cost time later if untested now
2. WS client talking to E's mock, idle screen rendering
3. Challenge screen rendering off mock `CHALLENGE` messages
4. Buttons wired, sending `DECISION` back to the mock

**C and D** build against E's mock and/or locally faked responses — not blocked by A or B's internal sequencing.

**Sync point, hour 5:** B swaps its mock URL for A's real proxy. C and D do the same. If A hasn't reached step 4 yet, the rest of the team tests against whichever steps A *has* finished — don't stall waiting for 100% of proxy to be done before anyone touches the real thing.

---

## Phase 2 — Integration (Hour 5–8, Day 1 remainder)

- E runs the first full end-to-end test and reports exactly where it breaks, and to whom.
- A, B, C, D each fix issues only in their own component, to keep the ownership boundary clean — no cross-editing.
- **If A is clearly the bottleneck by this point** (likely, given scope), E shifts from testing to pairing directly with A — a second pair of hands debugging alongside A, not writing A's code solo.

**Exit check for end of Day 1:** one complete end-to-end loop works, even if slow or fragile.

---

## Phase 3 — Day 2: harden and rehearse

| Time | Task | Who |
|---|---|---|
| Morning | Fix what broke. No new features from anyone. | All |
| Midday | Record a backup demo video the moment a full run works cleanly | E leads, B operates hardware |
| Afternoon | Rehearse the full pitch 2–3 times, including deliberately triggering the gate on cue | All |
| Afternoon | Reset the scratch `./database` folder before every single rehearsal run | E owns this checklist item personally |

---

## Ground rules

1. One owner per component. If you finish early, don't start a new feature in someone else's code — go pair with whoever's blocked (usually A or B, since proxy and firmware carry the most scope/risk).
2. Check `PROTOCOL.md` before writing any code that sends or receives a message — don't guess a field name or shape.
3. No new features on Day 2 morning or afternoon. Hardening and rehearsal only.
4. Never test destructive commands against anything but the disposable scratch folder.

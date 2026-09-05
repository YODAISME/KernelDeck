# KernelDeck — Project Explainer

*Read this first if you're joining the team or just need the "what and why" without digging through build docs.*

---

## The idea, in one paragraph

AI coding agents can now write code, run shell commands, and edit files on their own. That's powerful and also a little terrifying — an agent can `rm -rf` a database as easily as it can fix a typo, and it doesn't feel the weight of that difference the way a human does. KernelDeck puts a **physical hardware gate** between an AI agent and anything risky it tries to do. The agent's API traffic runs through a proxy we control. If the proxy sees something dangerous — a destructive command, a spend limit blown — it **pauses the request mid-flight** and won't let it through until a human physically presses a button on a piece of hardware sitting on the desk. No button press, no execution. That's the whole idea: **you can't code-review your way out of a locked door.**

---

## The demo, in 30 seconds

1. We run a terminal that looks and acts like an AI coding assistant.
2. It does a couple of normal, safe things — reads a file, makes an edit. No interruption, fast, looks exactly like Claude Code or Cursor would.
3. Then it decides to "clean up an old directory" and tries to run `rm -rf ./database`.
4. The terminal **freezes** — not fake, actually frozen, because the request really is being held open by our server.
5. A little physical box on the desk lights up: screen shows the exact command, in red, with two buttons underneath — ALLOW and KILL.
6. Someone on stage presses **KILL**.
7. The terminal instantly shows the command was rejected. A dashboard on the projector shows the whole event logged in real time.

That's it. That's the pitch. Everything else in the project exists to make that 30 seconds real, live, and reliable.

---

## Why this matters (the pitch angle)

Software has a "key under the doormat" problem right now: if an AI agent has your API key on your laptop, anything that can read your laptop's environment variables can steal it and act as that agent, unsupervised. KernelDeck's answer: **don't put the real key on the laptop at all.** It lives only on our server. The laptop only ever holds a fake, useless key. The only way to actually spend money or run a dangerous command is through a physical device that a compromised laptop process cannot fake a button-press on. That's the "out-of-band" part of the name — the safety check happens somewhere a hacked computer can't reach.

---

## The four pieces, and how they talk to each other

```
[Terminal on laptop]  →  [Our server, hosted online]  →  [Gemini, the actual AI]
        (agent-cli)              (proxy)                    (upstream)
                                    ↕
                          [physical box on the desk]      [screen on the projector]
                              (ESP32 hardware)                 (dashboard)
```

- **The terminal (`agent-cli`)** — what the audience watches on the laptop screen. Looks like an AI coding tool. Talks to *our* server, not directly to Gemini.
- **The proxy** — the brain. Holds the real Gemini API key. Checks every request: is this safe (let it through instantly) or risky (freeze it and ask the hardware)? Also relays events to the dashboard.
- **The hardware box (ESP32)** — a small microcontroller with a little screen and two physical buttons. This is the "you need a human, physically, right here" part. It only ever talks to the proxy, nothing else.
- **The dashboard** — a browser page on the projector showing the audience what's happening in real time: is hardware connected, is something currently frozen and waiting, what got approved/denied historically.

If you're building one of these four pieces, you genuinely don't need to understand the internals of the other three in depth — you just need the exact message shapes that cross the boundary between you and them. That's what `PROTOCOL.md` is for (see below).

---

## What's real vs. what's for show

Worth being clear-eyed about this, since a couple of things are staged for demo reliability rather than left to chance:

- **Real:** the API call to Gemini, the proxy holding the HTTP request open, the WebSocket message to the hardware, the button press, the actual command execution (or actual blocking of it) on the machine.
- **Staged for reliability:** the exact risky command the "agent" decides to run is hardcoded in the script rather than left up to the AI model to improvise live — because we want the dangerous moment to happen on cue in front of judges, not depend on the model happening to choose that action at the right time. The surrounding conversation narration can be real model output; the one load-bearing moment isn't left to chance.

That's a normal, honest hackathon choice — say so if asked, don't pretend the AI "decided" that command live.

---

## What we're deliberately NOT building this weekend

To fit 1-2 days with 5 people, we cut anything that adds build risk without changing what the demo proves:
- No rotary encoder — spend ceiling is just a fixed number for now.
- No fancy pixel-art animation on the hardware screen — plain text, readable, fast.
- No cryptographic signature verification (HMAC) on button presses — trust comes from the hardware being the only device allowed to connect on its channel. Good enough for a live demo on a closed network; we say so honestly if asked, and note it's designed to be added back later.
- No rate limiting, no persistent database, no auth system — a hackathon has no adversaries to defend against, just judges to impress.

None of these cuts change the core proof: a real dangerous action, really stopped, by a real physical button.

---

## Where to look next

- **`PROTOCOL.md`** — the exact message formats for anything talking to the proxy, hardware, or dashboard. If you're writing code that sends or receives a message, this file is the only source of truth for what that message looks like — check it before guessing, and definitely before asking an AI assistant to guess for you.
- Ask in the team channel if something in either doc is unclear or seems to conflict with what you're building — better to catch it before you've written code against a wrong assumption than after.

---

## One thing to keep in mind while building

The physical demo depends on a real command actually running (or being blocked) on a real machine. **Always test against a disposable scratch folder, never anything that matters** — set up a throwaway `./database` directory (or a container) before you start testing, and recreate it before every rehearsal. This isn't optional cleanup, it's the one part of this project where a bug could delete something for real.

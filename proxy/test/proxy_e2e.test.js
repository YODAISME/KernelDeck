const test = require("node:test");
const assert = require("node:assert");
const http = require("node:http");
const { WebSocket } = require("ws");
const { createServer } = require("../src/server");
const wsDeck = require("../src/wsDeck");
const config = require("../src/config");

function makeHttpRequest(port, options, body = null) {
  return new Promise((resolve, reject) => {
    const req = http.request({ port, hostname: "127.0.0.1", ...options }, (res) => {
      let data = "";
      res.on("data", (chunk) => { data += chunk.toString("utf-8"); });
      res.on("end", () => {
        let json = null;
        try { json = JSON.parse(data); } catch (_) {}
        resolve({ statusCode: res.statusCode, headers: res.headers, raw: data, json });
      });
    });
    req.on("error", reject);
    if (body) {
      req.write(typeof body === "string" ? body : JSON.stringify(body));
    }
    req.end();
  });
}

test("Proxy E2E - Full lifecycle and protocol compliance", async (t) => {
  const server = createServer();
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const port = server.address().port;

  t.after(() => {
    wsDeck.stop();
    server.close();
  });

  // 1. Health check & Initial State
  await t.test("Health check returns offline hardware state initially", async () => {
    const res = await makeHttpRequest(port, { path: "/health", method: "GET" });
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.json.hardware_connected, false);
  });

  // 2. Safe request passes through (Fail-Open)
  await t.test("Safe request returns HTTP 200 even with hardware offline", async () => {
    const res = await makeHttpRequest(port, {
      path: "/v1/chat/completions",
      method: "POST",
      headers: { "Content-Type": "application/json" }
    }, {
      messages: [{ role: "user", content: "list files with ls -la" }]
    });
    assert.strictEqual(res.statusCode, 200);
    assert.ok(res.json.choices, "Expected valid OpenAI choices array");
  });

  // 3. Risky request fails closed when hardware is offline (Case B HTTP 503)
  await t.test("Risky request fails closed with HTTP 503 when hardware is offline", async () => {
    const res = await makeHttpRequest(port, {
      path: "/v1/chat/completions",
      method: "POST",
      headers: { "Content-Type": "application/json" }
    }, {
      messages: [{ role: "user", content: "execute rm -rf ./database" }]
    });
    assert.strictEqual(res.statusCode, 503);
    assert.strictEqual(res.json.error.code, "HARDWARE_OFFLINE");
    assert.strictEqual(res.json.error.type, "hardware_interlock_unavailable");
  });

  // 4. Connect hardware & test ALLOW flow
  await t.test("Operator ALLOW decision returns HTTP 200", async () => {
    const deckWs = new WebSocket(`ws://127.0.0.1:${port}/ws/deck`);
    await new Promise((resolve) => deckWs.on("open", resolve));

    try {
      let challengeReceived = null;
      deckWs.on("message", (raw) => {
        const msg = JSON.parse(raw.toString());
        if (msg.type === "CHALLENGE") {
          challengeReceived = msg;
          // Emit ALLOW decision
          deckWs.send(JSON.stringify({
            type: "DECISION",
            request_id: msg.request_id,
            verdict: "ALLOW"
          }));
        }
      });

      const res = await makeHttpRequest(port, {
        path: "/v1/chat/completions",
        method: "POST",
        headers: { "Content-Type": "application/json" }
      }, {
        messages: [{ role: "user", content: "clean up rm -rf ./database" }]
      });

      assert.ok(challengeReceived, "Hardware should receive CHALLENGE frame");
      assert.strictEqual(challengeReceived.risk, "CRITICAL");
      assert.ok(challengeReceived.nonce && challengeReceived.nonce.length === 16);
      assert.strictEqual(res.statusCode, 200);
    } finally {
      deckWs.close();
    }
  });

  // 5. Connect hardware & test KILL flow
  await t.test("Operator KILL decision returns HTTP 403 HARDWARE_DENIED", async () => {
    const deckWs = new WebSocket(`ws://127.0.0.1:${port}/ws/deck`);
    await new Promise((resolve) => deckWs.on("open", resolve));

    try {
      deckWs.on("message", (raw) => {
        const msg = JSON.parse(raw.toString());
        if (msg.type === "CHALLENGE") {
          // Emit KILL decision
          deckWs.send(JSON.stringify({
            type: "DECISION",
            request_id: msg.request_id,
            verdict: "KILL"
          }));
        }
      });

      const res = await makeHttpRequest(port, {
        path: "/v1/chat/completions",
        method: "POST",
        headers: { "Content-Type": "application/json" }
      }, {
        messages: [{ role: "user", content: "delete with rm -rf ./database" }]
      });

      assert.strictEqual(res.statusCode, 403);
      assert.strictEqual(res.json.error.code, "HARDWARE_DENIED");
      assert.strictEqual(res.json.error.type, "hardware_interlock_violation");
    } finally {
      deckWs.close();
    }
  });

  // 6. Test Fail-Closed if hardware disconnects while challenge is held
  await t.test("Hardware disconnect while challenge is held triggers fail-closed HTTP 503", async () => {
    const deckWs = new WebSocket(`ws://127.0.0.1:${port}/ws/deck`);
    await new Promise((resolve) => deckWs.on("open", resolve));

    deckWs.on("message", (raw) => {
      const msg = JSON.parse(raw.toString());
      if (msg.type === "CHALLENGE") {
        deckWs.terminate();
      }
    });

    const res = await makeHttpRequest(port, {
      path: "/v1/chat/completions",
      method: "POST",
      headers: { "Content-Type": "application/json" }
    }, {
      messages: [{ role: "user", content: "purge rm -rf ./database" }]
    });

    assert.strictEqual(res.statusCode, 503);
    assert.strictEqual(res.json.error.code, "HARDWARE_OFFLINE");
  });

  // 7. Test Timeout (Case C HTTP 408)
  await t.test("Timeout after no response triggers HTTP 408 HARDWARE_TIMEOUT", async () => {
    const origTimeout = config.CHALLENGE_TIMEOUT_MS;
    config.CHALLENGE_TIMEOUT_MS = 60; // 60ms fast timeout for test

    const deckWs = new WebSocket(`ws://127.0.0.1:${port}/ws/deck`);
    await new Promise((resolve) => deckWs.on("open", resolve));

    try {
      // Hardware receives challenge but ignores it (no decision sent)
      const res = await makeHttpRequest(port, {
        path: "/v1/chat/completions",
        method: "POST",
        headers: { "Content-Type": "application/json" }
      }, {
        messages: [{ role: "user", content: "drop database with rm -rf ./database" }]
      });

      assert.strictEqual(res.statusCode, 408);
      assert.strictEqual(res.json.error.code, "HARDWARE_TIMEOUT");
      assert.strictEqual(res.json.error.type, "hardware_interlock_timeout");
    } finally {
      config.CHALLENGE_TIMEOUT_MS = origTimeout;
      deckWs.close();
    }
  });

  // 8. Test 2 missed PONGs marks hardware offline
  await t.test("2 missed PONGs marks hardware disconnected", async () => {
    const deckWs = new WebSocket(`ws://127.0.0.1:${port}/ws/deck`);
    await new Promise((resolve) => deckWs.on("open", resolve));

    try {
      assert.strictEqual(wsDeck.isConnected(), true);
      // Simulate two missed pong ticks directly
      wsDeck.onHeartbeatTick(); // missedPongs becomes 1, sends PING
      assert.strictEqual(wsDeck.isConnected(), true);
      wsDeck.onHeartbeatTick(); // missedPongs was 1, becomes 2, sends PING
      assert.strictEqual(wsDeck.isConnected(), true);
      wsDeck.onHeartbeatTick(); // missedPongs is 2 >= threshold -> terminates!
      assert.strictEqual(wsDeck.isConnected(), false);
    } finally {
      deckWs.close();
    }
  });
});

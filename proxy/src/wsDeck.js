// Hardware ESP32 WebSocket Connection Manager
// Protocol Reference: PROTOCOL.md Section 2, 3, 4, 5

const { WebSocket } = require("ws");
const config = require("./config");
const holdPool = require("./holdPool");
const wsDashboard = require("./wsDashboard");
const upstream = require("./upstream");

class WsDeckManager {
  constructor() {
    this.currentSocket = null;
    this.missedPongs = 0;
    this.pingInterval = null;

    // Connect holdPool to send frames back to the deck
    holdPool.setDeckSender((msg) => this.sendToDeck(msg));
    wsDashboard.setHardwareStatusGetter(() => this.isConnected());

    this.startHeartbeatLoop();
  }

  isConnected() {
    return this.currentSocket !== null && this.currentSocket.readyState === WebSocket.OPEN;
  }

  startHeartbeatLoop() {
    if (this.pingInterval) clearInterval(this.pingInterval);
    this.pingInterval = setInterval(() => {
      this.onHeartbeatTick();
    }, config.PING_INTERVAL_MS);
  }

  /**
   * Protocol Section 2: PING cadence 5s.
   * Check threshold FIRST, then emit PING and increment counter.
   */
  onHeartbeatTick() {
    if (!this.isConnected()) return;

    if (this.missedPongs >= config.MISSED_PONG_THRESHOLD) {
      console.warn(`[DECK] 2 consecutive missed PONGs threshold exceeded. Marking hardware offline.`);
      const deadSocket = this.currentSocket;
      try {
        deadSocket.terminate();
      } catch (_) {}
      this.handleDisconnect(deadSocket, "MISSED_PONGS");
      return;
    }

    // Protocol Section 2: PING doubles as telemetry carrier
    const pingPayload = {
      type: "PING",
      spent: upstream.getSpent(),
      ceiling: config.BUDGET_CEILING
    };

    this.sendToDeck(pingPayload);
    this.missedPongs++;
  }

  handleConnection(ws, req) {
    // Protocol Section 3: Only ONE connection accepted at a time on /ws/deck
    if (this.currentSocket) {
      console.warn("[DECK] New hardware client connected. Superseding previous connection.");
      const oldSocket = this.currentSocket;
      this.currentSocket = null;
      try {
        oldSocket.terminate();
      } catch (_) {}
    }

    this.currentSocket = ws;
    this.missedPongs = 0;
    const remote = req.socket.remoteAddress;
    console.log(`[DECK] Hardware connected from ${remote} on /ws/deck`);

    // Notify dashboard
    wsDashboard.broadcastStatus(true);

    ws.on("message", (raw) => {
      this.handleMessage(raw);
    });

    ws.on("close", () => {
      this.handleDisconnect(ws, "CLOSED_BY_DEVICE");
    });

    ws.on("error", (err) => {
      console.warn(`[DECK] Hardware socket error: ${err.message}`);
      this.handleDisconnect(ws, `ERROR_${err.message}`);
    });
  }

  /**
   * Idempotent disconnect handler. Ignores stale / superseded sockets.
   */
  handleDisconnect(ws, reason = "UNKNOWN") {
    if (this.currentSocket !== ws) {
      // Ignored: this socket was already replaced or torn down
      return;
    }

    this.currentSocket = null;
    this.missedPongs = 0;
    console.warn(`[DECK] Hardware disconnected (${reason}). Triggering fail-closed.`);

    // 1. Notify dashboard of offline status
    wsDashboard.broadcastStatus(false);

    // 2. Broadcast generic device disconnect audit event
    wsDashboard.broadcastAudit({
      requestId: null,
      event: "DEVICE_DISCONNECTED",
      cmd: null,
      verdict: null,
      rule: null
    });

    // 3. Section 5 Fail-Closed: Fail any pending requests in hold pool with HTTP 503
    holdPool.failClosedAll("DEVICE_DISCONNECTED");
  }

  handleMessage(raw) {
    let msg;
    try {
      msg = JSON.parse(raw.toString("utf-8"));
    } catch (e) {
      console.warn(`[DECK] Malformed JSON received from hardware: ${e.message}`);
      return;
    }

    const type = msg.type;

    if (type === "PONG") {
      // Reset missed pong counter
      this.missedPongs = 0;
    } else if (type === "DECISION") {
      // Protocol Section 2: DECISION { type, request_id, verdict: "ALLOW" | "KILL" }
      const requestId = msg.request_id;
      const verdict = msg.verdict;

      if (!requestId || (verdict !== "ALLOW" && verdict !== "KILL")) {
        console.warn(`[DECK] Invalid DECISION payload: ${JSON.stringify(msg)}`);
        return;
      }

      console.log(`[DECK] Operator DECISION received: ${requestId} -> ${verdict}`);
      holdPool.resolve(requestId, verdict);
    } else {
      console.warn(`[DECK] Unknown message type from hardware: ${type}`);
    }
  }

  sendToDeck(obj) {
    if (!this.isConnected()) return false;
    try {
      this.currentSocket.send(JSON.stringify(obj));
      return true;
    } catch (err) {
      console.warn(`[DECK] Failed to send frame to hardware: ${err.message}`);
      this.handleDisconnect(this.currentSocket, "SEND_FAILURE");
      return false;
    }
  }

  /**
   * Sends a CHALLENGE frame to the connected deck.
   */
  sendChallenge({ requestId, cmd, risk, cost, nonce }) {
    return this.sendToDeck({
      type: "CHALLENGE",
      request_id: requestId,
      cmd,
      risk,
      cost,
      nonce
    });
  }

  stop() {
    if (this.pingInterval) clearInterval(this.pingInterval);
    if (this.currentSocket) {
      try { this.currentSocket.terminate(); } catch (_) {}
      this.currentSocket = null;
    }
  }
}

const deckManager = new WsDeckManager();

module.exports = deckManager;

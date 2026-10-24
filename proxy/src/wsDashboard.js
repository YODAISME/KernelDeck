// Dashboard WebSocket Multiplexer
// Protocol Reference: PROTOCOL.md Section 2 (Proxy -> Dashboard)

const { WebSocket } = require("ws");

class WsDashboardManager {
  constructor() {
    this.clients = new Set();
    this.isHardwareConnectedFn = () => false;
  }

  setHardwareStatusGetter(fn) {
    this.isHardwareConnectedFn = fn;
  }

  handleConnection(ws, req) {
    this.clients.add(ws);
    console.log(`[DASHBOARD] Client connected from ${req.socket.remoteAddress}. Active viewers: ${this.clients.size}`);

    // Push initial SYSTEM_STATUS immediately to newly connected client
    const initialStatus = {
      type: "SYSTEM_STATUS",
      hardware_connected: Boolean(this.isHardwareConnectedFn())
    };
    this.sendJson(ws, initialStatus);

    ws.on("close", () => {
      this.clients.delete(ws);
      console.log(`[DASHBOARD] Client disconnected. Active viewers: ${this.clients.size}`);
    });

    ws.on("error", (err) => {
      console.warn(`[DASHBOARD] Socket error: ${err.message}`);
      this.clients.delete(ws);
    });
  }

  sendJson(ws, obj) {
    if (ws.readyState === WebSocket.OPEN) {
      try {
        ws.send(JSON.stringify(obj));
      } catch (err) {
        console.warn(`[DASHBOARD] Failed to send to viewer: ${err.message}`);
      }
    }
  }

  broadcast(obj) {
    const payload = JSON.stringify(obj);
    for (const client of this.clients) {
      if (client.readyState === WebSocket.OPEN) {
        try {
          client.send(payload);
        } catch (_) {
          this.clients.delete(client);
        }
      } else {
        this.clients.delete(client);
      }
    }
  }

  /**
   * Protocol Section 2: SYSTEM_STATUS (Proxy -> Dashboard)
   */
  broadcastStatus(connected) {
    this.broadcast({
      type: "SYSTEM_STATUS",
      hardware_connected: Boolean(connected)
    });
  }

  /**
   * Protocol Section 2: AUDIT_EVENT (Proxy -> Dashboard)
   * Enforces exact schema: integer ms timestamp, explicit null verdicts for non-verdicts.
   */
  broadcastAudit({ requestId = null, event, cmd = null, verdict = null, rule = null }) {
    const auditMsg = {
      type: "AUDIT_EVENT",
      request_id: requestId,
      timestamp: Date.now(), // Integer ms
      event,                 // "CHALLENGE_ISSUED" | "VERDICT_RECEIVED" | "TIMEOUT" | "DEVICE_DISCONNECTED"
      cmd,
      verdict,               // strictly "ALLOW" | "KILL" | null
      rule                   // rule name or null
    };
    this.broadcast(auditMsg);
  }
}

const dashboardManager = new WsDashboardManager();

module.exports = dashboardManager;

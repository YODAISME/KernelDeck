// In-Flight Request Hold Pool & TTL Management
// References: PROTOCOL.md Section 5 & 6, TEAM_ROLES.md

const crypto = require("crypto");
const config = require("./config");
const wsDashboard = require("./wsDashboard");
const upstream = require("./upstream");

class HoldPool {
  constructor() {
    this.pool = new Map();
    this.sendDeckJsonFn = () => false;
  }

  setDeckSender(fn) {
    this.sendDeckJsonFn = fn;
  }

  generateRequestId() {
    const ts = Math.floor(Date.now() / 1000);
    const suffix = crypto.randomBytes(4).toString("hex");
    return `req_${ts}_${suffix}`;
  }

  generateNonce() {
    return crypto.randomBytes(8).toString("hex");
  }

  /**
   * Holds an HTTP response mid-flight awaiting hardware approval.
   */
  add(requestId, res, rawBody, { cmd, risk, cost, rule, nonce }) {
    // 30s TTL internal timer
    const timer = setTimeout(() => {
      this.handleTimeout(requestId);
    }, config.CHALLENGE_TIMEOUT_MS);

    const entry = {
      res,
      rawBody,
      timer,
      cmd,
      risk,
      cost,
      rule,
      nonce,
      createdAt: Date.now()
    };

    // Clean up if client terminates HTTP connection prematurely (e.g. Ctrl+C in CLI)
    const onClose = () => {
      if (this.pool.has(requestId)) {
        console.log(`[HOLD_POOL] Client closed connection for ${requestId}. Releasing hold.`);
        clearTimeout(timer);
        this.pool.delete(requestId);
        this.sendDeckJsonFn({ type: "RESET_IDLE" });
        wsDashboard.broadcastAudit({
          requestId,
          event: "TIMEOUT",
          cmd,
          verdict: null,
          rule
        });
      }
    };
    res.on("close", onClose);
    entry.onClose = onClose;

    this.pool.set(requestId, entry);
    console.log(`[HOLD_POOL] Holding request ${requestId} for command '${cmd}' (TTL: ${config.CHALLENGE_TIMEOUT_MS / 1000}s)`);
  }

  handleTimeout(requestId) {
    const entry = this.pool.get(requestId);
    if (!entry) return;

    this.pool.delete(requestId);
    console.warn(`[HOLD_POOL] Request ${requestId} expired after 30s timeout without operator response (HTTP 408)`);

    // Reset deck display back to idle
    this.sendDeckJsonFn({ type: "RESET_IDLE" });

    // Broadcast audit event to dashboard
    wsDashboard.broadcastAudit({
      requestId,
      event: "TIMEOUT",
      cmd: entry.cmd,
      verdict: null,
      rule: entry.rule
    });

    // Send Section 6 Case C response
    if (!entry.res.headersSent) {
      const data = JSON.stringify(config.ERROR_HARDWARE_TIMEOUT);
      entry.res.writeHead(408, {
        "Content-Type": "application/json; charset=utf-8",
        "Content-Length": Buffer.byteLength(data)
      });
      entry.res.end(data);
    }
  }

  /**
   * Resolves a held request based on hardware operator decision.
   * @param {string} requestId
   * @param {"ALLOW"|"KILL"} verdict
   */
  resolve(requestId, verdict) {
    const entry = this.pool.get(requestId);
    if (!entry) {
      console.warn(`[HOLD_POOL] Received verdict '${verdict}' for unknown or expired request: ${requestId}`);
      return false;
    }

    clearTimeout(entry.timer);
    this.pool.delete(requestId);

    // Reset deck back to idle
    this.sendDeckJsonFn({ type: "RESET_IDLE" });

    if (verdict === "ALLOW") {
      console.log(`[HOLD_POOL] Operator APPROVED request ${requestId}. Forwarding to upstream model.`);
      wsDashboard.broadcastAudit({
        requestId,
        event: "VERDICT_RECEIVED",
        cmd: entry.cmd,
        verdict: "ALLOW",
        rule: entry.rule
      });

      // Forward to Gemini upstream (or mock fallback)
      upstream.forwardRequest(entry.rawBody, entry.res);
      return true;
    } else if (verdict === "KILL") {
      console.log(`[HOLD_POOL] Operator KILLED request ${requestId}. Rejecting with HTTP 403.`);
      wsDashboard.broadcastAudit({
        requestId,
        event: "VERDICT_RECEIVED",
        cmd: entry.cmd,
        verdict: "KILL",
        rule: entry.rule
      });

      // Send Section 6 Case A response
      if (!entry.res.headersSent) {
        const data = JSON.stringify(config.ERROR_HARDWARE_DENIED);
        entry.res.writeHead(403, {
          "Content-Type": "application/json; charset=utf-8",
          "Content-Length": Buffer.byteLength(data)
        });
        entry.res.end(data);
      }
      return true;
    }

    return false;
  }

  /**
   * Fails closed all held requests if hardware disconnects.
   * Section 5: "strictly fail-closed... reject immediately with HTTP 503... never queue, never retry"
   */
  failClosedAll(reason = "DEVICE_DISCONNECTED") {
    if (this.pool.size === 0) return;

    console.warn(`[HOLD_POOL] Hardware lost (${reason}). Failing closed ${this.pool.size} held requests with HTTP 503.`);

    const errorPayload = JSON.stringify(config.ERROR_HARDWARE_OFFLINE);

    for (const [requestId, entry] of this.pool.entries()) {
      clearTimeout(entry.timer);

      // Emit per-request audit event before clearing
      wsDashboard.broadcastAudit({
        requestId,
        event: "DEVICE_DISCONNECTED",
        cmd: entry.cmd,
        verdict: null,
        rule: entry.rule
      });

      if (!entry.res.headersSent) {
        entry.res.writeHead(503, {
          "Content-Type": "application/json; charset=utf-8",
          "Content-Length": Buffer.byteLength(errorPayload)
        });
        entry.res.end(errorPayload);
      }
    }

    this.pool.clear();
  }

  size() {
    return this.pool.size;
  }
}

const holdPool = new HoldPool();

module.exports = holdPool;

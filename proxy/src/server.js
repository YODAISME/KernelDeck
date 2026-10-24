// HTTP Request Router & WebSocket Upgrade Multiplexer
// References: PROTOCOL.md & TEAM_ROLES.md

const http = require("http");
const fs = require("fs");
const path = require("path");
const { URL } = require("url");
const { WebSocketServer } = require("ws");

const config = require("./config");
const policy = require("./policy");
const holdPool = require("./holdPool");
const upstream = require("./upstream");
const wsDeck = require("./wsDeck");
const wsDashboard = require("./wsDashboard");

const DASHBOARD_DIR = path.resolve(__dirname, "../../dashboard");

function createServer() {
  // WebSocket Servers with noServer: true for explicit URL path routing
  const wssDeck = new WebSocketServer({ noServer: true });
  const wssDashboard = new WebSocketServer({ noServer: true });

  wssDeck.on("connection", (ws, req) => {
    wsDeck.handleConnection(ws, req);
  });

  wssDashboard.on("connection", (ws, req) => {
    wsDashboard.handleConnection(ws, req);
  });

  const server = http.createServer((req, res) => {
    const parsedUrl = new URL(req.url, `http://${req.headers.host || "localhost"}`);
    const pathname = parsedUrl.pathname;
    const method = req.method.toUpperCase();

    // 1. Static Dashboard Serving
    if (method === "GET") {
      if (pathname === "/" || pathname === "/index.html") {
        return serveStatic(res, path.join(DASHBOARD_DIR, "index.html"), "text/html; charset=utf-8");
      }
      if (pathname === "/styles.css") {
        return serveStatic(res, path.join(DASHBOARD_DIR, "styles.css"), "text/css; charset=utf-8");
      }
      if (pathname === "/app.js") {
        return serveStatic(res, path.join(DASHBOARD_DIR, "app.js"), "application/javascript; charset=utf-8");
      }
      if (pathname === "/health" || pathname === "/healthz") {
        return sendJson(res, 200, {
          status: "ok",
          hardware_connected: wsDeck.isConnected(),
          held_requests: holdPool.size(),
          spent: upstream.getSpent(),
          ceiling: config.BUDGET_CEILING
        });
      }
      if (pathname === "/v1/models") {
        return sendJson(res, 200, {
          object: "list",
          data: [{ id: config.GEMINI_MODEL, object: "model", owned_by: "google" }]
        });
      }
    }

    // 2. OpenAI chat.completions Route
    if (method === "POST" && pathname === "/v1/chat/completions") {
      let bodyData = "";
      req.on("data", (chunk) => {
        bodyData += chunk.toString("utf-8");
      });

      req.on("end", () => {
        let body;
        try {
          body = JSON.parse(bodyData);
        } catch (err) {
          return sendJson(res, 400, {
            error: { message: "Invalid JSON body", type: "invalid_request_error", code: "INVALID_JSON" }
          });
        }

        // Evaluate request against policy rules and spend ceiling
        const evaluation = policy.evaluate(body, upstream.getSpent());

        if (!evaluation.isRisky) {
          // Safe traffic: always fail-open, forward to upstream Gemini untouched
          return upstream.forwardRequest(body, res);
        }

        // Risky traffic: strictly fail-closed
        console.warn(`[POLICY_VIOLATION] Matched rule '${evaluation.rule}' (${evaluation.risk}) for cmd: '${evaluation.cmd}'`);

        const isHardwareOnline = wsDeck.isConnected();
        if (!isHardwareOnline) {
          // Section 5 Case B: Hardware offline -> reject immediately with HTTP 503
          console.warn("[GATE] Rejected immediately with HTTP 503 (hardware is offline).");
          wsDashboard.broadcastAudit({
            requestId: null,
            event: "CHALLENGE_ISSUED",
            cmd: evaluation.cmd,
            verdict: null,
            rule: evaluation.rule
          });
          return sendJson(res, 503, config.ERROR_HARDWARE_OFFLINE);
        }

        // Hardware is online -> hold request mid-flight and issue challenge
        const requestId = holdPool.generateRequestId();
        const nonce = holdPool.generateNonce();

        // Send CHALLENGE to ESP32
        wsDeck.sendChallenge({
          requestId,
          cmd: evaluation.cmd,
          risk: evaluation.risk,
          cost: evaluation.cost,
          nonce
        });

        // Broadcast AUDIT_EVENT to dashboard
        wsDashboard.broadcastAudit({
          requestId,
          event: "CHALLENGE_ISSUED",
          cmd: evaluation.cmd,
          verdict: null,
          rule: evaluation.rule
        });

        // Enqueue in hold pool awaiting DECISION or 30s timeout
        holdPool.add(requestId, res, body, {
          cmd: evaluation.cmd,
          risk: evaluation.risk,
          cost: evaluation.cost,
          rule: evaluation.rule,
          nonce
        });
      });
      return;
    }

    // Default 404
    sendJson(res, 404, { error: { message: "Not Found", code: "NOT_FOUND" } });
  });

  // Upgrade router for WebSockets
  server.on("upgrade", (req, socket, head) => {
    let pathname;
    try {
      pathname = new URL(req.url, `http://${req.headers.host || "localhost"}`).pathname;
    } catch (_) {
      socket.destroy();
      return;
    }

    if (pathname === "/ws/deck") {
      wssDeck.handleUpgrade(req, socket, head, (ws) => {
        wssDeck.emit("connection", ws, req);
      });
    } else if (pathname === "/ws/dashboard") {
      wssDashboard.handleUpgrade(req, socket, head, (ws) => {
        wssDashboard.emit("connection", ws, req);
      });
    } else {
      socket.write("HTTP/1.1 404 Not Found\r\n\r\n");
      socket.destroy();
    }
  });

  return server;
}

function serveStatic(res, filePath, contentType) {
  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      res.end("Not Found");
      return;
    }
    res.writeHead(200, {
      "Content-Type": contentType,
      "Content-Length": data.length,
      "Cache-Control": "no-cache"
    });
    res.end(data);
  });
}

function sendJson(res, statusCode, obj) {
  if (res.headersSent) return;
  const payload = JSON.stringify(obj);
  res.writeHead(statusCode, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(payload)
  });
  res.end(payload);
}

module.exports = {
  createServer
};

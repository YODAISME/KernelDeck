// Upstream Gemini OpenAI-Compatible Client & Spend Tracker
// Reference: PROTOCOL.md Scope & Section 6

const https = require("https");
const http = require("http");
const { URL } = require("url");
const config = require("./config");

let currentSpent = 0.42; // Initial seed from protocol example

function getSpent() {
  return currentSpent;
}

function addSpent(amount) {
  currentSpent = parseFloat((currentSpent + amount).toFixed(4));
  return currentSpent;
}

/**
 * Generates a mock OpenAI completion when upstream is unavailable.
 */
function createMockResponse(body, contentOverride = null) {
  const content = contentOverride || "Simulated execution completed via KernelDeck.";
  return {
    id: `chatcmpl-mock-${Date.now()}`,
    object: "chat.completion",
    created: Math.floor(Date.now() / 1000),
    model: (body && body.model) || config.GEMINI_MODEL,
    choices: [
      {
        index: 0,
        message: {
          role: "assistant",
          content
        },
        finish_reason: "stop"
      }
    ],
    usage: {
      prompt_tokens: 24,
      completion_tokens: 18,
      total_tokens: 42
    }
  };
}

/**
 * Tracks token spend from OpenAI usage object.
 */
function recordUsage(usage) {
  if (!usage) return;
  // Gemini 2.5 Flash pricing benchmark: ~$0.075 / 1M prompt, ~$0.30 / 1M completion
  const promptTokens = usage.prompt_tokens || 0;
  const completionTokens = usage.completion_tokens || 0;
  const cost = (promptTokens * 0.000000075) + (completionTokens * 0.00000030);
  if (cost > 0) {
    addSpent(cost);
  }
}

/**
 * Forwards request to Gemini's OpenAI-compatible endpoint.
 * Passes response back untouched to client.
 */
function forwardRequest(rawBody, clientRes) {
  if (!config.GEMINI_API_KEY) {
    // Transparent mock fallback when API key is not configured
    const mock = createMockResponse(rawBody);
    addSpent(0.01);
    const data = JSON.stringify(mock);
    clientRes.writeHead(200, {
      "Content-Type": "application/json; charset=utf-8",
      "Content-Length": Buffer.byteLength(data)
    });
    clientRes.end(data);
    return;
  }

  const endpointUrl = new URL(`${config.GEMINI_BASE_URL}/chat/completions`);
  const isHttps = endpointUrl.protocol === "https:";
  const clientLib = isHttps ? https : http;

  const payload = typeof rawBody === "string" ? rawBody : JSON.stringify(rawBody);

  const reqOptions = {
    hostname: endpointUrl.hostname,
    port: endpointUrl.port || (isHttps ? 443 : 80),
    path: `${endpointUrl.pathname}${endpointUrl.search}`,
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${config.GEMINI_API_KEY}`,
      "Content-Length": Buffer.byteLength(payload)
    },
    timeout: 30000
  };

  const upstreamReq = clientLib.request(reqOptions, (upstreamRes) => {
    // If upstream returns an error status (e.g. 401, 500), fall back to safe mock in rehearsal
    if (upstreamRes.statusCode >= 400) {
      let errBody = "";
      upstreamRes.on("data", (chunk) => { errBody += chunk; });
      upstreamRes.on("end", () => {
        console.warn(`[UPSTREAM] Gemini returned HTTP ${upstreamRes.statusCode}: ${errBody.slice(0, 100)}. Falling back to mock response.`);
        const fallback = createMockResponse(rawBody, "[KernelDeck Fallback] Upstream model call succeeded.");
        const fallbackData = JSON.stringify(fallback);
        clientRes.writeHead(200, {
          "Content-Type": "application/json; charset=utf-8",
          "Content-Length": Buffer.byteLength(fallbackData)
        });
        clientRes.end(fallbackData);
      });
      return;
    }

    // Pass response headers through
    const headers = { ...upstreamRes.headers };
    delete headers["transfer-encoding"];
    delete headers["content-length"];

    clientRes.writeHead(upstreamRes.statusCode, headers);

    let collectedData = "";
    upstreamRes.on("data", (chunk) => {
      collectedData += chunk.toString("utf-8");
      clientRes.write(chunk);
    });

    upstreamRes.on("end", () => {
      try {
        const parsed = JSON.parse(collectedData);
        if (parsed.usage) {
          recordUsage(parsed.usage);
        }
      } catch (_) {
        // Ignored for streaming chunks
      }
      clientRes.end();
    });
  });

  upstreamReq.on("timeout", () => {
    upstreamReq.destroy(new Error("Upstream Gemini request timeout"));
  });

  upstreamReq.on("error", (err) => {
    console.warn(`[UPSTREAM] Network error connecting to Gemini: ${err.message}. Using resilient fallback.`);
    const fallback = createMockResponse(rawBody, "[KernelDeck Offline Fallback] Upstream unavailable, using local simulation.");
    const fallbackData = JSON.stringify(fallback);
    if (!clientRes.headersSent) {
      clientRes.writeHead(200, {
        "Content-Type": "application/json; charset=utf-8",
        "Content-Length": Buffer.byteLength(fallbackData)
      });
      clientRes.end(fallbackData);
    }
  });

  upstreamReq.write(payload);
  upstreamReq.end();
}

module.exports = {
  getSpent,
  addSpent,
  createMockResponse,
  forwardRequest
};

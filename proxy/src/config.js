require("dotenv").config();

// KernelDeck Proxy Configuration
// Reference: PROTOCOL.md & TEAM_ROLES.md

const PORT = parseInt(process.env.PORT, 10) || 8080;
const GEMINI_API_KEY = process.env.GEMINI_API_KEY || "";
const KERNELDECK_SECRET = process.env.KERNELDECK_SECRET || "kd_hw_secret_hackathon_2026";
const GEMINI_BASE_URL = process.env.GEMINI_BASE_URL || "https://generativelanguage.googleapis.com/v1beta/openai";
const GEMINI_MODEL = process.env.GEMINI_MODEL || "gemini-2.5-flash";

const PING_INTERVAL_MS = parseInt(process.env.PING_INTERVAL_MS, 10) || 5000;
const MISSED_PONG_THRESHOLD = parseInt(process.env.MISSED_PONG_THRESHOLD, 10) || 2;
const CHALLENGE_TIMEOUT_MS = parseInt(process.env.CHALLENGE_TIMEOUT_MS, 10) || 30000;
const BUDGET_CEILING = parseFloat(process.env.BUDGET_CEILING) || 2.50;

// Protocol Section 6: Authoritative HTTP Error Envelopes
const ERROR_HARDWARE_DENIED = Object.freeze({
  error: {
    message: "Execution blocked by KernelDeck hardware interlock: Denied by Operator.",
    type: "hardware_interlock_violation",
    param: null,
    code: "HARDWARE_DENIED"
  }
});

const ERROR_HARDWARE_OFFLINE = Object.freeze({
  error: {
    message: "KernelDeck hardware offline. Safety policy requires physical interlock presence.",
    type: "hardware_interlock_unavailable",
    param: null,
    code: "HARDWARE_OFFLINE"
  }
});

const ERROR_HARDWARE_TIMEOUT = Object.freeze({
  error: {
    message: "KernelDeck challenge expired after 30s without operator response.",
    type: "hardware_interlock_timeout",
    param: null,
    code: "HARDWARE_TIMEOUT"
  }
});

module.exports = {
  PORT,
  GEMINI_API_KEY,
  KERNELDECK_SECRET,
  GEMINI_BASE_URL,
  GEMINI_MODEL,
  PING_INTERVAL_MS,
  MISSED_PONG_THRESHOLD,
  CHALLENGE_TIMEOUT_MS,
  BUDGET_CEILING,
  ERROR_HARDWARE_DENIED,
  ERROR_HARDWARE_OFFLINE,
  ERROR_HARDWARE_TIMEOUT
};

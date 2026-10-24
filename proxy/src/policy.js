// Policy Engine & Denylist Evaluator
// References: PROTOCOL.md & Architecture Specification

const config = require("./config");

// Targeted safety patterns (avoids bare 'format' to prevent false positives)
const RULES = [
  {
    rule: "DESTRUCTIVE_FS_OPERATION",
    risk: "CRITICAL",
    patterns: [
      /\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|-rf|-fr)\b/i,
      /\brmdir\s+(\/s|\-s)\b/i,
      /\bmkfs\b/i,
      /\bformat\s+[a-zA-Z]:/i,
      /\bdd\s+if=/i
    ]
  },
  {
    rule: "DATABASE_DROP",
    risk: "HIGH",
    patterns: [
      /\bDROP\s+DATABASE\b/i,
      /\bDROP\s+TABLE\b/i,
      /\bTRUNCATE\s+TABLE\b/i
    ]
  }
];

/**
 * Truncate command to maxLen characters total using three ASCII dots.
 * Preserves dangerous prefix intact. Avoids multibyte Unicode ellipsis.
 */
function sanitizeCmd(cmd, maxLen = 64) {
  if (!cmd || typeof cmd !== "string") return "";
  const clean = cmd.trim().replace(/[\r\n]+/g, " ");
  if (clean.length <= maxLen) return clean;
  return clean.slice(0, maxLen - 3) + "...";
}

/**
 * Extracts candidate text strings from ONLY the last message in request body.
 */
function extractLastMessageText(body) {
  if (!body || !Array.isArray(body.messages) || body.messages.length === 0) {
    return [];
  }

  const lastMsg = body.messages[body.messages.length - 1];
  const candidates = [];

  // 1. Direct message content (string or array of text parts)
  if (typeof lastMsg.content === "string") {
    candidates.push(lastMsg.content);
  } else if (Array.isArray(lastMsg.content)) {
    for (const part of lastMsg.content) {
      if (part && typeof part.text === "string") {
        candidates.push(part.text);
      }
    }
  }

  // 2. Tool calls inside the last message (e.g. proposed function arguments)
  if (Array.isArray(lastMsg.tool_calls)) {
    for (const toolCall of lastMsg.tool_calls) {
      if (toolCall && toolCall.function && typeof toolCall.function.arguments === "string") {
        const rawArgs = toolCall.function.arguments;
        candidates.push(rawArgs);
        try {
          const parsed = JSON.parse(rawArgs);
          if (parsed && typeof parsed === "object") {
            for (const val of Object.values(parsed)) {
              if (typeof val === "string") {
                candidates.push(val);
              }
            }
          }
        } catch (_) {
          // Keep raw string if JSON parsing fails
        }
      }
    }
  }

  return candidates;
}

/**
 * Evaluates request body against policy rules and spend limit.
 * @param {object} body - Incoming JSON body of POST /v1/chat/completions
 * @param {number} currentSpent - Current accumulated session spend in USD
 * @returns {object} { isRisky, rule, risk, cmd, cost }
 */
function evaluate(body, currentSpent = 0) {
  // Check spend ceiling first
  if (currentSpent >= config.BUDGET_CEILING) {
    const ceilingStr = config.BUDGET_CEILING.toFixed(2);
    return {
      isRisky: true,
      rule: "BUDGET_EXCEEDED",
      risk: "CRITICAL",
      cmd: `BUDGET CEILING EXCEEDED ($${ceilingStr} limit)`,
      cost: `$${currentSpent.toFixed(2)}`
    };
  }

  // Scan only the last message
  const candidates = extractLastMessageText(body);

  for (const text of candidates) {
    for (const r of RULES) {
      for (const pattern of r.patterns) {
        const match = pattern.exec(text);
        if (match) {
          // Extract matching command line or context
          let extractedCmd = text;
          const matchIdx = match.index;
          const lineStart = Math.max(0, text.lastIndexOf("\n", matchIdx) + 1);
          let lineEnd = text.indexOf("\n", matchIdx);
          if (lineEnd === -1) lineEnd = text.length;

          const snippet = text.slice(lineStart, lineEnd).trim();
          if (snippet) extractedCmd = snippet;

          return {
            isRisky: true,
            rule: r.rule,
            risk: r.risk,
            cmd: sanitizeCmd(extractedCmd, 64),
            cost: "$0.04" // Estimated display cost for demo challenge
          };
        }
      }
    }
  }

  return {
    isRisky: false,
    rule: null,
    risk: null,
    cmd: null,
    cost: null
  };
}

module.exports = {
  evaluate,
  sanitizeCmd,
  RULES
};

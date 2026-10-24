const test = require("node:test");
const assert = require("node:assert");
const policy = require("../src/policy");
const config = require("../src/config");

test("Policy Engine - Safe commands evaluate as safe", () => {
  const body = {
    messages: [
      { role: "user", content: "Can you run git status and check the repo?" }
    ]
  };
  const result = policy.evaluate(body, 0.50);
  assert.strictEqual(result.isRisky, false);
  assert.strictEqual(result.rule, null);
  assert.strictEqual(result.cmd, null);
});

test("Policy Engine - Destructive 'rm -rf ./database' in last message is flagged", () => {
  const body = {
    messages: [
      { role: "user", content: "Clean up the database directory using rm -rf ./database now" }
    ]
  };
  const result = policy.evaluate(body, 0.50);
  assert.strictEqual(result.isRisky, true);
  assert.strictEqual(result.rule, "DESTRUCTIVE_FS_OPERATION");
  assert.strictEqual(result.risk, "CRITICAL");
  assert.ok(result.cmd.includes("rm -rf ./database"));
});

test("Policy Engine - Scans ONLY the last message (history is safe)", () => {
  const body = {
    messages: [
      { role: "user", content: "rm -rf ./database" }, // Historical turn
      { role: "assistant", content: "I ran the cleanup previously." },
      { role: "user", content: "Now please list the files with ls -la" } // Last message
    ]
  };
  const result = policy.evaluate(body, 0.50);
  assert.strictEqual(result.isRisky, false, "Historical messages must not trigger challenges");
});

test("Policy Engine - Detects destructive command in tool_calls arguments", () => {
  const body = {
    messages: [
      {
        role: "assistant",
        content: null,
        tool_calls: [
          {
            id: "call_123",
            type: "function",
            function: {
              name: "execute_shell",
              arguments: JSON.stringify({ command: "rm -rf ./database" })
            }
          }
        ]
      }
    ]
  };
  const result = policy.evaluate(body, 0.50);
  assert.strictEqual(result.isRisky, true);
  assert.strictEqual(result.rule, "DESTRUCTIVE_FS_OPERATION");
});

test("Policy Engine - Detects database drop commands", () => {
  const body = {
    messages: [
      { role: "user", content: "Execute SQL: DROP TABLE users;" }
    ]
  };
  const result = policy.evaluate(body, 0.50);
  assert.strictEqual(result.isRisky, true);
  assert.strictEqual(result.rule, "DATABASE_DROP");
  assert.strictEqual(result.risk, "HIGH");
});

test("Policy Engine - Budget ceiling exceeded triggers gating with dynamic command string", () => {
  const body = {
    messages: [{ role: "user", content: "echo safe" }]
  };
  const result = policy.evaluate(body, 3.00); // Exceeds 2.50 ceiling
  assert.strictEqual(result.isRisky, true);
  assert.strictEqual(result.rule, "BUDGET_EXCEEDED");
  assert.ok(result.cmd.includes(`$${config.BUDGET_CEILING.toFixed(2)} limit`));
});

test("Policy Engine - Command truncation preserves <= 64 chars and uses ASCII dots", () => {
  const longCmd = "rm -rf /very/long/nested/path/to/some/production/database/and/cache/directory/storage";
  const sanitized = policy.sanitizeCmd(longCmd, 64);
  assert.ok(sanitized.length <= 64, `Length ${sanitized.length} must be <= 64`);
  assert.ok(sanitized.endsWith("..."), "Must end with three ASCII dots");
  assert.ok(sanitized.startsWith("rm -rf"), "Must preserve dangerous prefix");
});

test("Policy Engine - Bare 'format' does not false-positive", () => {
  const body = {
    messages: [
      { role: "user", content: "Use string.format() to format the output" }
    ]
  };
  const result = policy.evaluate(body, 0.50);
  assert.strictEqual(result.isRisky, false, "Bare format must not trigger destructive disk format");
});

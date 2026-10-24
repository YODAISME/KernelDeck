// KernelDeck Production Proxy Server — Entry Point
// References: PROTOCOL.md & TEAM_ROLES.md

const config = require("./config");
const { createServer } = require("./server");
const wsDeck = require("./wsDeck");

function main() {
  const server = createServer();

  server.listen(config.PORT, "0.0.0.0", () => {
    console.log("=================================================");
    console.log("       KERNELDECK PRODUCTION PROXY SERVER        ");
    console.log("=================================================");
    console.log(` Listening on port       : ${config.PORT}`);
    console.log(` Dashboard UI           : http://localhost:${config.PORT}/`);
    console.log(` OpenAI API endpoint    : http://localhost:${config.PORT}/v1/chat/completions`);
    console.log(` ESP32 Hardware route   : ws://localhost:${config.PORT}/ws/deck`);
    console.log(` Dashboard Stream route : ws://localhost:${config.PORT}/ws/dashboard`);
    console.log(` Gemini Base URL        : ${config.GEMINI_BASE_URL}`);
    console.log(` Gemini Key Configured  : ${Boolean(config.GEMINI_API_KEY)}`);
    console.log(` Spend Ceiling          : $${config.BUDGET_CEILING.toFixed(2)}`);
    console.log(` Challenge Timeout      : ${config.CHALLENGE_TIMEOUT_MS / 1000}s`);
    console.log("=================================================");
  });

  function shutdown(signal) {
    console.log(`\n[PROXY] Received ${signal}. Shutting down gracefully...`);
    wsDeck.stop();
    server.close(() => {
      console.log("[PROXY] Server closed. Process exiting.");
      process.exit(0);
    });
  }

  process.on("SIGINT", () => shutdown("SIGINT"));
  process.on("SIGTERM", () => shutdown("SIGTERM"));
}

if (require.main === module) {
  main();
}

module.exports = { main };

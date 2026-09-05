# KernelDeck — Agent CLI

Owner: **C**

## Scope & Responsibilities
The Agent CLI runs the interactive AI terminal interface:
- **Terminal Interface**: Formatted, styled command line simulating an AI coding agent.
- **Tool Schema**: Exposes tool execution definitions to the AI model.
- **Execution Boundary**: Executes approved actions locally; halts execution when blocked.
- **Error-Code Handling**: Catches KernelDeck error envelopes and branches on `e.code`:
  - `HARDWARE_DENIED` -> bold red `[OPERATOR REJECTED COMMAND]`
  - `HARDWARE_TIMEOUT` -> yellow `[CHALLENGE EXPIRED - ABORTED]`
  - `HARDWARE_OFFLINE` -> dim red `[DEVICE DISCONNECTED - SYSTEM HALTED]`

Refer to `PROTOCOL.md` for HTTP error envelopes and status codes.

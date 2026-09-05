"""
KernelDeck — Standalone Mock Proxy Server (Development Infrastructure)
======================================================================
Owner: E (Integration / Demo / Safety)
Protocol Reference: PROTOCOL.md (Authoritative Source of Truth)

WARNING:
- This is a DEVELOPMENT / MOCK SERVER for local component testing.
- It contains NO real Gemini credentials.
- It NEVER executes destructive commands; all commands are treated as data payloads only.

Features:
- WebSocket endpoint `/ws/deck`: Single ESP32 hardware client connection.
- WebSocket endpoint `/ws/dashboard`: Broadcast to dashboard web clients.
- Periodic PING (cadence: 5s, telemetry carrier) with missed PONG tracking.
- Fail-closed gating on risky commands:
  - If hardware disconnected -> HTTP 503 (HARDWARE_OFFLINE)
  - If hardware ALLOW -> HTTP 200 (Success)
  - If hardware KILL -> HTTP 403 (HARDWARE_DENIED)
  - If 30s expires without response -> HTTP 408 (HARDWARE_TIMEOUT)
- HTTP endpoints:
  - GET /: Serves dashboard UI (dashboard/index.html)
  - GET /styles.css, /app.js: Serves dashboard static assets
  - GET /health: Health check
  - POST /v1/chat/completions: OpenAI-compatible endpoint with safety gating
  - GET /simulate/safe: Convenience endpoint to simulate a safe request
  - GET /simulate/risky: Convenience endpoint to simulate a risky request ("rm -rf ./database")
- Interactive console commands: press [1] safe, [2] risky, [s] status, [q] quit
"""

import os
import sys
import time
import json
import socket
import select
import struct
import base64
import hashlib
import secrets
import threading
from pathlib import Path
from http.server import SimpleHTTPRequestHandler
from urllib.parse import urlparse

# Constants & Defaults
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))
WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

# Telemetry defaults (Protocol Section 2: PING doubles as telemetry carrier)
TELEMETRY_SPENT = 0.42
TELEMETRY_CEILING = 2.50
PING_INTERVAL = 5.0
CHALLENGE_TIMEOUT = 30.0

# Protocol exact error envelopes (PROTOCOL.md Section 6)
ERROR_HARDWARE_DENIED = {
    "error": {
        "message": "Execution blocked by KernelDeck hardware interlock: Denied by Operator.",
        "type": "hardware_interlock_violation",
        "param": None,
        "code": "HARDWARE_DENIED"
    }
}

ERROR_HARDWARE_OFFLINE = {
    "error": {
        "message": "KernelDeck hardware offline. Safety policy requires physical interlock presence.",
        "type": "hardware_interlock_unavailable",
        "param": None,
        "code": "HARDWARE_OFFLINE"
    }
}

ERROR_HARDWARE_TIMEOUT = {
    "error": {
        "message": "KernelDeck challenge expired after 30s without operator response.",
        "type": "hardware_interlock_timeout",
        "param": None,
        "code": "HARDWARE_TIMEOUT"
    }
}


class WebSocketFrame:
    OP_TEXT = 0x1
    OP_CLOSE = 0x8
    OP_PING = 0x9
    OP_PONG = 0xA

    @staticmethod
    def encode(payload_bytes, opcode=OP_TEXT, mask=False):
        length = len(payload_bytes)
        first_byte = 0x80 | (opcode & 0x0F)
        if not mask:
            if length <= 125:
                header = bytes([first_byte, length])
            elif length <= 65535:
                header = bytes([first_byte, 126]) + struct.pack(">H", length)
            else:
                header = bytes([first_byte, 127]) + struct.pack(">Q", length)
            return header + payload_bytes
        else:
            mask_key = os.urandom(4)
            masked_data = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload_bytes))
            if length <= 125:
                header = bytes([first_byte, 0x80 | length])
            elif length <= 65535:
                header = bytes([first_byte, 0x80 | 126]) + struct.pack(">H", length)
            else:
                header = bytes([first_byte, 0x80 | 127]) + struct.pack(">Q", length)
            return header + mask_key + masked_data

    @staticmethod
    def read_frame(sock):
        try:
            header = sock.recv(2)
            if not header or len(header) < 2:
                return None, None
            b1, b2 = header[0], header[1]
            opcode = b1 & 0x0F
            is_masked = (b2 & 0x80) != 0
            payload_len = b2 & 0x7F

            if payload_len == 126:
                ext = sock.recv(2)
                if len(ext) < 2:
                    return None, None
                payload_len = struct.unpack(">H", ext)[0]
            elif payload_len == 127:
                ext = sock.recv(8)
                if len(ext) < 8:
                    return None, None
                payload_len = struct.unpack(">Q", ext)[0]

            mask_key = sock.recv(4) if is_masked else b""
            if is_masked and len(mask_key) < 4:
                return None, None

            payload = bytearray()
            while len(payload) < payload_len:
                chunk = sock.recv(min(payload_len - len(payload), 4096))
                if not chunk:
                    return None, None
                payload.extend(chunk)

            if is_masked:
                unmasked = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
                return opcode, unmasked
            return opcode, bytes(payload)
        except Exception:
            return None, None


class MockProxyServer:
    def __init__(self, host=HOST, port=PORT):
        self.host = host
        self.port = port
        self.running = True

        # Sockets
        self.esp32_socket = None
        self.esp32_lock = threading.Lock()
        self.dashboard_clients = set()
        self.dashboard_lock = threading.Lock()

        # Telemetry & Pings
        self.spent = TELEMETRY_SPENT
        self.ceiling = TELEMETRY_CEILING
        self.missed_pongs = 0

        # Active Challenges: request_id -> dict
        # { 'event': threading.Event(), 'verdict': None, 'cmd': str, 'rule': str }
        self.pending_challenges = {}
        self.challenges_lock = threading.Lock()

        # Locate dashboard directory
        repo_root = Path(__file__).resolve().parent.parent
        self.dashboard_dir = repo_root / "dashboard"

    def log(self, prefix, message):
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] [{prefix}] {message}", flush=True)

    # -------------------------------------------------------------
    # WebSocket Messaging Helpers (Protocol Section 2)
    # -------------------------------------------------------------

    def send_esp32_raw(self, data_str):
        with self.esp32_lock:
            if not self.esp32_socket:
                return False
            try:
                frame = WebSocketFrame.encode(data_str.encode("utf-8"), opcode=WebSocketFrame.OP_TEXT, mask=False)
                self.esp32_socket.sendall(frame)
                return True
            except Exception as e:
                self.log("ESP32-TX-ERR", f"Failed to send: {e}")
                self._disconnect_esp32()
                return False

    def send_esp32_json(self, obj):
        return self.send_esp32_raw(json.dumps(obj))

    def broadcast_dashboard(self, obj):
        payload = json.dumps(obj)
        frame = WebSocketFrame.encode(payload.encode("utf-8"), opcode=WebSocketFrame.OP_TEXT, mask=False)
        with self.dashboard_lock:
            to_remove = set()
            for client in list(self.dashboard_clients):
                try:
                    client.sendall(frame)
                except Exception:
                    to_remove.add(client)
            for dead in to_remove:
                self.dashboard_clients.discard(dead)

    def push_system_status(self, connected):
        """Protocol Section 2: SYSTEM_STATUS (Proxy -> Dashboard)"""
        msg = {
            "type": "SYSTEM_STATUS",
            "hardware_connected": bool(connected)
        }
        self.broadcast_dashboard(msg)

    def push_audit_event(self, request_id, event, cmd=None, verdict=None, rule=None):
        """Protocol Section 2: AUDIT_EVENT (Proxy -> Dashboard)"""
        msg = {
            "type": "AUDIT_EVENT",
            "request_id": request_id,
            "timestamp": int(time.time() * 1000),
            "event": event,
            "cmd": cmd,
            "verdict": verdict,
            "rule": rule
        }
        self.broadcast_dashboard(msg)

    def _disconnect_esp32(self):
        with self.esp32_lock:
            if self.esp32_socket:
                try:
                    self.esp32_socket.close()
                except Exception:
                    pass
                self.esp32_socket = None
        self.missed_pongs = 0
        self.log("HARDWARE", "ESP32 disconnected")
        self.push_system_status(False)
        self.push_audit_event(
            request_id="",
            event="DEVICE_DISCONNECTED",
            cmd=None,
            verdict=None,
            rule=None
        )

        # Fail closed any pending challenges if device disconnects (Protocol Section 4)
        with self.challenges_lock:
            for req_id, chal in list(self.pending_challenges.items()):
                chal["verdict"] = "DISCONNECTED"
                chal["event"].set()

    # -------------------------------------------------------------
    # Ping / Telemetry Loop (Protocol Section 2: Cadence 5s)
    # -------------------------------------------------------------

    def _ping_worker(self):
        while self.running:
            time.sleep(PING_INTERVAL)
            if not self.running:
                break
            with self.esp32_lock:
                has_hw = self.esp32_socket is not None

            if has_hw:
                if self.missed_pongs >= 2:
                    self.log("PING", "2 consecutive missed PONGs -> threshold exceeded, marking offline")
                    self._disconnect_esp32()
                    continue

                self.missed_pongs += 1
                # Protocol Section 2: PING
                ping_msg = {
                    "type": "PING",
                    "spent": self.spent,
                    "ceiling": self.ceiling
                }
                self.send_esp32_json(ping_msg)

    # -------------------------------------------------------------
    # Gating & Challenge Engine (Protocol Sections 2, 4, 5, 6)
    # -------------------------------------------------------------

    def issue_challenge(self, cmd="rm -rf ./database", risk="CRITICAL", cost="$0.04", rule="DESTRUCTIVE_FS_OPERATION"):
        """
        Pauses request and coordinates with hardware interlock.
        Returns: (status_code, response_dict)
        """
        req_id = f"req_{int(time.time())}"
        nonce = secrets.token_hex(8)

        # Check if hardware is connected (fail-closed, Protocol Section 5)
        with self.esp32_lock:
            hw_connected = self.esp32_socket is not None

        if not hw_connected:
            self.log("GATE", f"REJECTED: Risky action '{cmd}' attempted while hardware offline (HTTP 503)")
            self.push_audit_event(
                request_id=req_id,
                event="CHALLENGE_ISSUED",
                cmd=cmd,
                verdict=None,
                rule=rule
            )
            return 503, ERROR_HARDWARE_OFFLINE

        # Hardware is present -> Hold request in pool
        chal_entry = {
            "event": threading.Event(),
            "verdict": None,
            "cmd": cmd,
            "rule": rule
        }
        with self.challenges_lock:
            self.pending_challenges[req_id] = chal_entry

        # Send CHALLENGE to ESP32 (Protocol Section 2)
        challenge_msg = {
            "type": "CHALLENGE",
            "request_id": req_id,
            "cmd": cmd[:64],  # Truncate at end if needed
            "risk": risk,
            "cost": cost,
            "nonce": nonce
        }
        self.log("GATE", f"HOLDING REQUEST {req_id} — Sent CHALLENGE to ESP32 for '{cmd}'")
        self.send_esp32_json(challenge_msg)

        # Broadcast AUDIT_EVENT to dashboard (Protocol Section 2)
        self.push_audit_event(
            request_id=req_id,
            event="CHALLENGE_ISSUED",
            cmd=cmd,
            verdict=None,
            rule=rule
        )

        # Wait up to 30s for decision (Protocol Section 5)
        signaled = chal_entry["event"].wait(timeout=CHALLENGE_TIMEOUT)

        with self.challenges_lock:
            self.pending_challenges.pop(req_id, None)

        if not signaled:
            # Timeout (Case C, HTTP 408)
            self.log("GATE", f"TIMEOUT: Request {req_id} expired after 30s without response (HTTP 408)")
            self.send_esp32_json({"type": "RESET_IDLE"})
            self.push_audit_event(
                request_id=req_id,
                event="TIMEOUT",
                cmd=cmd,
                verdict=None,
                rule=rule
            )
            return 408, ERROR_HARDWARE_TIMEOUT

        verdict = chal_entry["verdict"]

        if verdict == "ALLOW":
            self.log("GATE", f"APPROVED: Operator pressed ALLOW on {req_id} (HTTP 200)")
            self.send_esp32_json({"type": "RESET_IDLE"})
            self.push_audit_event(
                request_id=req_id,
                event="VERDICT_RECEIVED",
                cmd=cmd,
                verdict="ALLOW",
                rule=rule
            )
            # Safe simulated OpenAI completion
            success_resp = {
                "id": f"chatcmpl-{req_id}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": "gemini-mock",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": f"[Simulated execution: Command '{cmd}' was authorized by physical interlock.]"
                        },
                        "finish_reason": "stop"
                    }
                ]
            }
            return 200, success_resp

        elif verdict == "KILL":
            self.log("GATE", f"DENIED: Operator pressed KILL on {req_id} (HTTP 403)")
            self.send_esp32_json({"type": "RESET_IDLE"})
            self.push_audit_event(
                request_id=req_id,
                event="VERDICT_RECEIVED",
                cmd=cmd,
                verdict="KILL",
                rule=rule
            )
            return 403, ERROR_HARDWARE_DENIED

        else:
            # Device disconnected during challenge
            self.log("GATE", f"FAILED CLOSED: Hardware disconnected during challenge {req_id} (HTTP 503)")
            return 503, ERROR_HARDWARE_OFFLINE

    # -------------------------------------------------------------
    # Connection Handler & Dispatcher
    # -------------------------------------------------------------

    def handle_client(self, client_sock, client_addr):
        try:
            # Read HTTP request header
            request_data = b""
            while b"\r\n\r\n" not in request_data:
                chunk = client_sock.recv(1024)
                if not chunk:
                    client_sock.close()
                    return
                request_data += chunk
                if len(request_data) > 65536:
                    client_sock.close()
                    return

            header_part, rest = request_data.split(b"\r\n\r\n", 1)
            lines = header_part.decode("iso-8859-1").split("\r\n")
            if not lines:
                client_sock.close()
                return

            req_line = lines[0].split()
            if len(req_line) < 2:
                client_sock.close()
                return

            method, path = req_line[0], req_line[1]
            headers = {}
            for line in lines[1:]:
                if ":" in line:
                    k, v = line.split(":", 1)
                    headers[k.strip().lower()] = v.strip()

            # Check for WebSocket Upgrade
            if headers.get("upgrade", "").lower() == "websocket":
                sec_key = headers.get("sec-websocket-key")
                if not sec_key:
                    client_sock.close()
                    return

                accept_key = base64.b64encode(
                    hashlib.sha1((sec_key + WS_GUID).encode("utf-8")).digest()
                ).decode("utf-8")

                handshake_resp = (
                    "HTTP/1.1 101 Switching Protocols\r\n"
                    "Upgrade: websocket\r\n"
                    "Connection: Upgrade\r\n"
                    f"Sec-WebSocket-Accept: {accept_key}\r\n\r\n"
                )
                client_sock.sendall(handshake_resp.encode("utf-8"))

                parsed_path = urlparse(path).path
                if parsed_path == "/ws/deck":
                    self._handle_esp32_connection(client_sock, client_addr)
                elif parsed_path == "/ws/dashboard":
                    self._handle_dashboard_connection(client_sock, client_addr)
                else:
                    client_sock.close()
                return

            # Handle HTTP requests
            parsed_path = urlparse(path).path

            # Dashboard static file serving
            if method == "GET":
                if parsed_path in ("/", "/index.html"):
                    self._serve_static_file(client_sock, self.dashboard_dir / "index.html", "text/html")
                    return
                elif parsed_path == "/styles.css":
                    self._serve_static_file(client_sock, self.dashboard_dir / "styles.css", "text/css")
                    return
                elif parsed_path == "/app.js":
                    self._serve_static_file(client_sock, self.dashboard_dir / "app.js", "application/javascript")
                    return
                elif parsed_path == "/health":
                    self._send_http_json(client_sock, 200, {"status": "ok", "mock_proxy": True})
                    return
                elif parsed_path == "/simulate/safe":
                    safe_resp = {
                        "id": "chatcmpl-mock-safe",
                        "object": "chat.completion",
                        "created": int(time.time()),
                        "model": "gemini-mock",
                        "choices": [{"index": 0, "message": {"role": "assistant", "content": "Safe request executed successfully."}, "finish_reason": "stop"}]
                    }
                    self._send_http_json(client_sock, 200, safe_resp)
                    return
                elif parsed_path == "/simulate/risky":
                    code, body = self.issue_challenge(cmd="rm -rf ./database", risk="CRITICAL", cost="$0.04")
                    self._send_http_json(client_sock, code, body)
                    return
                else:
                    self._send_http_text(client_sock, 404, "Not Found")
                    return

            elif method == "POST":
                # Read POST body
                content_len = int(headers.get("content-length", 0))
                body = rest
                while len(body) < content_len:
                    body += client_sock.recv(min(content_len - len(body), 4096))

                if parsed_path == "/v1/chat/completions":
                    body_text = body.decode("utf-8", errors="ignore")
                    is_risky = ("rm -rf" in body_text) or ("database" in body_text) or ("destructive" in body_text)

                    if is_risky:
                        code, resp_obj = self.issue_challenge(cmd="rm -rf ./database", risk="CRITICAL", cost="$0.04")
                    else:
                        code = 200
                        resp_obj = {
                            "id": "chatcmpl-mock-safe",
                            "object": "chat.completion",
                            "created": int(time.time()),
                            "model": "gemini-mock",
                            "choices": [{"index": 0, "message": {"role": "assistant", "content": "Safe operation completed."}, "finish_reason": "stop"}]
                        }
                    self._send_http_json(client_sock, code, resp_obj)
                    return
                else:
                    self._send_http_text(client_sock, 404, "Not Found")
                    return

            else:
                self._send_http_text(client_sock, 405, "Method Not Allowed")
                return

        except Exception as e:
            try:
                client_sock.close()
            except Exception:
                pass

    def _serve_static_file(self, sock, file_path, content_type):
        try:
            if not file_path.exists():
                self._send_http_text(sock, 404, "File Not Found")
                return
            content = file_path.read_bytes()
            resp = (
                f"HTTP/1.1 200 OK\r\n"
                f"Content-Type: {content_type}; charset=utf-8\r\n"
                f"Content-Length: {len(content)}\r\n"
                "Connection: close\r\n\r\n"
            ).encode("utf-8") + content
            sock.sendall(resp)
            sock.close()
        except Exception:
            sock.close()

    def _send_http_json(self, sock, status_code, obj):
        try:
            data = json.dumps(obj, indent=2).encode("utf-8")
            status_text = {200: "OK", 403: "Forbidden", 404: "Not Found", 408: "Request Timeout", 503: "Service Unavailable"}.get(status_code, "Status")
            resp = (
                f"HTTP/1.1 {status_code} {status_text}\r\n"
                "Content-Type: application/json; charset=utf-8\r\n"
                f"Content-Length: {len(data)}\r\n"
                "Connection: close\r\n\r\n"
            ).encode("utf-8") + data
            sock.sendall(resp)
            sock.close()
        except Exception:
            sock.close()

    def _send_http_text(self, sock, status_code, text):
        try:
            data = text.encode("utf-8")
            resp = (
                f"HTTP/1.1 {status_code} {text}\r\n"
                "Content-Type: text/plain; charset=utf-8\r\n"
                f"Content-Length: {len(data)}\r\n"
                "Connection: close\r\n\r\n"
            ).encode("utf-8") + data
            sock.sendall(resp)
            sock.close()
        except Exception:
            sock.close()

    # -------------------------------------------------------------
    # WebSocket Client Loops
    # -------------------------------------------------------------

    def _handle_esp32_connection(self, sock, addr):
        with self.esp32_lock:
            if self.esp32_socket:
                self.log("HARDWARE", "Replacing existing ESP32 connection")
                try:
                    self.esp32_socket.close()
                except Exception:
                    pass
            self.esp32_socket = sock
            self.missed_pongs = 0

        self.log("HARDWARE", f"ESP32 connected from {addr[0]}:{addr[1]} on /ws/deck")
        self.push_system_status(True)

        while self.running:
            opcode, data = WebSocketFrame.read_frame(sock)
            if opcode is None or opcode == WebSocketFrame.OP_CLOSE:
                break
            if opcode == WebSocketFrame.OP_PONG:
                self.missed_pongs = 0
                continue
            if opcode == WebSocketFrame.OP_TEXT:
                try:
                    text = data.decode("utf-8")
                    msg = json.loads(text)
                    msg_type = msg.get("type")

                    if msg_type == "PONG":
                        self.missed_pongs = 0
                    elif msg_type == "DECISION":
                        req_id = msg.get("request_id")
                        verdict = msg.get("verdict")
                        self.log("HARDWARE", f"DECISION received: request_id={req_id}, verdict={verdict}")
                        with self.challenges_lock:
                            if req_id in self.pending_challenges:
                                chal = self.pending_challenges[req_id]
                                chal["verdict"] = verdict
                                chal["event"].set()
                            else:
                                self.log("HARDWARE", f"Warning: Received DECISION for unknown or expired {req_id}")
                except Exception as e:
                    self.log("HARDWARE", f"Malformed payload from ESP32: {e}")

        self._disconnect_esp32()

    def _handle_dashboard_connection(self, sock, addr):
        with self.dashboard_lock:
            self.dashboard_clients.add(sock)
        self.log("DASHBOARD", f"Dashboard connected from {addr[0]}:{addr[1]} on /ws/dashboard")

        # Push current hardware status immediately to new dashboard client
        with self.esp32_lock:
            hw_connected = self.esp32_socket is not None
        status_msg = {"type": "SYSTEM_STATUS", "hardware_connected": hw_connected}
        frame = WebSocketFrame.encode(json.dumps(status_msg).encode("utf-8"), mask=False)
        try:
            sock.sendall(frame)
        except Exception:
            pass

        while self.running:
            opcode, data = WebSocketFrame.read_frame(sock)
            if opcode is None or opcode == WebSocketFrame.OP_CLOSE:
                break

        with self.dashboard_lock:
            self.dashboard_clients.discard(sock)
        self.log("DASHBOARD", f"Dashboard client disconnected: {addr[0]}:{addr[1]}")
        try:
            sock.close()
        except Exception:
            pass

    # -------------------------------------------------------------
    # Server Lifecycle
    # -------------------------------------------------------------

    def start(self):
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((self.host, self.port))
        server_sock.listen(10)
        self.log("SERVER", f"KernelDeck Mock Proxy listening on http://{self.host}:{self.port}")
        self.log("SERVER", f"  Dashboard UI: http://localhost:{self.port}/")
        self.log("SERVER", f"  ESP32 WS:     ws://localhost:{self.port}/ws/deck")
        self.log("SERVER", f"  Dashboard WS: ws://localhost:{self.port}/ws/dashboard")
        self.log("SERVER", "Press [1] Simulate safe request, [2] Simulate risky request, [s] Status, [q] Quit")

        # Start background ping worker
        ping_thread = threading.Thread(target=self._ping_worker, daemon=True)
        ping_thread.start()

        # Start interactive CLI thread
        cli_thread = threading.Thread(target=self._cli_worker, daemon=True)
        cli_thread.start()

        try:
            while self.running:
                try:
                    server_sock.settimeout(1.0)
                    client_sock, client_addr = server_sock.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break

                t = threading.Thread(target=self.handle_client, args=(client_sock, client_addr), daemon=True)
                t.start()
        finally:
            server_sock.close()

    def _cli_worker(self):
        while self.running:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                cmd = line.strip().lower()
                if cmd == "1":
                    self.log("CONSOLE", "Simulating SAFE request...")
                    self.log("CONSOLE", "Safe request executed: HTTP 200")
                elif cmd == "2":
                    self.log("CONSOLE", "Simulating RISKY request ('rm -rf ./database')...")
                    threading.Thread(
                        target=self.issue_challenge,
                        kwargs={"cmd": "rm -rf ./database", "risk": "CRITICAL", "cost": "$0.04"},
                        daemon=True
                    ).start()
                elif cmd == "s":
                    with self.esp32_lock:
                        hw = "CONNECTED" if self.esp32_socket else "DISCONNECTED"
                    with self.dashboard_lock:
                        dash_count = len(self.dashboard_clients)
                    self.log("STATUS", f"ESP32: {hw} | Dashboards: {dash_count} | Spent: ${self.spent:.2f}/${self.ceiling:.2f}")
                elif cmd == "q":
                    self.log("SERVER", "Shutting down mock proxy...")
                    self.running = False
                    break
            except Exception:
                break


if __name__ == "__main__":
    server = MockProxyServer()
    server.start()

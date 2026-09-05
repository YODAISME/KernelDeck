"""
KernelDeck — Standalone Mock ESP32 Hardware Device (Development Infrastructure)
==============================================================================
Owner: E (Integration / Demo / Safety) / B (Firmware reference)
Protocol Reference: PROTOCOL.md (Authoritative Source of Truth)

WARNING:
- This is a DEVELOPMENT / HARDWARE SIMULATOR for local testing without physical hardware.
- It connects to the proxy at `/ws/deck`.
- It NEVER executes received commands; commands are display-only.

Features:
- Pure Python 3 standard library (no pip dependencies required).
- Full RFC 6455 masked WebSocket client.
- Automatically handles PING/PONG and telemetry carrier.
- Terminal-based physical hardware interface simulation.
- Interactive [A] ALLOW / [K] KILL button prompt.
- Resilient auto-reconnect loop if connection is severed.
"""

import os
import sys
import time
import json
import socket
import struct
import base64
import threading
from urllib.parse import urlparse

# Default proxy host and port
DEFAULT_WS_URL = os.environ.get("KERNELDECK_DECK_URL", "ws://localhost:8080/ws/deck")
WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class WebSocketClientFrame:
    OP_TEXT = 0x1
    OP_CLOSE = 0x8
    OP_PING = 0x9
    OP_PONG = 0xA

    @staticmethod
    def encode(payload_bytes, opcode=OP_TEXT, mask=True):
        """Client-to-server frames MUST be masked according to RFC 6455."""
        length = len(payload_bytes)
        first_byte = 0x80 | (opcode & 0x0F)
        mask_key = os.urandom(4) if mask else b""
        masked_data = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload_bytes)) if mask else payload_bytes
        mask_bit = 0x80 if mask else 0x00

        if length <= 125:
            header = bytes([first_byte, mask_bit | length])
        elif length <= 65535:
            header = bytes([first_byte, mask_bit | 126]) + struct.pack(">H", length)
        else:
            header = bytes([first_byte, mask_bit | 127]) + struct.pack(">Q", length)

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


class MockESP32:
    def __init__(self, ws_url=DEFAULT_WS_URL):
        self.ws_url = ws_url
        self.running = True
        self.sock = None
        self.current_challenge = None
        self.challenge_lock = threading.Lock()
        self.spent = 0.0
        self.ceiling = 0.0

    def print_banner(self, status):
        print("\n" + "=" * 42)
        print("╔══════════════════════════════════════╗")
        print("║       KERNELDECK MOCK ESP32          ║")
        print("╠══════════════════════════════════════╣")
        status_line = f"║ STATUS: {status:<28} ║"
        print(status_line)
        print("╚══════════════════════════════════════╝")

    def connect(self):
        parsed = urlparse(self.ws_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 8080
        path = parsed.path or "/ws/deck"

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect((host, port))

        # Generate WebSocket handshake
        raw_key = os.urandom(16)
        sec_key = base64.b64encode(raw_key).decode("utf-8")
        req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {sec_key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        sock.sendall(req.encode("utf-8"))

        # Read handshake response
        resp = b""
        while b"\r\n\r\n" not in resp:
            chunk = sock.recv(1024)
            if not chunk:
                raise ConnectionError("Server closed connection during handshake")
            resp += chunk

        if b"101 Switching Protocols" not in resp:
            raise ConnectionError(f"Handshake failed: {resp.decode('latin1', errors='ignore')}")

        sock.settimeout(None)
        self.sock = sock
        return sock

    def send_json(self, obj):
        if not self.sock:
            return False
        try:
            payload = json.dumps(obj).encode("utf-8")
            frame = WebSocketClientFrame.encode(payload, opcode=WebSocketClientFrame.OP_TEXT, mask=True)
            self.sock.sendall(frame)
            return True
        except Exception as e:
            print(f"[ERR] Failed to send frame: {e}")
            return False

    def handle_message(self, text):
        try:
            msg = json.loads(text)
        except Exception as e:
            print(f"[WARN] Received malformed JSON from proxy: {e}")
            return

        msg_type = msg.get("type")

        if msg_type == "PING":
            # Protocol Section 2: PING carrier for telemetry
            self.spent = msg.get("spent", self.spent)
            self.ceiling = msg.get("ceiling", self.ceiling)
            # Reply with PONG
            self.send_json({"type": "PONG"})

        elif msg_type == "RESET_IDLE":
            # Protocol Section 2: RESET_IDLE
            with self.challenge_lock:
                was_challenging = self.current_challenge is not None
                self.current_challenge = None
            if was_challenging:
                print("\n[STATE_IDLE] Screen reset to IDLE. Spend: ${:.2f} / Ceiling: ${:.2f}".format(self.spent, self.ceiling))

        elif msg_type == "CHALLENGE":
            # Protocol Section 2: CHALLENGE
            req_id = msg.get("request_id")
            cmd = msg.get("cmd", "")
            risk = msg.get("risk", "UNKNOWN")
            cost = msg.get("cost", "$0.00")

            with self.challenge_lock:
                self.current_challenge = msg

            print("\n" + "!" * 42)
            print("⚠ CHALLENGE RECEIVED")
            print(f"Request ID : {req_id}")
            print(f"Risk Level : {risk}")
            print(f"Est Cost   : {cost}")
            print("\nCommand:")
            print(f"  {cmd}\n")
            print("[A] ALLOW")
            print("[K] KILL")
            print("Decision: ", end="", flush=True)

    def input_loop(self):
        """Monitors terminal input for physical button press simulation [A] or [K]."""
        while self.running:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                choice = line.strip().upper()

                with self.challenge_lock:
                    active = self.current_challenge

                if not active:
                    if choice in ("A", "K"):
                        print("[INFO] No challenge currently active on hardware display.")
                    continue

                if choice == "A":
                    # Emit ALLOW decision (Protocol Section 2)
                    decision = {
                        "type": "DECISION",
                        "request_id": active.get("request_id"),
                        "verdict": "ALLOW"
                    }
                    print("\n[BUTTON PRESSED] Operator selected: ALLOW")
                    self.send_json(decision)
                    with self.challenge_lock:
                        self.current_challenge = None

                elif choice == "K":
                    # Emit KILL decision (Protocol Section 2)
                    decision = {
                        "type": "DECISION",
                        "request_id": active.get("request_id"),
                        "verdict": "KILL"
                    }
                    print("\n[BUTTON PRESSED] Operator selected: KILL")
                    self.send_json(decision)
                    with self.challenge_lock:
                        self.current_challenge = None

                else:
                    print(f"Invalid input '{choice}'. Enter [A] for ALLOW or [K] for KILL: ", end="", flush=True)

            except Exception:
                break

    def run(self):
        input_thread = threading.Thread(target=self.input_loop, daemon=True)
        input_thread.start()

        while self.running:
            try:
                self.print_banner("CONNECTING...")
                self.connect()
                self.print_banner("CONNECTED")
                print("Hardware gate active. Waiting for proxy challenges...\n")

                while self.running:
                    opcode, data = WebSocketClientFrame.read_frame(self.sock)
                    if opcode is None or opcode == WebSocketClientFrame.OP_CLOSE:
                        print("\n[WARN] Connection closed by proxy.")
                        break
                    elif opcode == WebSocketClientFrame.OP_PING:
                        # Protocol ping frame
                        pong_frame = WebSocketClientFrame.encode(data, opcode=WebSocketClientFrame.OP_PONG, mask=True)
                        self.sock.sendall(pong_frame)
                    elif opcode == WebSocketClientFrame.OP_TEXT:
                        self.handle_message(data.decode("utf-8", errors="replace"))

            except Exception as e:
                self.print_banner("DISCONNECTED")
                print(f"[INFO] Connection failed: {e}")

            if self.sock:
                try:
                    self.sock.close()
                except Exception:
                    pass
                self.sock = None

            with self.challenge_lock:
                self.current_challenge = None

            if self.running:
                print("[INFO] Reconnecting in 3 seconds...")
                time.sleep(3.0)


if __name__ == "__main__":
    esp32 = MockESP32()
    try:
        esp32.run()
    except KeyboardInterrupt:
        print("\nStopping Mock ESP32.")

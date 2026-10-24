"""
KernelDeck Agent CLI — Comprehensive Unit Tests
===============================================
Owner: C
Protocol Reference: PROTOCOL.md
"""

import sys
import unittest
from pathlib import Path
import tempfile
import shutil

# Ensure agent-cli is in sys.path
agent_cli_root = Path(__file__).resolve().parent.parent
if str(agent_cli_root) not in sys.path:
    sys.path.insert(0, str(agent_cli_root))

import httpx
from openai import APIStatusError
from src.client import ProxyClient
from src.tools import ToolSandbox
from src.demo_script import preflight_denylist_check, setup_disposable_database, DENYLIST_PATTERNS


def create_mock_api_error(status_code: int, body_dict: dict) -> APIStatusError:
    req = httpx.Request("POST", "http://localhost:8080/v1/chat/completions")
    resp = httpx.Response(status_code=status_code, json=body_dict, request=req)
    return APIStatusError(
        message=f"Error code: {status_code}",
        response=resp,
        body=body_dict
    )


class TestAgentCLI(unittest.TestCase):

    def test_client_configuration(self):
        """CRITICAL: Verifies max_retries=0 and timeout >= 60s."""
        client = ProxyClient()
        self.assertEqual(client.client.max_retries, 0, "max_retries MUST be 0 to avoid silent SDK 408/5xx retries")
        self.assertGreaterEqual(client.timeout, 60.0, "timeout MUST be at least 60s to accommodate 30s challenge TTL")
        self.assertEqual(client.api_key, "kd_fake_laptop_key")

    def test_error_envelope_parsing_403(self):
        """Tests parsing of HARDWARE_DENIED (HTTP 403)."""
        client = ProxyClient()
        mock_body = {
            "error": {
                "message": "Execution blocked by KernelDeck hardware interlock: Denied by Operator.",
                "type": "hardware_interlock_violation",
                "param": None,
                "code": "HARDWARE_DENIED"
            }
        }
        err = create_mock_api_error(403, mock_body)
        status_code, code, message = client.parse_api_error(err)
        self.assertEqual(status_code, 403)
        self.assertEqual(code, "HARDWARE_DENIED")
        self.assertIn("Denied by Operator", message)

    def test_error_envelope_parsing_408(self):
        """Tests parsing of HARDWARE_TIMEOUT (HTTP 408)."""
        client = ProxyClient()
        mock_body = {
            "error": {
                "message": "KernelDeck challenge expired after 30s without operator response.",
                "type": "hardware_interlock_timeout",
                "param": None,
                "code": "HARDWARE_TIMEOUT"
            }
        }
        err = create_mock_api_error(408, mock_body)
        status_code, code, message = client.parse_api_error(err)
        self.assertEqual(status_code, 408)
        self.assertEqual(code, "HARDWARE_TIMEOUT")
        self.assertIn("expired after 30s", message)

    def test_error_envelope_parsing_503(self):
        """Tests parsing of HARDWARE_OFFLINE (HTTP 503)."""
        client = ProxyClient()
        mock_body = {
            "error": {
                "message": "KernelDeck hardware offline. Safety policy requires physical interlock presence.",
                "type": "hardware_interlock_unavailable",
                "param": None,
                "code": "HARDWARE_OFFLINE"
            }
        }
        err = create_mock_api_error(503, mock_body)
        status_code, code, message = client.parse_api_error(err)
        self.assertEqual(status_code, 503)
        self.assertEqual(code, "HARDWARE_OFFLINE")
        self.assertIn("hardware offline", message)

    def test_preflight_scanner_clean_payloads(self):
        """Asserts pre-flight check passes for clean safe payloads."""
        clean_payloads = [
            "Please read the database schema to inspect tables.",
            "Append a maintenance status into the log file."
        ]
        # Should not raise
        preflight_denylist_check(clean_payloads)

    def test_preflight_scanner_catches_denylist_keywords(self):
        """Asserts pre-flight check catches dangerous commands."""
        forbidden_payloads = [
            ["Inspect database", "Now run rm -rf ./database please"],
            ["Execute DROP TABLE users;"],
            ["Run TRUNCATE TABLE config;"],
            ["Execute mkfs /dev/sda1"]
        ]
        for payloads in forbidden_payloads:
            with self.assertRaises(ValueError):
                preflight_denylist_check(payloads)

    def test_sanitized_seeded_database(self):
        """Verifies setup_disposable_database produces 0 denylist matches."""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            db_dir = temp_dir / "database"
            setup_disposable_database(db_dir)
            self.assertTrue(db_dir.exists())
            self.assertTrue((db_dir / "schema.sql").exists())
            self.assertTrue((db_dir / "records.db").exists())

            schema_text = (db_dir / "schema.sql").read_text(encoding="utf-8")
            # Verify no denylist strings in schema
            for pattern in DENYLIST_PATTERNS:
                import re
                self.assertIsNone(
                    re.search(pattern, schema_text, re.IGNORECASE),
                    f"Forbidden pattern '{pattern}' found in seeded schema.sql!"
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_tool_sandbox_confinement(self):
        """Verifies sandbox allows local operations but blocks traversal escapes."""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            sandbox = ToolSandbox(base_dir=temp_dir)
            # Safe write and read
            res = sandbox.write_file("test.txt", "hello world")
            self.assertIn("File written", res)
            content = sandbox.read_file("test.txt")
            self.assertEqual(content, "hello world")

            # Traversal attempt must be rejected
            with self.assertRaises(PermissionError):
                sandbox.read_file("../../outside.txt")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

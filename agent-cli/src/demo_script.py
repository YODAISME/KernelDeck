"""
KernelDeck Agent CLI — Deterministic 30-Second Stage Demo Scenario
==================================================================
Owner: C
Protocol Reference: PROTOCOL.md & PROJECT-EXPLAINER.md
"""

import os
import re
import sys
import time
import shutil
import json
from pathlib import Path

from src.client import ProxyClient
from src.tools import ToolSandbox, TOOLS_SCHEMA
from src.ui import (
    print_banner,
    print_step_header,
    print_assistant_thought,
    print_tool_call,
    print_tool_result,
    format_error_code,
    InterlockSpinner
)

# Denylist patterns per proxy policy engine
DENYLIST_PATTERNS = [
    r"\brm\s+-[rf]{1,2}\b",
    r"\brmdir\b",
    r"\bmkfs\b",
    r"\bformat\s+[a-z]:\b",
    r"\bdd\s+if=",
    r"\bdrop\s+table\b",
    r"\bdrop\s+database\b",
    r"\btruncate\s+table\b"
]


def preflight_denylist_check(safe_payloads: list):
    """
    Scans all safe step payloads before execution begins.
    Ensures that no denylist keywords appear in safe turns, which would cause premature gating.
    """
    for idx, payload in enumerate(safe_payloads, 1):
        for pattern in DENYLIST_PATTERNS:
            match = re.search(pattern, payload, re.IGNORECASE)
            if match:
                raise ValueError(
                    f"PRE-FLIGHT CHECK FAILED: Safe Step {idx} contains forbidden denylist string '{match.group(0)}'."
                )


def setup_disposable_database(db_dir: Path):
    """
    Initializes a throwaway scratch directory for safety testing.
    Contents are strictly sanitized of all denylist strings.
    """
    if db_dir.exists():
        shutil.rmtree(db_dir, ignore_errors=True)
    db_dir.mkdir(parents=True, exist_ok=True)

    # Clean schema.sql (Additive DDL only, zero DROP/TRUNCATE keywords)
    schema_content = (
        "-- KernelDeck Demo Database Schema\n"
        "CREATE TABLE IF NOT EXISTS users (\n"
        "    id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
        "    username TEXT NOT NULL,\n"
        "    email TEXT NOT NULL,\n"
        "    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n"
        ");\n"
        "CREATE TABLE IF NOT EXISTS config (\n"
        "    key TEXT PRIMARY KEY,\n"
        "    value TEXT\n"
        ");\n"
        "INSERT INTO users (username, email) VALUES ('alice', 'alice@demo.internal');\n"
        "INSERT INTO users (username, email) VALUES ('bob', 'bob@demo.internal');\n"
    )
    (db_dir / "schema.sql").write_text(schema_content, encoding="utf-8")

    # Clean records.db (binary placeholder)
    (db_dir / "records.db").write_bytes(b"\x00\x01\x02\x03\x04SQLite format 3\x00")


def run_stage_demo(proxy_url=None):
    """
    Runs the 30-second presentation demo from PROJECT-EXPLAINER.md:
    1. Pre-flight check & setup of throwaway ./database directory.
    2. Safe Step 1: Reads database schema (instant pass-through).
    3. Safe Step 2: Writes maintenance log (instant pass-through).
    4. Staged Risky Step: Agent triggers 'rm -rf ./database'.
       - Must sit in the last message of the request!
       - Pauses mid-flight while hardware interlock waits for human decision.
       - Operator ALLOW or KILL executed and visualized.
    """
    print_banner()

    root_dir = Path.cwd()
    db_dir = root_dir / "database"

    # Pre-flight Check: verify safe payloads contain no denylist triggers
    safe_step1_text = "Please read the database schema to inspect the existing tables."
    safe_step2_text = "Append a maintenance timestamp comment into the database directory."
    preflight_denylist_check([safe_step1_text, safe_step2_text])

    print("[PRE-FLIGHT] Sanitized safe step payloads verified (0 denylist matches).")
    print("[PRE-FLIGHT] Setting up disposable scratch folder at ./database ...")
    setup_disposable_database(db_dir)
    print("[PRE-FLIGHT] Scratch database initialized successfully.\n")

    client = ProxyClient(base_url=proxy_url)
    sandbox = ToolSandbox(base_dir=root_dir)

    # -------------------------------------------------------------
    # Step 1: Safe Operation (Read File)
    # -------------------------------------------------------------
    print_step_header(1, "Safe Operation — Read Database Schema")
    print_assistant_thought("Inspecting local database definition before maintenance...")
    print_tool_call("read_file", {"path": "database/schema.sql"})

    messages_step1 = [
        {"role": "system", "content": "You are an autonomous AI coding assistant."},
        {"role": "user", "content": safe_step1_text}
    ]

    spinner = InterlockSpinner("Relaying to proxy")
    spinner.start()
    try:
        # Non-gated safe request passes through instantly
        resp = client.create_completion(messages=messages_step1, tools=TOOLS_SCHEMA)
        spinner.stop()
    except Exception as e:
        spinner.stop()
        print(f"Unexpected error on safe step 1: {e}")
        return False

    res1 = sandbox.read_file("database/schema.sql")
    print_tool_result("read_file", f"Loaded {len(res1)} characters (CREATE TABLE users...)")
    time.sleep(1.0)

    # -------------------------------------------------------------
    # Step 2: Safe Operation (Write Maintenance Log)
    # -------------------------------------------------------------
    print_step_header(2, "Safe Operation — Record Maintenance Timestamp")
    print_assistant_thought("Writing audit entry to maintenance log...")
    print_tool_call("write_file", {"path": "database/maintenance.log", "content": "STATUS=HEALTHY"})

    messages_step2 = [
        {"role": "system", "content": "You are an autonomous AI coding assistant."},
        {"role": "user", "content": safe_step2_text}
    ]

    spinner = InterlockSpinner("Relaying to proxy")
    spinner.start()
    try:
        resp = client.create_completion(messages=messages_step2, tools=TOOLS_SCHEMA)
        spinner.stop()
    except Exception as e:
        spinner.stop()
        print(f"Unexpected error on safe step 2: {e}")
        return False

    res2 = sandbox.write_file("database/maintenance.log", f"LOG_TIMESTAMP={time.time()}\nSTATUS=HEALTHY\n")
    print_tool_result("write_file", res2)
    time.sleep(1.2)

    # -------------------------------------------------------------
    # Step 3: Staged Dangerous Operation (rm -rf ./database)
    # -------------------------------------------------------------
    print_step_header(3, "Risky Operation — Autonomous Cleanup of Directory")
    print_assistant_thought("Maintenance complete. Cleaning up scratch database directory...")

    risky_cmd = "rm -rf ./database"
    print_tool_call("run_command", {"command": risky_cmd})

    # CRITICAL MUST-DO 2:
    # The proxy scans ONLY the last entry in messages: its content, or tool_calls arguments.
    # Therefore, the risky command MUST sit in the last message!
    messages_risky = [
        {"role": "system", "content": "You are an autonomous AI coding assistant."},
        {"role": "user", "content": f"Execute the cleanup operation: {risky_cmd}"}
    ]

    spinner = InterlockSpinner("Sending execution request")
    spinner.start()

    try:
        # This call WILL pause mid-flight on the proxy!
        resp = client.create_completion(messages=messages_risky, tools=TOOLS_SCHEMA)
        spinner.stop()

        # If we reach here, the proxy returned HTTP 200 OK -> Operator pressed ALLOW!
        print("\n[OPERATOR APPROVED COMMAND]")
        print("  Interlock Policy: Physical ALLOW button pressed by operator.")
        # Execute locally ONLY after HTTP 200 returned
        result = sandbox.run_command(risky_cmd)
        print_tool_result("run_command", result)
        print(f"  Status: Database directory removed: {not db_dir.exists()}")
        return True

    except Exception as err:
        spinner.stop()
        status_code, code, message = client.parse_api_error(err)

        # Distinguish all three cases by e.code
        format_error_code(code, message)

        if code == "HARDWARE_DENIED":
            # Command was rejected by physical KILL button
            print("  [SAFETY INTEGRITY CONFIRMED]: Command was blocked from running locally.")
            print(f"  [VERIFICATION]: Scratch database directory still exists: {db_dir.exists()}\n")
            return True
        elif code == "HARDWARE_TIMEOUT":
            print("  [SAFETY INTEGRITY CONFIRMED]: Challenge timed out; command was blocked.\n")
            return True
        elif code == "HARDWARE_OFFLINE":
            print("  [SAFETY INTEGRITY CONFIRMED]: Hardware disconnected; fail-closed safety preserved.\n")
            return True
        else:
            print(f"  Unknown error during gate test: status={status_code}, code={code}, msg={message}")
            return False

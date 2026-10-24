"""
KernelDeck Agent CLI — Main Entry Point
=======================================
Owner: C
Protocol Reference: PROTOCOL.md & PROJECT-EXPLAINER.md
"""

import os
import sys
from pathlib import Path
import argparse

# -------------------------------------------------------------
# 1. Windows Console UTF-8 Reconfiguration
# -------------------------------------------------------------
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# -------------------------------------------------------------
# 2. Path Normalization for Direct or Module Invocation
# -------------------------------------------------------------
# Ensure 'agent-cli' root is in sys.path so 'from src.X import ...' resolves cleanly
pkg_root = Path(__file__).resolve().parent.parent
if str(pkg_root) not in sys.path:
    sys.path.insert(0, str(pkg_root))

from dotenv import load_dotenv
load_dotenv()

from src.demo_script import run_stage_demo
from src.agent import run_interactive_agent


def main():
    parser = argparse.ArgumentParser(
        description="KernelDeck Agent CLI — Hardware-Gated AI Coding Assistant"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run the deterministic 30-second stage presentation demo."
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run free-form interactive agent chat session (default)."
    )
    parser.add_argument(
        "--proxy-url",
        type=str,
        default=os.environ.get("KERNELDECK_PROXY_URL", "http://localhost:8080/v1"),
        help="KernelDeck Proxy URL endpoint (default: http://localhost:8080/v1)."
    )

    args = parser.parse_args()

    if args.demo:
        success = run_stage_demo(proxy_url=args.proxy_url)
        sys.exit(0 if success else 1)
    else:
        run_interactive_agent(proxy_url=args.proxy_url)


if __name__ == "__main__":
    main()

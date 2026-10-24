"""
KernelDeck Agent CLI — UI & Terminal Presentation Engine
========================================================
Owner: C
Protocol Reference: PROTOCOL.md
"""

import sys
import time
import threading
from colorama import Fore, Style, init

init(autoreset=True)


class InterlockSpinner:
    """
    Background daemon thread spinner for API calls.
    Transitions to an explicit interlock indicator if the call exceeds 1.2 seconds,
    meaning the proxy has frozen the request mid-flight awaiting a physical button press.
    """
    def __init__(self, message="Agent thinking"):
        self.message = message
        self.running = False
        self.thread = None
        self.interlock_active = False

    def _spin(self):
        spinner_chars = ["|", "/", "-", "\\"]
        idx = 0
        start_time = time.time()
        while self.running:
            elapsed = time.time() - start_time
            if elapsed > 1.5 and not self.interlock_active:
                self.interlock_active = True
                sys.stdout.write("\r" + " " * 78 + "\r")
                sys.stdout.write(
                    f"{Fore.YELLOW}{Style.BRIGHT}[WAIT] Hardware interlock engaged: awaiting operator verdict on ESP32...{Style.RESET_ALL}\n"
                )
                sys.stdout.flush()

            char = spinner_chars[idx % len(spinner_chars)]
            status_text = "Holding for hardware verdict..." if self.interlock_active else f"{self.message}..."
            sys.stdout.write(f"\r{Fore.CYAN}{char} {status_text}{Style.RESET_ALL}")
            sys.stdout.flush()
            time.sleep(0.1)
            idx += 1

        # Clear line on stop
        sys.stdout.write("\r" + " " * 78 + "\r")
        sys.stdout.flush()

    def start(self):
        self.running = True
        self.interlock_active = False
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.5)


def print_banner():
    """Renders the top banner using ASCII borders for Windows console compatibility."""
    bar = "=" * 62
    print(f"\n{Fore.CYAN}{Style.BRIGHT}+{bar}+")
    print(f"{Fore.CYAN}{Style.BRIGHT}|             KERNELDECK // AGENT TERMINAL v0.1.0              |")
    print(f"{Fore.CYAN}{Style.BRIGHT}|        Hardware-Gated Out-of-Band Execution Boundary         |")
    print(f"{Fore.CYAN}{Style.BRIGHT}+{bar}+{Style.RESET_ALL}\n")


def print_step_header(step_num: int, title: str):
    print(f"\n{Fore.GREEN}{Style.BRIGHT}--- [STEP {step_num}] {title} ---{Style.RESET_ALL}")


def print_assistant_thought(thought: str):
    print(f"{Fore.BLUE}{Style.BRIGHT}[AGENT THOUGHT]{Style.RESET_ALL} {thought}")


def print_tool_call(tool_name: str, args_dict: dict):
    args_str = ", ".join(f"{k}={v!r}" for k, v in args_dict.items())
    print(f"{Fore.MAGENTA}[TOOL CALL]{Style.RESET_ALL} {Fore.WHITE}{tool_name}({args_str}){Style.RESET_ALL}")


def print_tool_result(tool_name: str, result_summary: str, is_error: bool = False):
    color = Fore.RED if is_error else Fore.GREEN
    tag = "[TOOL ERROR]" if is_error else "[TOOL RESULT]"
    print(f"{color}{tag}{Style.RESET_ALL} {tool_name} -> {result_summary}")


def format_error_code(code: str, message: str):
    """
    Renders KernelDeck error envelopes per PROTOCOL.md Section 6.
    Distinguishes all three cases by e.code.
    """
    if code == "HARDWARE_DENIED":
        print(f"\n{Fore.RED}{Style.BRIGHT}[OPERATOR REJECTED COMMAND]{Style.RESET_ALL}")
        print(f"{Fore.RED}  Interlock Policy: Execution blocked by KernelDeck physical interlock: Denied by Operator.{Style.RESET_ALL}")
        if message:
            print(f"{Fore.WHITE}  Detail: {message}{Style.RESET_ALL}\n")
    elif code == "HARDWARE_TIMEOUT":
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}[CHALLENGE EXPIRED - ABORTED]{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}  Interlock Policy: 30s challenge TTL elapsed without physical operator response.{Style.RESET_ALL}")
        if message:
            print(f"{Fore.WHITE}  Detail: {message}{Style.RESET_ALL}\n")
    elif code == "HARDWARE_OFFLINE":
        print(f"\n{Fore.RED}{Style.DIM}[DEVICE DISCONNECTED - SYSTEM HALTED]{Style.RESET_ALL}")
        print(f"{Fore.RED}{Style.DIM}  Interlock Policy: KernelDeck hardware offline. Safety policy requires physical interlock presence.{Style.RESET_ALL}")
        if message:
            print(f"{Fore.WHITE}  Detail: {message}{Style.RESET_ALL}\n")
    else:
        print(f"\n{Fore.MAGENTA}[API STATUS ERROR ({code})]{Style.RESET_ALL}: {message}\n")

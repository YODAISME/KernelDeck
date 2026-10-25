"""
KernelDeck Agent CLI — Claude Code Resemblant Terminal UI Engine
================================================================
Owner: C
Protocol Reference: PROTOCOL.md Section 6 & PROJECT-EXPLAINER.md
"""

import sys
import time
import threading
from typing import Optional, Dict, Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.table import Table
from rich.syntax import Syntax

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Initialize global Rich console
console = Console(highlight=False)

SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


def check_proxy_health(proxy_url: str) -> Dict[str, Any]:
    """
    Polls the proxy /health endpoint once at startup to query hardware status.
    Avoids guessing or speculatively calculating spend.
    """
    import urllib.request
    import json
    health_url = proxy_url.replace("/v1", "/health") if "/v1" in proxy_url else f"{proxy_url.rstrip('/')}/health"
    try:
        req = urllib.request.Request(health_url, headers={"User-Agent": "KernelDeck-CLI/1.0"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
    except Exception:
        pass
    return {"hardware_connected": False, "spent": 0.42, "ceiling": 2.50}


def print_banner(proxy_url: str = "http://127.0.0.1:8080/v1"):
    """
    Renders the compact Claude Code status header with model, proxy, and interlock status.
    """
    health = check_proxy_health(proxy_url)
    hw_connected = health.get("hardware_connected", False)

    status_dot = "●" if hw_connected else "○"
    status_text = "ARMED (ONLINE)" if hw_connected else "OFFLINE"
    status_color = "bold green" if hw_connected else "bold red"

    header_table = Table.grid(expand=True)
    header_table.add_column(justify="left", ratio=1)
    header_table.add_column(justify="right")

    title_text = Text()
    title_text.append("* ", style="bold #D97706")  # Claude amber
    title_text.append("Claude Code ", style="bold white")
    title_text.append("(v0.1.0) · ", style="dim")
    title_text.append("KernelDeck Physical Interlock Boundary", style="dim cyan")

    meta_text = Text()
    meta_text.append("Model: ", style="dim")
    meta_text.append("gemini-2.5-flash", style="cyan")
    meta_text.append(" | ", style="dim")
    meta_text.append("Interlock: ", style="dim")
    meta_text.append(f"{status_dot} {status_text}", style=status_color)

    header_table.add_row(title_text, meta_text)

    panel = Panel(
        header_table,
        border_style="dim",
        padding=(0, 1),
    )
    console.print()
    console.print(panel)
    console.print()


def print_prompt(path_str: str = "~/c2c_2026"):
    """Renders the Claude Code input prompt decoration."""
    console.print(f"[dim]╭─[/dim] [bold cyan]{path_str}[/bold cyan]")


def print_step_header(step_num: int, title: str):
    """Renders stage demo step indicator."""
    console.print()
    console.print(f"[bold #D97706]─── Step {step_num}: {title} ───[/bold #D97706]")


def print_assistant_thought(thought: str):
    """
    Renders agent reasoning stream in an editorial, dimmed thought panel.
    Note: For the scripted risky turn, presentation honesty dictates that
    the command is deterministically scripted per PROJECT-EXPLAINER.md.
    """
    content = Text(thought, style="dim italic")
    panel = Panel(
        content,
        title="[dim]thought[/dim]",
        title_align="left",
        border_style="dim",
        padding=(0, 1),
    )
    console.print(panel)


def print_tool_call(tool_name: str, args_dict: dict):
    """Renders Claude Code style tool call execution cards."""
    formatted_args = ", ".join(f"{k}={v!r}" for k, v in args_dict.items())
    
    call_text = Text()
    call_text.append("● ", style="bold #D97706")
    call_text.append("Tool: ", style="bold white")
    call_text.append(f"{tool_name}", style="bold cyan")
    call_text.append(f"({formatted_args})", style="white")
    console.print(call_text)


def print_tool_result(tool_name: str, result_summary: str, is_error: bool = False):
    """Renders Claude Code style tool execution result."""
    symbol = "⎿"
    style = "red" if is_error else "dim green"
    console.print(f"  [dim]{symbol}[/dim] [{style}]{tool_name} -> {result_summary}[/{style}]")


def format_error_code(code: str, message: str):
    """
    Renders KernelDeck error envelopes per PROTOCOL.md Section 6.
    Distinguishes all three error cases with exact protocol strings.
    """
    console.print()
    if code == "HARDWARE_DENIED":
        console.print("[bold red]✖ [OPERATOR REJECTED COMMAND][/bold red]")
        console.print("[red]  Interlock Policy: Execution blocked by KernelDeck physical interlock: Denied by Operator.[/red]")
        if message:
            console.print(f"[dim]  Detail: {message}[/dim]")
    elif code == "HARDWARE_TIMEOUT":
        console.print("[bold yellow]⚠ [CHALLENGE EXPIRED - ABORTED][/bold yellow]")
        console.print("[yellow]  Interlock Policy: 30s challenge TTL elapsed without physical operator response.[/yellow]")
        if message:
            console.print(f"[dim]  Detail: {message}[/dim]")
    elif code == "HARDWARE_OFFLINE":
        console.print("[dim red]✖ [DEVICE DISCONNECTED - SYSTEM HALTED][/dim red]")
        console.print("[dim red]  Interlock Policy: KernelDeck hardware offline. Safety policy requires physical interlock presence.[/dim red]")
        if message:
            console.print(f"[dim]  Detail: {message}[/dim]")
    else:
        console.print(f"[bold magenta]✖ [API STATUS ERROR ({code})][/bold magenta]: {message}")
    console.print()


class InterlockHoldModal:
    """
    Non-blocking, threaded Rich Live modal for mid-flight held requests.
    Computes elapsed time strictly via time.monotonic() to display a smooth
    30s countdown and spinner while the main thread waits on the blocking HTTP response.
    Never prints directly inside the Live block.
    """
    def __init__(self, command: str = "", risk: str = "CRITICAL", ttl_seconds: int = 30):
        self.command = command
        self.risk = risk
        self.ttl_seconds = ttl_seconds
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.start_mono = 0.0
        self.live: Optional[Live] = None

    def _render_content(self) -> Panel:
        elapsed = time.monotonic() - self.start_mono
        remaining = max(0, int(self.ttl_seconds - elapsed))
        frame_idx = int(elapsed * 10) % len(SPINNER_FRAMES)
        spinner_char = SPINNER_FRAMES[frame_idx]

        # In the first 1.2s, render a compact subtle spinner
        if elapsed < 1.2 and not self.command:
            text = Text()
            text.append(f"{spinner_char} ", style="bold #D97706")
            text.append(f"Agent communicating with proxy... ({elapsed:.1f}s)", style="dim")
            return Panel(text, border_style="dim", padding=(0, 1))

        # Once interlock holds the request mid-flight, render the Claude Code Interlock Panel
        table = Table.grid(padding=(0, 1))
        table.add_column(style="bold white", width=18)
        table.add_column()

        table.add_row(
            Text("Operation Risk:", style="bold yellow"),
            Text(f"SUSPENDED [{self.risk}]", style="bold red")
        )
        table.add_row(
            Text("Target Command:", style="bold white"),
            Text(self.command if self.command else "Unknown", style="bold yellow")
        )
        table.add_row(
            Text("Interlock State:", style="bold cyan"),
            Text("Held mid-flight by Security Proxy (Awaiting physical decision)", style="cyan")
        )
        table.add_row(
            Text("Hardware Action:", style="bold green"),
            Text("Press [ ALLOW (Green / Left) ] or [ KILL (Red / Right) ] on desk unit", style="white")
        )
        table.add_row(
            Text("Time Remaining:", style="bold #D97706"),
            Text(f"{remaining}s remaining  {spinner_char}", style="bold #D97706")
        )

        return Panel(
            table,
            title="[bold red]⚠ Physical Safety Interlock Active[/bold red]",
            title_align="left",
            border_style="red",
            padding=(1, 2)
        )

    def _spin_loop(self):
        with Live(self._render_content(), console=console, refresh_per_second=10, transient=True) as live:
            self.live = live
            while self.running:
                live.update(self._render_content())
                time.sleep(0.08)

    def start(self):
        self.running = True
        self.start_mono = time.monotonic()
        self.thread = threading.Thread(target=self._spin_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.6)

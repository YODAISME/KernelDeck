"""
KernelDeck Agent CLI — Interactive Agent Loop
=============================================
Owner: C
Protocol Reference: PROTOCOL.md
"""

import sys
import json
from pathlib import Path

from src.client import ProxyClient
from src.tools import ToolSandbox, TOOLS_SCHEMA
from src.ui import (
    console,
    print_banner,
    print_prompt,
    print_tool_call,
    print_tool_result,
    format_error_code,
    InterlockHoldModal
)


def run_interactive_agent(proxy_url=None):
    """
    Runs an interactive terminal session where a user can enter arbitrary prompts.
    Handles tool calls and gracefully intercepts hardware interlock events.
    """
    effective_url = proxy_url or "http://127.0.0.1:8080/v1"
    print_banner(proxy_url=effective_url)
    console.print("[dim]Interactive session started. Type 'exit' or 'quit' to end session.[/dim]\n")

    client = ProxyClient(base_url=effective_url)
    sandbox = ToolSandbox()

    messages = [
        {
            "role": "system",
            "content": (
                "You are KernelDeck Agent, an autonomous coding assistant. You have tools to inspect files, "
                "edit code, and run shell commands. Operations are subject to physical hardware safety policies."
            )
        }
    ]

    cwd_str = Path.cwd().name

    while True:
        try:
            print_prompt(f"~/{cwd_str}")
            user_input = input("╰─❯ ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                console.print("\n[dim]Exiting KernelDeck Agent. Goodbye.[/dim]")
                break

            messages.append({"role": "user", "content": user_input})

            # Process conversation turn
            process_turn(client, sandbox, messages, user_input)

        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Session interrupted. Exiting.[/dim]")
            break


def process_turn(client: ProxyClient, sandbox: ToolSandbox, messages: list, user_prompt: str = ""):
    """Processes a single conversational turn with tool calling and error catching."""
    # Start non-blocking hold modal in background
    hold_modal = InterlockHoldModal(command=user_prompt[:50] if "rm " in user_prompt else "", risk="EVALUATING")
    hold_modal.start()

    try:
        response = client.create_completion(messages=messages, tools=TOOLS_SCHEMA)
        hold_modal.stop()

        choice = response.choices[0]
        msg = choice.message

        if msg.content:
            console.print(f"\n[bold #D97706]Claude[/bold #D97706] [dim]>[/dim] {msg.content}\n")

        if msg.tool_calls:
            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in msg.tool_calls
                ]
            })

            for tc in msg.tool_calls:
                func_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except Exception:
                    args = {}

                print_tool_call(func_name, args)

                # Tool execution
                if func_name == "read_file":
                    res = sandbox.read_file(args.get("path", ""))
                    print_tool_result(func_name, f"Read {len(res)} characters")
                elif func_name == "write_file":
                    res = sandbox.write_file(args.get("path", ""), args.get("content", ""))
                    print_tool_result(func_name, res)
                elif func_name == "run_command":
                    res = sandbox.run_command(args.get("command", ""))
                    print_tool_result(func_name, res)
                else:
                    print_tool_result(func_name, f"Unknown tool: {func_name}", is_error=True)

    except Exception as err:
        hold_modal.stop()
        status_code, code, message = client.parse_api_error(err)
        format_error_code(code, message)

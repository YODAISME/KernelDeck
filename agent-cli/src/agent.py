"""
KernelDeck Agent CLI — Interactive Agent Loop
=============================================
Owner: C
Protocol Reference: PROTOCOL.md
"""

import sys
import json
from colorama import Fore, Style

from src.client import ProxyClient
from src.tools import ToolSandbox, TOOLS_SCHEMA
from src.ui import (
    print_banner,
    print_tool_call,
    print_tool_result,
    format_error_code,
    InterlockSpinner
)


def run_interactive_agent(proxy_url=None):
    """
    Runs an interactive terminal session where a user can enter arbitrary prompts.
    Handles tool calls and gracefully intercepts hardware interlock events.
    """
    print_banner()
    print(f"{Fore.GREEN}Interactive mode started. Type 'exit' or 'quit' to end session.{Style.RESET_ALL}\n")

    client = ProxyClient(base_url=proxy_url)
    sandbox = ToolSandbox()

    messages = [
        {
            "role": "system",
            "content": (
                "You are KernelDeck Agent, an AI coding assistant. You have tools to inspect files, "
                "edit code, and run shell commands. Operations are subject to physical hardware safety policies."
            )
        }
    ]

    while True:
        try:
            user_input = input(f"{Fore.GREEN}{Style.BRIGHT}User > {Style.RESET_ALL}").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                print("\nExiting KernelDeck Agent. Goodbye.")
                break

            messages.append({"role": "user", "content": user_input})

            # Process conversation turn
            process_turn(client, sandbox, messages)

        except (KeyboardInterrupt, EOFError):
            print("\nSession interrupted. Exiting.")
            break


def process_turn(client: ProxyClient, sandbox: ToolSandbox, messages: list):
    """Processes a single conversational turn with tool calling and error catching."""
    spinner = InterlockSpinner("Agent communicating with proxy")
    spinner.start()

    try:
        response = client.create_completion(messages=messages, tools=TOOLS_SCHEMA)
        spinner.stop()

        choice = response.choices[0]
        msg = choice.message

        if msg.content:
            print(f"\n{Fore.CYAN}{Style.BRIGHT}Agent >{Style.RESET_ALL} {msg.content}\n")

        if msg.tool_calls:
            # Append assistant message with tool calls to history
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

                # Tool execution locally (only reached after HTTP 200 from proxy!)
                tool_output = sandbox.execute_tool_call(func_name, args)
                print_tool_result(func_name, tool_output[:120] + "..." if len(tool_output) > 120 else tool_output)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_output
                })

            # Follow up turn after tool execution
            process_turn(client, sandbox, messages)

    except Exception as err:
        spinner.stop()
        status_code, code, message = client.parse_api_error(err)
        format_error_code(code, message)

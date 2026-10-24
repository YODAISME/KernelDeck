"""
KernelDeck Agent CLI — OpenAI SDK Client & Error Parser
=======================================================
Owner: C
Protocol Reference: PROTOCOL.md
"""

import os
import json
from openai import OpenAI, APIStatusError


class ProxyClient:
    """
    OpenAI-compatible client communicating exclusively with KernelDeck Proxy.
    The real upstream Gemini credentials live strictly on the proxy server.
    """
    def __init__(self, base_url=None, api_key=None, timeout=60.0):
        raw_url = base_url or os.getenv("KERNELDECK_PROXY_URL", "http://127.0.0.1:8080/v1")
        # On Windows, resolving 'localhost' attempts IPv6 (::1) first and delays for ~2s
        # before falling back to IPv4 (127.0.0.1). Normalize to 127.0.0.1 for instant response.
        if "://localhost" in raw_url:
            raw_url = raw_url.replace("://localhost", "://127.0.0.1")
        self.base_url = raw_url
        self.api_key = api_key or "kd_fake_laptop_key"
        self.timeout = timeout

        # CRITICAL MUST-DO 1: max_retries=0 stops SDK from silently retrying 408 & 5xx.
        # Without it, a 30s timeout causes 2 retries (90s+ hang) and duplicate challenges.
        # CRITICAL MUST-DO 2: timeout=60.0s provides ample headroom over 30s challenge TTL.
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            max_retries=0,
            timeout=self.timeout
        )

    def parse_api_error(self, err: APIStatusError):
        """
        Extracts status_code, error code string, and message from OpenAI SDK errors.
        Robustly navigates nested OpenAI error envelopes across HTTP 403, 408, and 503.
        """
        status_code = getattr(err, "status_code", 500)
        code = getattr(err, "code", None)
        message = getattr(err, "message", str(err))

        # Deep inspection into err.body or err.response
        body = getattr(err, "body", None)
        if isinstance(body, dict):
            err_dict = body.get("error", {})
            if isinstance(err_dict, dict):
                code = err_dict.get("code", code)
                message = err_dict.get("message", message)
        elif hasattr(err, "response") and err.response is not None:
            try:
                data = err.response.json()
                if isinstance(data, dict):
                    err_dict = data.get("error", {})
                    if isinstance(err_dict, dict):
                        code = err_dict.get("code", code)
                        message = err_dict.get("message", message)
            except Exception:
                pass

        return status_code, code, message

    def create_completion(self, messages, tools=None, tool_choice=None, model="gemini-2.5-flash"):
        """
        Standard OpenAI chat completion request.
        Non-streaming (stream=False) for demo reliability and clean spend tracking.
        """
        kwargs = {
            "model": model,
            "messages": messages,
            "stream": False
        }
        if tools:
            kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice

        return self.client.chat.completions.create(**kwargs)

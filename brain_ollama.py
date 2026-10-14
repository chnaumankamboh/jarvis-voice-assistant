"""Local brain: an open model running in Ollama. Free, private, no API key.

Setup once:
  - install Ollama from https://ollama.com and leave it running
  - pull a tool-capable model:  ollama pull llama3.2:3b   (or: python pull_model.py)
"""
import json

import ollama

import config
from brain import run_tool, trim_history
from tools import TOOL_SCHEMAS

_client = ollama.Client(host=config.OLLAMA_HOST) if config.OLLAMA_HOST else ollama.Client()


def _get(obj, key):
    """Read a field whether the Ollama client returns dicts or objects."""
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


# Our schemas are Anthropic-style; convert once so tools.py serves both brains.
_TOOLS = [
    {
        "type": "function",
        "function": {"name": s["name"], "description": s["description"], "parameters": s["input_schema"]},
    }
    for s in TOOL_SCHEMAS
]


def describe():
    return f"local model {config.OLLAMA_MODEL} via Ollama"


def check():
    try:
        listing = _client.list()
    except Exception:
        return "I can't reach Ollama. Start the Ollama app, then run me again."
    have = {_get(m, "model") or _get(m, "name") for m in (_get(listing, "models") or [])}
    want = config.OLLAMA_MODEL if ":" in config.OLLAMA_MODEL else config.OLLAMA_MODEL + ":latest"
    if want not in have:
        return f"The model {config.OLLAMA_MODEL} isn't downloaded yet. Run: python pull_model.py"
    return None


def think(user_text, history):
    if not history:
        history.append({"role": "system", "content": config.SYSTEM_PROMPT})
    history.append({"role": "user", "content": user_text})
    trim_history(history, keep_from=1)

    for _ in range(config.MAX_TOOL_ROUNDS):
        resp = _client.chat(
            model=config.OLLAMA_MODEL,
            messages=history,
            tools=_TOOLS,
            options={"num_ctx": config.OLLAMA_CONTEXT},
        )
        msg = _get(resp, "message")
        content = (_get(msg, "content") or "").strip()
        tool_calls = _get(msg, "tool_calls") or []

        if not tool_calls:
            history.append({"role": "assistant", "content": content})
            return content

        # Keep the tool calls on the assistant turn, then answer each one.
        calls, results = [], []
        for call in tool_calls:
            fn = _get(call, "function")
            name = _get(fn, "name")
            args = _get(fn, "arguments") or {}
            if isinstance(args, str):            # some models send JSON text
                try:
                    args = json.loads(args)
                except ValueError:
                    args = {}
            calls.append({"function": {"name": name, "arguments": args}})
            print(f"[tool] {name}({args})")
            results.append({"role": "tool", "tool_name": name, "content": run_tool(name, args)})
        history.append({"role": "assistant", "content": content, "tool_calls": calls})
        history.extend(results)

    return "Sorry, I got stuck trying to do that. Could you say it another way?"

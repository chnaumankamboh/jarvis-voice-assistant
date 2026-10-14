"""The agent brain: decides which tool to call, runs it, and writes the spoken reply.

Two interchangeable backends read the same tool definitions from tools.py:
  - brain_ollama.py  a local open model through Ollama (default, free, private)
  - brain_claude.py  Anthropic's API (faster, better at choosing tools, needs a key)
Pick one with BRAIN in config.py or the JARVIS_BRAIN environment variable.

The loop is the same in both:
  1. send the conversation + tool schemas to the model,
  2. if it asks for tools, run them and feed the results back,
  3. repeat (at most MAX_TOOL_ROUNDS times) until it returns a plain reply.
"""
import importlib

import config
from tools import TOOL_FNS

_BACKENDS = {"ollama": "brain_ollama", "claude": "brain_claude"}
_backend = None


def _load():
    """Import the configured backend once. Done lazily so the unused one's
    library (ollama or anthropic) doesn't have to be installed."""
    global _backend
    if _backend is None:
        name = _BACKENDS.get(config.BRAIN)
        if name is None:
            raise ValueError(f"Unknown BRAIN '{config.BRAIN}'. Use 'ollama' or 'claude'.")
        _backend = importlib.import_module(name)
    return _backend


def check():
    """Return None if the brain is ready, otherwise a short sentence saying what to fix."""
    try:
        return _load().check()
    except (ImportError, ValueError) as e:
        return str(e)


def describe():
    """Human-readable name of the active brain, for the startup banner."""
    return _load().describe()


def think(user_text, history):
    """Take one user utterance + the running history, return the reply to speak.
    `history` is a list owned by the caller; the backend appends to it in place."""
    return _load().think(user_text, history)


# ── helpers shared by both backends ─────────────────────────────────
def run_tool(name, args):
    """Call a tool by name. Errors become text so the model can explain them."""
    fn = TOOL_FNS.get(name)
    if fn is None:
        return f"Unknown tool: {name}"
    try:
        return str(fn(**(args or {})))
    except TypeError as e:
        return f"Tool '{name}' got the wrong arguments: {e}"
    except Exception as e:
        return f"Tool '{name}' failed: {e}"


def _is_user_text(msg):
    # A user message holding tool results must stay glued to the tool call before it,
    # so only a user message with plain text is a safe place to cut.
    return msg.get("role") == "user" and isinstance(msg.get("content"), str)


def trim_history(history, keep_from=0):
    """Drop the oldest turns once the history passes MAX_HISTORY_MESSAGES.

    Without this, a long session silently overflows the model's context and the
    model starts losing the oldest messages, which for Ollama is the system prompt.
    Messages before `keep_from` (the system prompt) are always kept.
    """
    body = len(history) - keep_from
    if body <= config.MAX_HISTORY_MESSAGES:
        return
    cut = keep_from + body - config.MAX_HISTORY_MESSAGES
    while cut < len(history) - 1 and not _is_user_text(history[cut]):
        cut += 1
    del history[keep_from:cut]

"""Cloud brain: Anthropic's Claude API. Fast and good at tool use; needs ANTHROPIC_API_KEY.

Setup once:
  - pip install anthropic
  - set ANTHROPIC_API_KEY (see config.py), then set BRAIN = "claude"
"""
import anthropic

import config
from brain import run_tool, trim_history
from tools import TOOL_SCHEMAS

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


def describe():
    return f"{config.CLAUDE_MODEL} via the Anthropic API"


def check():
    if not config.ANTHROPIC_API_KEY:
        return "No Anthropic API key is set. Set ANTHROPIC_API_KEY, or switch BRAIN back to ollama."
    return None


def think(user_text, history):
    history.append({"role": "user", "content": user_text})
    trim_history(history)

    for _ in range(config.MAX_TOOL_ROUNDS):
        resp = _get_client().messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=400,
            system=config.SYSTEM_PROMPT,
            tools=TOOL_SCHEMAS,
            messages=history,
        )
        history.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason != "tool_use":
            return "".join(b.text for b in resp.content if b.type == "text").strip()

        results = []
        for block in resp.content:
            if block.type == "tool_use":
                print(f"[tool] {block.name}({block.input})")
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": run_tool(block.name, block.input),
                })
        history.append({"role": "user", "content": results})

    return "Sorry, I got stuck trying to do that. Could you say it another way?"

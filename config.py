"""All the knobs in one place. Edit these, not the other files."""
import os
from pathlib import Path

# ── Which brain (LLM) to use ────────────────────────────────────────
# "ollama" = a local open model. Free, private, no API key (default).
# "claude" = Anthropic's API. Faster and better at picking tools; needs a key.
# You can also switch without editing:  set JARVIS_BRAIN=claude
BRAIN = os.environ.get("JARVIS_BRAIN", "ollama").strip().lower()

# ── Local brain (Ollama) ────────────────────────────────────────────
# Install from https://ollama.com , then:  ollama pull llama3.2:3b
# (or run:  python pull_model.py). The model must support tool calling;
# qwen2.5:7b is more reliable with tools if your machine can run it.
OLLAMA_MODEL = os.environ.get("JARVIS_OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "")   # blank = http://localhost:11434
OLLAMA_CONTEXT = 8192         # tokens of context; tool schemas + history must fit

# ── Cloud brain (Claude) ────────────────────────────────────────────
#   Windows:      setx ANTHROPIC_API_KEY "sk-ant-..."   (then reopen the terminal)
#   macOS/Linux:  export ANTHROPIC_API_KEY="sk-ant-..."
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
# Haiku answers fastest, which matters when every reply is spoken.
# Use "claude-sonnet-5-5" for harder multi-step requests.
CLAUDE_MODEL = os.environ.get("JARVIS_CLAUDE_MODEL", "claude-haiku-5-5")

# ── Agent loop limits ───────────────────────────────────────────────
MAX_TOOL_ROUNDS = 4           # tool calls allowed per request before giving up
MAX_HISTORY_MESSAGES = 24     # older turns are dropped so the prompt stays in context

# ── Speech-to-text (Whisper, runs locally) ──────────────────────────
# tiny.en (fastest) < base.en < small.en (most accurate). .en = English-only.
STT_MODEL = "base.en"
STT_DEVICE = "cpu"            # "cuda" if you have an NVIDIA GPU
STT_COMPUTE_TYPE = "int8"     # use "float16" when on GPU

# ── Microphone / recording ──────────────────────────────────────────
SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.01      # RMS below this = silence. Raise if a noisy room
                              # cuts you off; lower if it never stops listening.
SILENCE_DURATION = 1.2        # seconds of quiet that end an utterance
WAIT_FOR_SPEECH_SECONDS = 6   # give up if you haven't started talking by then
MAX_RECORD_SECONDS = 15       # hard cap on one utterance

# ── Voice output ────────────────────────────────────────────────────
SPEECH_RATE = 185             # words per minute; lower = slower

# ── Where to look for local media + files ───────────────────────────
HOME = Path.home()
MEDIA_DIRS = [HOME / "Music", HOME / "Videos", HOME / "Downloads"]
FILE_SEARCH_DIRS = [HOME / "Documents", HOME / "Desktop", HOME / "Downloads"]
SKIP_DIRS = {"node_modules", ".git", ".venv", "venv", "__pycache__", "AppData", "$RECYCLE.BIN"}
MAX_FILES_SCANNED = 50_000    # stop a search early on huge folders

# ── News (optional) ─────────────────────────────────────────────────
# Free key from https://newsapi.org . Leave unset to disable the news tool.
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY", "")

# ── Assistant persona ───────────────────────────────────────────────
ASSISTANT_NAME = "Jarvis"
SYSTEM_PROMPT = (
    f"You are {ASSISTANT_NAME}, a concise voice assistant running on the user's "
    "computer. You hear transcribed speech, and your replies are spoken aloud, so "
    "keep them short and natural: one or two sentences, no markdown, no lists. "
    "Use the available tools to actually perform actions (open sites, play media, "
    "search files, check the time, weather or news) instead of describing how to "
    "do them. Only call a tool when the request needs it; answer small talk "
    "directly. After a tool runs, give a brief spoken confirmation of what happened."
)

"""Download the Ollama model named in config.py through the Python client.

Use this if the `ollama` command isn't on your PATH but the Ollama app is
running. Run once:

    python pull_model.py
"""
import ollama

import config

MODEL = config.OLLAMA_MODEL

print(f"Pulling '{MODEL}' from the local Ollama server...")
last = None
try:
    for progress in ollama.pull(MODEL, stream=True):
        status = progress.get("status", "")
        total = progress.get("total")
        done = progress.get("completed")
        if total and done:
            pct = done / total * 100
            line = f"  {status}: {pct:5.1f}%  ({done // 1_000_000} / {total // 1_000_000} MB)"
        else:
            line = f"  {status}"
        if line != last:
            print(line)
            last = line
    print("\nDone. Now run:  python main.py")
except Exception as e:
    print(f"\nCouldn't pull the model: {e}")
    print("Make sure the Ollama app is running (check your system tray).")

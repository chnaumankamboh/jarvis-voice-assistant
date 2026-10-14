"""Jarvis: a minimal voice assistant.

    python main.py          press Enter and speak (or type a command, then Enter)
    python main.py --text   keyboard only: no microphone, replies are printed

This file stays small: it wires listen -> brain -> speak. Ctrl+C to quit.
"""
import argparse
import sys

import brain
import config
import speak

EXIT_PHRASES = {"quit", "exit", "goodbye", "bye", "stop listening"}


def explain(error):
    """Turn an exception into something worth saying out loud."""
    text = f"{type(error).__name__} {error}".lower()
    if "portaudio" in text or "input device" in text:
        return "I can't use the microphone. Check it's connected, or type your command instead."
    if "connect" in text or "refused" in text:
        return "I lost my connection to the brain. If you're using Ollama, check it's still running."
    if "authentication" in text or "api key" in text or "401" in text:
        return "The Anthropic API key was rejected. Check ANTHROPIC_API_KEY."
    return "Sorry, something went wrong. The details are in the console."


def main():
    parser = argparse.ArgumentParser(description=f"{config.ASSISTANT_NAME} voice assistant")
    parser.add_argument("--text", action="store_true", help="type commands; replies are printed, not spoken")
    args = parser.parse_args()
    sys.stdout.reconfigure(errors="replace")   # news titles can hold characters the console can't show
    speak.muted = args.text

    problem = brain.check()
    if problem:
        speak.say(problem)
        sys.exit(1)

    listen = None
    if not args.text:
        try:
            from listen import listen       # mic + Whisper are only loaded in voice mode
        except Exception as e:
            print(f"[listen] voice input unavailable ({e}); you can still type.")

    print(f"[brain] {brain.describe()}")
    speak.say(f"{config.ASSISTANT_NAME} online." + (" Press Enter, then speak." if listen else ""))
    history = []   # the whole conversation, kept for this session

    while True:
        try:
            prompt = "[press Enter and speak, or type] > " if listen else "[type a command] > "
            text = input("\n" + prompt).strip()
            if not text and listen:
                print("[listening...]")
                text = listen()
                if text:
                    print(f"[you] {text}")
            if not text:
                print("[heard nothing]")
                continue

            if text.lower().strip(" .!?,") in EXIT_PHRASES:
                speak.say("Goodbye.")
                break

            speak.say(brain.think(text, history) or "Done.")

        except (KeyboardInterrupt, EOFError):
            print("\n[shutting down]")
            break
        except Exception as e:
            print(f"[error] {type(e).__name__}: {e}")
            speak.say(explain(e))


if __name__ == "__main__":
    main()

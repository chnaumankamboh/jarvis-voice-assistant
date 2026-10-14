"""Text-to-speech. Uses pyttsx3: fully offline, works on Windows/macOS/Linux.

IMPORTANT: a fresh engine is created for every utterance. Reusing one global
engine makes pyttsx3 speak only the first time on Windows (its run loop
ends after the first runAndWait and won't restart on the same object).

Upgrade paths when you want it to sound less robotic:
  - Piper (local, fast, much nicer voices)
  - ElevenLabs (API, near-human, costs money)
Both just replace the body of say() below.
"""
import config

muted = False   # main.py sets this in --text mode: replies are printed, not spoken


def say(text):
    if not text:
        return
    print(f"[{config.ASSISTANT_NAME}] {text}")
    if muted:
        return
    try:
        import pyttsx3
        engine = pyttsx3.init()              # fresh engine each call
        engine.setProperty("rate", config.SPEECH_RATE)
        engine.say(text)
        engine.runAndWait()
        engine.stop()
    except Exception as e:
        print(f"[speak] TTS failed: {e}")

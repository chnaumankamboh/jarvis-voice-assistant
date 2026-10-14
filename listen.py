"""Microphone capture + speech-to-text using faster-whisper."""
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

import config

_model = None
BLOCK_SECONDS = 0.1   # audio is processed in 100 ms blocks
PRE_ROLL_BLOCKS = 3   # keep 300 ms before speech starts so the first word isn't clipped


def _get_model():
    """Load Whisper once, lazily (the first call is slow; later ones are fast)."""
    global _model
    if _model is None:
        print(f"[listen] loading Whisper '{config.STT_MODEL}' (first run downloads it)...")
        _model = WhisperModel(
            config.STT_MODEL,
            device=config.STT_DEVICE,
            compute_type=config.STT_COMPUTE_TYPE,
        )
    return _model


def record_until_silence():
    """Record from the default mic and stop after a pause.

    Waits up to WAIT_FOR_SPEECH_SECONDS for speech to start. If nobody speaks,
    returns an empty array instead of a long silent clip, because Whisper tends
    to "hear" phrases like "Thank you." in silence.
    """
    sr = config.SAMPLE_RATE
    block = int(sr * BLOCK_SECONDS)
    silence_blocks_needed = int(config.SILENCE_DURATION / BLOCK_SECONDS)
    wait_blocks = int(config.WAIT_FOR_SPEECH_SECONDS / BLOCK_SECONDS)
    max_blocks = int(config.MAX_RECORD_SECONDS / BLOCK_SECONDS)

    pre_roll, frames = [], []
    silent_run = 0
    speech_started = False

    with sd.InputStream(samplerate=sr, channels=1, dtype="float32", blocksize=block) as stream:
        for i in range(max_blocks):
            data, _overflow = stream.read(block)
            chunk = data[:, 0].copy()
            loud = float(np.sqrt(np.mean(chunk ** 2))) >= config.SILENCE_THRESHOLD

            if not speech_started:
                if loud:
                    speech_started = True
                    frames.extend(pre_roll)
                    frames.append(chunk)
                else:
                    pre_roll = (pre_roll + [chunk])[-PRE_ROLL_BLOCKS:]
                    if i >= wait_blocks:
                        break
                continue

            frames.append(chunk)
            silent_run = 0 if loud else silent_run + 1
            if silent_run >= silence_blocks_needed:
                break

    return np.concatenate(frames) if frames else np.zeros(0, dtype="float32")


def transcribe(audio):
    """Turn an audio array into text."""
    if audio.size == 0:
        return ""
    model = _get_model()
    # vad_filter drops non-speech audio before decoding, which cuts most hallucinations.
    segments, _info = model.transcribe(audio, language="en", vad_filter=True)
    return " ".join(seg.text for seg in segments).strip()


def listen():
    """Record one utterance and return its transcript ("" if nothing was said)."""
    return transcribe(record_until_silence())

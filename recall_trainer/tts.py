"""Volcengine TTS (Text-to-Speech) client.

Converts text to speech audio using the Volcengine TTS API.
Returns base64-encoded audio data that the frontend can play.

TTS failures must never block the text flow.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_TTS_URL = "https://openspeech.bytedance.com/api/v1/tts"


def is_tts_configured() -> bool:
    """Return True when the Volcengine TTS API key is available."""
    return bool(os.getenv("VOLCENGINE_API_KEY", ""))


def synthesize_speech(text: str, voice: str = "zh_female_01") -> dict[str, Any] | None:
    """Convert text to speech audio.

    Returns a dict with ``audio_base64`` and ``format`` keys,
    or None if TTS fails (never raises).
    """
    api_key = os.getenv("VOLCENGINE_API_KEY", "")
    if not api_key:
        return None

    tts_url = os.getenv("VOLCENGINE_TTS_URL", _DEFAULT_TTS_URL)

    payload = {
        "text": text,
        "voice": voice,
        "format": "mp3",
        "sample_rate": 24000,
    }

    try:
        request = urllib.request.Request(
            tts_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer;{api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        audio_data = data.get("audio") or data.get("data", "")
        if not audio_data:
            logger.warning("TTS returned no audio data")
            return None

        return {
            "audio_base64": audio_data,
            "format": "mp3",
        }
    except Exception as exc:
        logger.warning("TTS synthesis failed (non-fatal): %s", exc)
        return None

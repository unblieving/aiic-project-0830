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
import uuid
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_TTS_URL = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"
_DEFAULT_TTS_RESOURCE_ID = "Speech_Synthesis2000000933495388706"
_DEFAULT_TTS_VOICE_TYPE = "BV001_streaming"


def is_tts_configured() -> bool:
    """Return True when the Volcengine TTS API key is available."""
    return bool(os.getenv("VOLCENGINE_API_KEY", ""))


def synthesize_speech(text: str, voice: str = "zh_female_01") -> dict[str, Any]:
    """Convert text to speech audio.

    Returns a dict with ``audio_base64`` and ``format`` keys on success,
    or a dict with ``error`` / ``upstream_status`` / ``upstream_message``
    on failure (never raises, never returns None).
    """
    api_key = os.getenv("VOLCENGINE_API_KEY", "")
    if not api_key:
        return {"error": "VOLCENGINE_API_KEY not set"}

    tts_url = os.getenv("VOLCENGINE_TTS_URL", _DEFAULT_TTS_URL)
    resource_id = os.getenv("VOLCENGINE_TTS_RESOURCE_ID", _DEFAULT_TTS_RESOURCE_ID)
    voice_type = voice if voice != "zh_female_01" else os.getenv("VOLCENGINE_TTS_VOICE_TYPE", _DEFAULT_TTS_VOICE_TYPE)

    payload = {
        "user": {"uid": os.getenv("VOLCENGINE_TTS_UID", "recall-trainer")},
        "req_params": {
            "text": text,
            "speaker": voice_type,
            "audio_params": {
                "format": "mp3",
                "sample_rate": 24000,
            },
        },
    }
    request_id = str(uuid.uuid4())

    try:
        request = urllib.request.Request(
            tts_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "X-Api-Key": api_key,
                "X-Api-Resource-Id": resource_id,
                "X-Api-Request-Id": request_id,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        if data.get("code") not in {None, 0}:
            return {
                "error": "TTS request failed",
                "upstream_status": 200,
                "upstream_message": json.dumps(data, ensure_ascii=False)[:1000],
            }

        audio_data = data.get("audio") or data.get("data", "")
        if not audio_data:
            logger.warning("TTS returned no audio data, keys=%s", list(data.keys()))
            return {
                "error": "TTS returned no audio",
                "upstream_status": 200,
                "upstream_message": f"response keys: {list(data.keys())}",
            }

        return {
            "audio_base64": audio_data,
            "format": "mp3",
        }

    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        logger.error("[TTS] upstream status=%s", exc.code)
        logger.error("[TTS] response=%s", body)
        return {
            "error": "TTS request failed",
            "upstream_status": exc.code,
            "upstream_message": body[:1000],
        }
    except urllib.error.URLError as exc:
        logger.error("[TTS] connection error: %s", exc.reason)
        return {
            "error": "TTS connection failed",
            "upstream_message": str(exc.reason),
        }
    except Exception as exc:
        logger.error("[TTS] unexpected error: %s", exc)
        return {
            "error": "TTS unexpected error",
            "upstream_message": str(exc),
        }

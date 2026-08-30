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

_DEFAULT_TTS_URL = "https://openspeech.bytedance.com/api/v1/tts"
_DEFAULT_TTS_CLUSTER = "volcano_tts"
_DEFAULT_TTS_VOICE_TYPE = "BV001_streaming"


def is_tts_configured() -> bool:
    """Return True when the Volcengine TTS API key is available."""
    return bool(os.getenv("VOLCENGINE_API_KEY", "") and os.getenv("VOLCENGINE_TTS_APP_ID", ""))


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
    app_id = os.getenv("VOLCENGINE_TTS_APP_ID", "")
    access_token = os.getenv("VOLCENGINE_TTS_ACCESS_TOKEN", "")
    cluster = os.getenv("VOLCENGINE_TTS_CLUSTER", _DEFAULT_TTS_CLUSTER)
    voice_type = voice if voice != "zh_female_01" else os.getenv("VOLCENGINE_TTS_VOICE_TYPE", _DEFAULT_TTS_VOICE_TYPE)

    if not app_id:
        return {
            "error": "VOLCENGINE_TTS_APP_ID not set",
            "upstream_message": "Volcengine TTS v1 requires app.appid.",
        }
    if not access_token:
        return {
            "error": "VOLCENGINE_TTS_ACCESS_TOKEN not set",
            "upstream_message": "Volcengine TTS v1 requires app.token. Do not reuse the new console API key here unless Volcengine documents it for this instance.",
        }

    payload = {
        "app": {
            "appid": app_id,
            "token": access_token,
            "cluster": cluster,
        },
        "user": {
            "uid": os.getenv("VOLCENGINE_TTS_UID", "recall-trainer"),
        },
        "audio": {
            "voice_type": voice_type,
            "encoding": "mp3",
            "rate": 24000,
        },
        "request": {
            "reqid": str(uuid.uuid4()),
            "text": text,
            "operation": "query",
        },
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

        if data.get("code") not in {None, 3000}:
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

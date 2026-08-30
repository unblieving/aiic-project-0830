from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
import uuid
from typing import Any


_DEFAULT_ENDPOINT = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash"
_DEFAULT_RESOURCE_ID = "volc.onesentenceasr.common.cn"


def is_asr_configured() -> bool:
    return bool(os.getenv("VOLCENGINE_API_KEY", "").strip())


def recognize_audio(audio_bytes: bytes, content_type: str) -> str:
    return OneSentenceASRClient().recognize(audio_bytes, content_type)


class OneSentenceASRClient:
    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
        resource_id: str | None = None,
        timeout_seconds: int = 20,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("VOLCENGINE_API_KEY", "").strip()
        self.endpoint = endpoint or os.getenv("VOLCENGINE_ASR_ENDPOINT", _DEFAULT_ENDPOINT)
        self.resource_id = resource_id or os.getenv("VOLCENGINE_ASR_RESOURCE_ID", _DEFAULT_RESOURCE_ID)
        self.timeout_seconds = timeout_seconds

    def recognize(self, audio_bytes: bytes, content_type: str) -> str:
        if not self.api_key:
            raise RuntimeError("VOLCENGINE_API_KEY not set")
        if not audio_bytes:
            raise ValueError("empty audio body")

        print("[ASR VOLC] start")
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(self._payload(audio_bytes, content_type)).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Api-Key": self.api_key,
                "X-Api-Resource-Id": self.resource_id,
                "X-Api-Request-Id": str(uuid.uuid4()),
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            print(f"[ASR VOLC] failed type=HTTPError status={exc.code}")
            print(f"[ASR VOLC] failed message={body}")
            raise RuntimeError(f"Volcengine ASR HTTP {exc.code}: {body}") from exc
        except Exception as exc:
            print(f"[ASR VOLC] failed type={type(exc).__name__}")
            print(f"[ASR VOLC] failed message={exc}")
            raise

        data = json.loads(raw)
        transcript = _extract_transcript(data)
        print(f"[ASR VOLC] success transcript_chars={len(transcript)}")
        return transcript

    def _payload(self, audio_bytes: bytes, content_type: str) -> dict[str, Any]:
        return {
            "user": {"uid": "recall-trainer-demo"},
            "audio": {
                "data": base64.b64encode(audio_bytes).decode("ascii"),
                "format": _audio_format(content_type),
            },
            "request": {"model_name": "bigmodel"},
        }


def _audio_format(content_type: str) -> str:
    normalized = (content_type or "").split(";")[0].strip().lower()
    if normalized == "audio/wav":
        return "wav"
    if normalized in {"audio/mp3", "audio/mpeg"}:
        return "mp3"
    if normalized == "audio/ogg":
        return "ogg"
    return "webm"


def _extract_transcript(data: dict[str, Any]) -> str:
    candidates = [
        data.get("text"),
        data.get("transcript"),
        data.get("result", {}).get("text") if isinstance(data.get("result"), dict) else None,
        data.get("result", {}).get("transcript") if isinstance(data.get("result"), dict) else None,
    ]
    for candidate in candidates:
        if isinstance(candidate, str):
            return candidate.strip()
    result = data.get("result")
    if isinstance(result, list):
        texts = [item.get("text", "") for item in result if isinstance(item, dict)]
        return " ".join(text.strip() for text in texts if text.strip()).strip()
    return ""

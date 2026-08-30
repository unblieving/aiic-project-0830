"""Volcengine streaming ASR WebSocket client.

Connects to the Volcengine speech recognition streaming service,
sends audio chunks, and receives partial / final transcripts.

The exact WebSocket endpoint, authentication method, and message
schema are configurable via environment variables so that the
client can be adapted to the real Volcengine API without code
changes.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_ENDPOINT = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel"
_DEFAULT_CLUSTER = "volcengine_streaming"


def is_asr_configured() -> bool:
    """Return True when the Volcengine ASR API key is available."""
    return bool(os.getenv("VOLCENGINE_API_KEY", ""))


def get_ws_port() -> int:
    """Return the WebSocket proxy port."""


class VolcengineASRClient:
    """Async client for Volcengine streaming ASR over WebSocket."""

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
        cluster: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("VOLCENGINE_API_KEY", "")
        self.endpoint = endpoint or os.getenv("VOLCENGINE_ASR_ENDPOINT", _DEFAULT_ENDPOINT)
        self.cluster = cluster or os.getenv("VOLCENGINE_ASR_CLUSTER", _DEFAULT_CLUSTER)
        self._ws: Any = None
        self._request_id: str = ""

    async def connect(self) -> None:
        """Open WebSocket connection to Volcengine ASR service."""
        try:
            import websockets
        except ImportError as exc:
            raise RuntimeError(
                "The 'websockets' package is required for voice features. "
                "Install it with: pip install websockets"
            ) from exc
        headers = {"Authorization": f"Bearer;{self.api_key}"}
        self._ws = await websockets.connect(
            self.endpoint,
            additional_headers=headers,
            max_size=2**24,
            ping_interval=30,
            ping_timeout=10,
            close_timeout=5,
        )
        logger.info("Connected to Volcengine ASR: %s", self.endpoint)

    async def close(self) -> None:
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None

    async def send_start(self) -> None:
        """Send the initial configuration message."""
        import uuid
        self._request_id = str(uuid.uuid4())
        msg = {
            "uid": "recall_trainer_user",
            "format": "pcm",
            "rate": 16000,
            "bits": 16,
            "channel": 1,
            "codec": "raw",
            "req_mode": "bigmodel",
            "cluster": self.cluster,
            "request_id": self._request_id,
            "nbest": 1,
        }
        await self._ws.send(json.dumps(msg))

    async def send_audio(self, pcm_data: bytes) -> None:
        """Send a chunk of PCM audio data (base64-encoded)."""
        encoded = base64.b64encode(pcm_data).decode("ascii")
        msg = {"audio": encoded}
        await self._ws.send(json.dumps(msg))

    async def finalize(self) -> None:
        """Signal end of audio stream."""
        msg = {"audio": ""}
        await self._ws.send(json.dumps(msg))

    async def receive_result(self, timeout: float = 30.0) -> dict[str, Any]:
        """Wait for and return the next recognition result."""
        raw_text = await asyncio.wait_for(self._ws.recv(), timeout=timeout)
        raw = json.loads(raw_text)
        return self._parse_result(raw)

    @staticmethod
    def _parse_result(raw: dict[str, Any]) -> dict[str, Any]:
        """Parse a Volcengine ASR response into a normalised dict."""
        text = ""
        is_final = False
        if "result" in raw:
            result = raw["result"]
            if isinstance(result, str):
                text = result
            elif isinstance(result, dict):
                text = result.get("text", "")
        elif "text" in raw:
            text = raw["text"]
        if raw.get("is_final") or raw.get("is_last_package"):
            is_final = True
        if raw.get("sequence") == -1:
            is_final = True
        code = raw.get("code", 0)
        if code != 0:
            logger.warning("ASR error: code=%s msg=%s", code, raw.get("message", ""))
        return {"text": text, "is_final": is_final, "raw": raw}

    return int(os.getenv("WS_PORT", "8082"))

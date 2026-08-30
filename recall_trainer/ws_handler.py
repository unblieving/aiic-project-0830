"""WebSocket handler for ASR proxy between browser and Volcengine.

Runs a separate WebSocket server on a configurable port.
The browser connects here; we forward audio to Volcengine
and stream transcripts back.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import threading
from typing import Any

from recall_trainer.volcengine_asr import VolcengineASRClient, is_asr_configured

logger = logging.getLogger(__name__)


def start_ws_server(port: int) -> threading.Thread | None:
    """Start the WebSocket server in a background thread.

    Returns the thread object, or None if websockets is not
    installed or ASR is not configured.
    """
    if not is_asr_configured():
        logger.info("Volcengine ASR not configured; WebSocket server skipped.")
        return None

    try:
        import websockets  # noqa: F401
    except ImportError:
        logger.warning(
            "websockets package not installed; voice features disabled. "
            "Install with: pip install websockets"
        )
        return None

    def _run() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_serve(port))

    thread = threading.Thread(target=_run, daemon=True, name="ws-asr")
    thread.start()
    logger.info("WebSocket ASR server starting on port %d", port)
    return thread


async def _serve(port: int) -> None:
    import websockets

    async with websockets.serve(_handle_connection, "0.0.0.0", port):
        await asyncio.Future()  # run forever


async def _handle_connection(ws: Any) -> None:
    """Handle one browser WebSocket connection for ASR streaming."""
    asr_client: VolcengineASRClient | None = None
    try:
        async for raw_message in ws:
            try:
                msg = json.loads(raw_message)
            except json.JSONDecodeError:
                await ws.send(json.dumps({"type": "error", "message": "Invalid JSON"}))
                continue

            msg_type = msg.get("type", "")

            if msg_type == "start":
                asr_client = await _start_asr(ws)
                if asr_client is None:
                    return

            elif msg_type == "audio":
                if asr_client is None:
                    await ws.send(json.dumps({
                        "type": "error",
                        "message": "ASR session not started. Send 'start' first.",
                    }))
                    continue
                await _forward_audio(ws, asr_client, msg)

            elif msg_type == "stop":
                if asr_client:
                    await _finalize_asr(ws, asr_client)
                    asr_client = None

            else:
                await ws.send(json.dumps({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}",
                }))

    except Exception as exc:
        logger.error("WebSocket handler error: %s", exc)
        try:
            await ws.send(json.dumps({"type": "error", "message": str(exc)}))
        except Exception:
            pass
    finally:
        if asr_client:
            await asr_client.close()


async def _start_asr(ws: Any) -> VolcengineASRClient | None:
    """Connect to Volcengine ASR and send the start message."""
    client = VolcengineASRClient()
    try:
        await client.connect()
        await client.send_start()
        await ws.send(json.dumps({"type": "started"}))
        # Start a background task to forward ASR results back to browser
        asyncio.create_task(_forward_results(ws, client))
        return client
    except Exception as exc:
        logger.error("Failed to connect to Volcengine ASR: %s", exc)
        await ws.send(json.dumps({
            "type": "error",
            "message": f"ASR service unavailable: {exc}",
        }))
        await client.close()
        return None


async def _forward_audio(ws: Any, asr: VolcengineASRClient, msg: dict) -> None:
    """Forward a base64 audio chunk from browser to Volcengine."""
    audio_b64 = msg.get("audio", "")
    if audio_b64:
        try:
            pcm_data = base64.b64decode(audio_b64)
            await asr.send_audio(pcm_data)
        except Exception as exc:
            logger.error("Error forwarding audio: %s", exc)
            await ws.send(json.dumps({"type": "error", "message": f"Audio forward error: {exc}"}))


async def _forward_results(ws: Any, asr: VolcengineASRClient) -> None:
    """Continuously read ASR results and send to browser."""
    try:
        while True:
            try:
                result = await asr.receive_result(timeout=60.0)
            except asyncio.TimeoutError:
                continue
            except Exception as exc:
                logger.error("ASR receive error: %s", exc)
                await ws.send(json.dumps({"type": "error", "message": f"ASR result error: {exc}"}))
                break

            await ws.send(json.dumps({
                "type": "transcript",
                "text": result["text"],
                "isFinal": result["is_final"],
            }))

            if result["is_final"]:
                break
    except Exception as exc:
        logger.error("Forward results error: %s", exc)


async def _finalize_asr(ws: Any, asr: VolcengineASRClient) -> None:
    """Send finalize to Volcengine and wait for the last result."""
    try:
        await asr.finalize()
        # The _forward_results task will send the final transcript
    except Exception as exc:
        logger.error("Finalize error: %s", exc)
        await ws.send(json.dumps({"type": "error", "message": f"Finalize error: {exc}"}))
    finally:
        await asr.close()

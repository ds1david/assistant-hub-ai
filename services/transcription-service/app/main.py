from __future__ import annotations

import asyncio
import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from .broadcast import TranscriptBroadcaster
from .config import Settings, get_settings
from .echo_suppression import TranscriptEchoSuppressor
from .engine import TranscriptionEngine
from .metrics import LatencyMetricsRegistry
from .transcriber import StreamingTranscriber, WhisperEngine, transcribe_file

LOGGER = logging.getLogger(__name__)
STATIC_INDEX = Path(__file__).with_name("static") / "index.html"


def create_app(
    settings: Settings | None = None,
    engine: TranscriptionEngine | None = None,
    metrics_registry: LatencyMetricsRegistry | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    engine = engine or WhisperEngine(settings)
    metrics = metrics_registry or LatencyMetricsRegistry(
        max_samples_per_channel=settings.metrics_max_samples_per_channel,
        max_channels=settings.metrics_max_channels,
    )
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))

    broadcaster = TranscriptBroadcaster()
    echo_suppressor = TranscriptEchoSuppressor(
        enabled=settings.echo_suppression_enabled,
        window_seconds=settings.echo_suppression_window_seconds,
        similarity_threshold=settings.echo_suppression_similarity,
        min_chars=settings.echo_suppression_min_chars,
    )
    app = FastAPI(title="Assistant Hub AI Transcription Service", version="0.1.7")

    @app.get("/")
    async def dashboard() -> FileResponse:
        return FileResponse(STATIC_INDEX)

    @app.get("/health")
    async def health() -> dict:
        return {
            "status": "ok",
            "modelLoaded": engine.loaded,
            "model": settings.whisper_model,
            "device": settings.whisper_device,
            "language": settings.whisper_language,
            "sampleRate": settings.sample_rate,
            "beamSize": settings.whisper_beam_size,
            "hotwordsConfigured": bool(settings.resolved_hotwords()),
            "echoSuppressionEnabled": settings.echo_suppression_enabled,
        }

    @app.post("/v1/model/load")
    async def load_model() -> dict:
        started = asyncio.get_running_loop().time()
        await asyncio.to_thread(engine.load)
        return {
            "status": "loaded",
            "model": settings.whisper_model,
            "device": settings.whisper_device,
            "elapsedMs": int((asyncio.get_running_loop().time() - started) * 1000),
        }

    @app.websocket("/ws/transcripts")
    async def transcript_feed(websocket: WebSocket) -> None:
        await broadcaster.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            await broadcaster.disconnect(websocket)

    @app.websocket("/ws/audio/{session_id}/{channel_id}")
    async def audio_stream(websocket: WebSocket, session_id: str, channel_id: str) -> None:
        source_type = websocket.query_params.get("sourceType", "unknown")
        device_name = websocket.query_params.get("deviceName")
        device_index_raw = websocket.query_params.get("deviceIndex")
        label = websocket.query_params.get("label") or channel_id
        if source_type not in {"system", "microphone"}:
            await websocket.close(code=1008, reason="sourceType must be system or microphone")
            return
        try:
            device_index = int(device_index_raw) if device_index_raw is not None else None
        except ValueError:
            await websocket.close(code=1008, reason="deviceIndex must be an integer")
            return

        await websocket.accept()
        transcriber = StreamingTranscriber(settings, engine)
        windows: asyncio.Queue[tuple[bytes, bool] | None] = asyncio.Queue(maxsize=2)
        dropped_windows = 0
        LOGGER.info(
            "Audio channel connected session=%s channel=%s source_type=%s device=(%s) %s",
            session_id,
            channel_id,
            source_type,
            device_index,
            device_name,
        )

        async def emit(window: bytes, final: bool = False) -> None:
            result = await asyncio.to_thread(transcriber.transcribe_pcm, window)
            if result is None:
                return
            if source_type == "microphone" and settings.echo_suppression_enabled:
                # Let the cleaner system-audio channel finish first so a physically
                # echoed microphone transcript can be recognized as a duplicate.
                await asyncio.sleep(settings.echo_suppression_mic_delay_ms / 1000.0)

            echo = echo_suppressor.evaluate(
                session_id=session_id,
                source_type=source_type,
                text=result.text,
            )
            if echo.suppressed:
                LOGGER.info(
                    "Suppressed microphone echo session=%s channel=%s similarity=%.3f text=%r matched=%r",
                    session_id,
                    channel_id,
                    echo.similarity,
                    result.text,
                    echo.matched_text,
                )
                return

            event = {
                "type": "transcript.final.v2" if final else "transcript.partial.v2",
                "sessionId": session_id,
                "channelId": channel_id,
                "label": label,
                "sourceType": source_type,
                "device": {
                    "index": device_index,
                    "name": device_name,
                },
                "text": result.text,
                "language": result.language,
                "languageProbability": result.language_probability,
                "latencyMs": result.latency_ms,
                "audioSeconds": result.audio_seconds,
                "droppedWindows": dropped_windows,
                "occurredAt": datetime.now(timezone.utc).isoformat(),
            }
            await websocket.send_json(event)
            await broadcaster.publish(event)
            # Ponto único de registro: uma amostra por evento entregue. O
            # fan-out do broadcaster repete o mesmo evento por cliente e não
            # deve contar.
            metrics.record_transcription(
                session_id=session_id,
                channel_id=channel_id,
                source_type=source_type,
                label=label,
                latency_ms=result.latency_ms,
            )

        async def worker() -> None:
            while True:
                item = await windows.get()
                try:
                    if item is None:
                        return
                    window, final = item
                    await emit(window, final)
                finally:
                    windows.task_done()

        worker_task = asyncio.create_task(worker())

        def enqueue_latest(window: bytes, final: bool = False) -> None:
            nonlocal dropped_windows
            if windows.full():
                try:
                    windows.get_nowait()
                    windows.task_done()
                    dropped_windows += 1
                    metrics.record_dropped_window(
                        session_id=session_id, channel_id=channel_id
                    )
                except asyncio.QueueEmpty:
                    pass
            windows.put_nowait((window, final))

        try:
            while True:
                message = await websocket.receive()
                if data := message.get("bytes"):
                    window = transcriber.append(data)
                    if window is not None:
                        enqueue_latest(window)
                elif message.get("type") == "websocket.disconnect":
                    break
        except WebSocketDisconnect:
            pass
        finally:
            remaining = transcriber.flush()
            if remaining is not None:
                enqueue_latest(remaining, final=True)
            await windows.join()
            await windows.put(None)
            await worker_task
            LOGGER.info(
                "Audio channel disconnected session=%s channel=%s dropped_windows=%s",
                session_id,
                channel_id,
                dropped_windows,
            )

    @app.get("/v1/sessions/{session_id}/metrics")
    async def session_metrics(session_id: str) -> dict:
        snapshot = metrics.session_snapshot(session_id)
        return {
            "sessionId": snapshot.session_id,
            "generatedAt": snapshot.generated_at.isoformat(),
            "maxSamplesPerChannel": metrics.max_samples_per_channel,
            "channels": [
                {
                    "channelId": channel.channel_id,
                    "sourceType": channel.source_type,
                    "label": channel.label,
                    "sampleCount": channel.sample_count,
                    "p50Ms": channel.p50_ms,
                    "p95Ms": channel.p95_ms,
                    "minMs": channel.min_ms,
                    "maxMs": channel.max_ms,
                    "avgMs": channel.avg_ms,
                    "totalEvents": channel.total_events,
                    "droppedWindows": channel.dropped_windows,
                    "lastEventAt": (
                        channel.last_event_at.isoformat() if channel.last_event_at else None
                    ),
                }
                for channel in snapshot.channels
            ],
        }

    @app.post("/v1/transcribe-file")
    async def transcribe_uploaded_file(
        file: UploadFile = File(...),
        language: str | None = Query(default=None),
    ) -> dict:
        suffix = Path(file.filename or "audio.wav").suffix or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp:
            temp_path = Path(temp.name)
            while chunk := await file.read(1024 * 1024):
                temp.write(chunk)

        try:
            return await asyncio.to_thread(transcribe_file, temp_path, engine, language)
        finally:
            temp_path.unlink(missing_ok=True)

    return app


app = create_app()

import asyncio
import base64
import hashlib
import json
import os
import re
import uuid
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from websockets.exceptions import ConnectionClosed, WebSocketException
from websockets.asyncio.client import connect as websocket_connect

from backend.dialogue import (
    NODES,
    adjust_item,
    cancel_review,
    clear_order,
    confirm_order,
    initial_state,
    localized_line,
    process_turn,
    review_order,
    scene_view,
)
from backend.menu import ITEM_ALIASES, MENU, menu_payload


load_dotenv(Path(__file__).resolve().parent.parent / ".env")

app = FastAPI(title="Multilingual Ordering Kiosk API", version="0.1.0")
DEFAULT_FRONTEND_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://0.0.0.0:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://0.0.0.0:5174",
]
configured_origins = os.getenv("FRONTEND_ORIGINS")
if configured_origins:
    allowed_origins = [origin.strip() for origin in configured_origins.split(",") if origin.strip()]
else:
    allowed_origins = DEFAULT_FRONTEND_ORIGINS
allowed_origins = list(dict.fromkeys(allowed_origins))
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSIONS: dict[str, dict] = {}
TURN_RESULTS: dict[str, dict[str, dict]] = {}
VOICE_LINES = {key: lines[0] for key, lines in NODES.items()}
VOICE_CACHE = Path(os.getenv("VOICE_CACHE_DIR", "backend/.cache/voice"))


def prisma_stream_headers(language: str = "kn") -> dict[str, str]:
    api_key = os.getenv("GNANI_API_KEY")
    if not api_key:
        raise ValueError("Microphone transcription needs GNANI_API_KEY.")

    model = os.getenv("GNANI_STT_MODEL", "prisma-v3.0")
    headers = {
        "x-api-key-id": api_key,
        "model": model,
        "language_code": (
            "indic-auto"
            if model == "prisma-v3.0"
            else {"kn": "kn-IN", "ta": "ta-IN", "te": "te-IN"}.get(language, "kn-IN")
        ),
        "x-sample-rate": "16000",
        "format": "transcribe",
        "x-vad-threshold": "0.5",
        "x-min-silence-ms": "600",
        "x-min-speech-ms": "80",
        "x-idle-timeout-sec": "90",
    }
    if model == "prisma-v3.0":
        headers["keyterms"] = json.dumps(
            list(dict.fromkeys(
                alias
                for item in MENU
                for alias in ITEM_ALIASES[item["key"]]
            )),
            ensure_ascii=True,
        )
        headers["topic"] = (
            "A customer ordering, changing, or removing food and drinks at a Bengaluru darshini. "
            "The customer may speak Kannada, Tamil, Telugu, English, or mix these languages, "
            "and may mention quantities."
        )
    return headers


def public_session(session_id: str, state: dict) -> dict:
    return {
        "session_id": session_id,
        **state,
        "scene": scene_view(state),
        "menu": menu_payload(state.get("language", "kn")),
        "line": localized_line("greeting", state.get("language", "kn"))[0],
        "line_english": localized_line("greeting", state.get("language", "kn"))[1],
        "line_key": "greeting",
        "speech_enabled": bool(os.getenv("GNANI_API_KEY")),
        "voice_enabled": bool(os.getenv("GNANI_API_KEY")),
    }


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "speech_enabled": bool(os.getenv("GNANI_API_KEY")),
    }


@app.post("/api/session")
def create_session(scene_key: str = "order", language: str = "kn") -> dict:
    if scene_key != "order":
        raise HTTPException(status_code=404, detail="Unknown ordering session.")
    session_id = str(uuid.uuid4())
    try:
        state = initial_state(scene_key, language)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    SESSIONS[session_id] = state
    TURN_RESULTS[session_id] = {}
    return public_session(session_id, state)


async def synthesize_voice(line_key: str, language: str = "kn") -> bytes:
    api_key = os.getenv("GNANI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Gnani Timbre voice requires GNANI_API_KEY. The dialogue text remains available.",
        )
    if line_key not in VOICE_LINES:
        raise HTTPException(status_code=404, detail="Unknown character line.")
    if language not in {"kn", "ta", "te"}:
        raise HTTPException(status_code=422, detail="Choose Kannada, Tamil, or Telugu.")

    safe_model = os.getenv("GNANI_TTS_MODEL", "timbre-v2.5")
    language_code = {"kn": "kn-IN", "ta": "ta-IN", "te": "te-IN"}[language]
    text = localized_line(line_key, language)[0]
    if safe_model == "timbre-v3.0":
        safe_voice = "Shivani"
    else:
        safe_voice = {
            "kn": os.getenv("GNANI_TTS_VOICE", "Kavin"),
            "ta": "Noopur",
            "te": "Yukti",
        }[language]
    text_digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    cache_key = re.sub(
        r"[^a-zA-Z0-9_-]",
        "",
        f"{safe_model}-{safe_voice}-{language}-{line_key}-{text_digest}",
    )
    cache_path = VOICE_CACHE / f"{cache_key}.wav"
    if cache_path.is_file():
        return cache_path.read_bytes()

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "https://api.vachana.ai/api/v1/tts/inference",
            headers={"X-API-Key-ID": api_key, "Content-Type": "application/json"},
            json={
                "text": text,
                "voice": safe_voice,
                "model": safe_model,
                "language": language_code,
                "audio_config": {
                    "sample_rate": 24000,
                    "num_channels": 1,
                    "sample_width": 2,
                    "encoding": "linear_pcm",
                    "container": "wav",
                },
            },
        )
    if response.is_error:
        raise HTTPException(status_code=502, detail=f"Gnani voice synthesis failed ({response.status_code}).")
    content = response.content
    if response.headers.get("content-type", "").startswith("application/json"):
        try:
            payload = response.json()
            encoded = payload.get("audio") or payload.get("audio_base64")
            if not isinstance(encoded, str):
                raise ValueError
            content = base64.b64decode(encoded, validate=True)
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=502, detail="Gnani returned an unreadable voice response.") from exc
    if not content:
        raise HTTPException(status_code=502, detail="Gnani returned empty voice audio.")
    VOICE_CACHE.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(content)
    return content


@app.get("/api/voice/{line_key}")
async def voice(line_key: str, language: str = "kn") -> Response:
    audio = await synthesize_voice(line_key, language)
    return Response(content=audio, media_type="audio/wav", headers={"Cache-Control": "public, max-age=31536000"})


@app.websocket("/ws/session/{session_id}")
async def session_socket(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    if session_id not in SESSIONS:
        await websocket.send_json({"type": "error", "message": "Session not found. Start a new order."})
        await websocket.close(code=1008)
        return

    prisma = None
    reader_task = None
    active_audio_turn_id = None
    processed_turns = TURN_RESULTS.setdefault(session_id, {})
    transcript_segments: list[str] = []
    transcript_event = asyncio.Event()

    def cache_turn_result(turn_id: str | None, result: dict) -> None:
        if not turn_id:
            return
        processed_turns[turn_id] = result
        while len(processed_turns) > 100:
            processed_turns.pop(next(iter(processed_turns)))

    async def read_prisma() -> None:
        nonlocal prisma
        try:
            async for raw in prisma:
                try:
                    event = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    await websocket.send_json(
                        {"type": "error", "message": "Prisma returned an unreadable streaming message."}
                    )
                    continue

                if not isinstance(event, dict):
                    await websocket.send_json(
                        {"type": "error", "message": "Prisma returned an invalid streaming message."}
                    )
                    continue
                if event.get("type") == "transcript":
                    transcript_text = event.get("text")
                    text = transcript_text.strip() if isinstance(transcript_text, str) else ""
                    if text:
                        segment_id = event.get("segment_id")
                        if not segment_id or segment_id not in seen_segment_ids:
                            if segment_id:
                                seen_segment_ids.add(segment_id)
                            transcript_segments.append(text)
                        transcript_event.set()
                        await websocket.send_json(
                            {
                                "type": "live_transcript",
                                "text": " ".join(transcript_segments),
                                "detected_language_code": event.get("detected_language_code"),
                            }
                        )
                elif event.get("type") == "processing":
                    await websocket.send_json({"type": "stt_processing"})
                elif event.get("type") == "speech_start":
                    await websocket.send_json({"type": "speech_start"})
                elif event.get("type") == "error":
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": f"Prisma: {event.get('message', 'Streaming transcription failed.')}",
                        }
                    )
        except (ConnectionClosed, WebSocketException, OSError) as exc:
            if prisma is not None:
                await websocket.send_json(
                    {"type": "error", "message": f"Prisma streaming connection closed: {exc}"}
                )

    seen_segment_ids: set[str] = set()
    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break
            if message.get("bytes") is not None:
                frame = message["bytes"]
                if len(frame) != 1024:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "Microphone audio frame had the wrong size. Please refresh and try again.",
                        }
                    )
                    continue
                if prisma is None:
                    await websocket.send_json(
                        {"type": "error", "message": "Start the microphone before sending audio."}
                    )
                    continue
                try:
                    await prisma.send(frame)
                except (ConnectionClosed, WebSocketException, OSError) as exc:
                    await websocket.send_json(
                        {"type": "error", "message": f"Could not send microphone audio to Prisma: {exc}"}
                    )
                continue
            data = message.get("text")
            if data is None:
                continue

            try:
                event = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Could not read the message. Please try again."})
                continue
            if not isinstance(event, dict):
                await websocket.send_json({"type": "error", "message": "Message must be a JSON object."})
                continue

            event_type = event.get("type")
            turn_id = event.get("turn_id")
            if turn_id is not None and (
                not isinstance(turn_id, str)
                or not turn_id
                or len(turn_id) > 128
            ):
                await websocket.send_json({"type": "error", "message": "The voice turn identifier is invalid."})
                continue
            if event_type in ("transcript", "stop_audio") and turn_id in processed_turns:
                current_state = SESSIONS[session_id]
                await websocket.send_json(
                    {
                        **processed_turns[turn_id],
                        **current_state,
                        "order": dict(current_state.get("order", {})),
                        "scene": scene_view(current_state),
                        "menu": menu_payload(current_state.get("language", "kn")),
                        "replayed": True,
                    }
                )
                continue

            if event_type == "set_language":
                language = event.get("language")
                if language not in {"kn", "ta", "te"}:
                    await websocket.send_json(
                        {"type": "error", "message": "Choose Kannada, Tamil, or Telugu."}
                    )
                    continue
                if prisma is not None:
                    await websocket.send_json(
                        {"type": "error", "message": "Finish the current voice turn before changing language."}
                    )
                    continue
                state = {**SESSIONS[session_id], "language": language}
                SESSIONS[session_id] = state
                line_key = state.get("node", "greeting")
                line, line_english = localized_line(line_key, language)
                await websocket.send_json(
                    {
                        "type": "result",
                        **state,
                        "line": line,
                        "line_english": line_english,
                        "line_key": line_key,
                        "matched": True,
                        "order_updated": False,
                        "language_changed": True,
                        "scene": scene_view(state),
                        "menu": menu_payload(language),
                    }
                )
                continue
            if event_type == "start_audio":
                if prisma is not None:
                    await websocket.send_json(
                        {"type": "error", "message": "A microphone recording is already active."}
                    )
                    continue
                try:
                    prisma = await websocket_connect(
                        "wss://api.vachana.ai/stt/v3/stream",
                        additional_headers=prisma_stream_headers(
                            SESSIONS[session_id].get("language", "kn")
                        ),
                        open_timeout=15,
                        close_timeout=3,
                        max_size=1024 * 1024,
                    )
                    connected = json.loads(await asyncio.wait_for(prisma.recv(), timeout=10))
                    if connected.get("type") != "connected":
                        raise ValueError(
                            connected.get("message", "Prisma did not confirm the streaming session.")
                        )
                    transcript_segments.clear()
                    seen_segment_ids.clear()
                    transcript_event.clear()
                    active_audio_turn_id = turn_id
                    reader_task = asyncio.create_task(read_prisma())
                    await websocket.send_json(
                        {
                            "type": "recording_ready",
                            "message": "Microphone connected to Prisma.",
                            "model": connected.get("config", {}).get("model", "prisma"),
                        }
                    )
                except (ValueError, WebSocketException, OSError, asyncio.TimeoutError) as exc:
                    if prisma is not None:
                        await prisma.close()
                        prisma = None
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": f"Could not connect to Prisma streaming: {exc}",
                        }
                    )
                continue
            if event_type == "cancel_audio":
                if reader_task is not None:
                    reader_task.cancel()
                    try:
                        await reader_task
                    except asyncio.CancelledError:
                        pass
                    reader_task = None
                if prisma is not None:
                    try:
                        await prisma.close()
                    except (ConnectionClosed, WebSocketException, OSError) as exc:
                        await websocket.send_json(
                            {"type": "error", "message": f"Could not stop the Prisma recording: {exc}"}
                        )
                    prisma = None
                active_audio_turn_id = None
                transcript_segments.clear()
                seen_segment_ids.clear()
                await websocket.send_json({"type": "recording_cancelled"})
                continue
            if event_type in (
                "review_order",
                "cancel_review",
                "confirm_order",
                "adjust_item",
                "clear_order",
            ):
                if prisma is not None:
                    await websocket.send_json(
                        {"type": "error", "message": "Please wait until the voice turn is complete before changing the basket."}
                    )
                    continue
                try:
                    current_state = SESSIONS[session_id]
                    if event_type == "review_order":
                        state, outcome = review_order(current_state)
                    elif event_type == "cancel_review":
                        state, outcome = cancel_review(current_state)
                    elif event_type == "confirm_order":
                        state, outcome = confirm_order(current_state)
                    elif event_type == "clear_order":
                        state, outcome = clear_order(current_state)
                    else:
                        key = event.get("key")
                        delta = event.get("delta")
                        if not isinstance(key, str) or not isinstance(delta, int) or isinstance(delta, bool):
                            raise ValueError("Choose a menu item and a valid quantity change.")
                        state, outcome = adjust_item(current_state, key, delta)
                except ValueError as exc:
                    await websocket.send_json({"type": "error", "message": str(exc)})
                    continue
                SESSIONS[session_id] = state
                await websocket.send_json(
                    {
                        "type": "result",
                        **outcome,
                        **state,
                        "scene": scene_view(state),
                        "menu": menu_payload(state.get("language", "kn")),
                    }
                )
                continue
            if event_type == "stop_audio":
                request_turn_id = turn_id or active_audio_turn_id
                if prisma is None:
                    await websocket.send_json(
                        {"type": "error", "message": "There is no active microphone recording to stop."}
                    )
                    continue
                try:
                    previous_segments = len(transcript_segments)
                    transcript_event.clear()
                    await prisma.send(json.dumps({"type": "commit"}))
                    try:
                        await asyncio.wait_for(transcript_event.wait(), timeout=4)
                    except asyncio.TimeoutError:
                        pass
                    if len(transcript_segments) > previous_segments:
                        await asyncio.sleep(0.15)
                    transcript = " ".join(transcript_segments).strip()
                except (ConnectionClosed, WebSocketException, OSError) as exc:
                    transcript = " ".join(transcript_segments).strip()
                    await websocket.send_json(
                        {"type": "error", "message": f"Prisma streaming ended unexpectedly: {exc}"}
                    )
                finally:
                    if reader_task is not None:
                        reader_task.cancel()
                        try:
                            await reader_task
                        except asyncio.CancelledError:
                            pass
                        reader_task = None
                    await prisma.close()
                    prisma = None
                    active_audio_turn_id = None

                if not transcript:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "Prisma did not detect speech. Check that the browser is using the correct microphone, then try again.",
                        }
                    )
                    continue
                try:
                    state, outcome = process_turn(SESSIONS[session_id], transcript)
                except ValueError as exc:
                    await websocket.send_json({"type": "error", "message": str(exc)})
                    continue
                SESSIONS[session_id] = state
                result = {
                    "type": "result",
                    "transcript": transcript,
                    **outcome,
                    **state,
                }
                cache_turn_result(request_turn_id, result)
                await websocket.send_json(result)
                continue
            if event_type == "transcript":
                supplied_transcript = event.get("text")
                transcript = supplied_transcript.strip() if isinstance(supplied_transcript, str) else ""
                if not transcript:
                    await websocket.send_json({"type": "error", "message": "Enter an order to continue."})
                    continue
            else:
                await websocket.send_json({"type": "error", "message": "Unsupported message type."})
                continue

            try:
                state, outcome = process_turn(SESSIONS[session_id], transcript)
            except ValueError as exc:
                await websocket.send_json({"type": "error", "message": str(exc)})
                continue
            SESSIONS[session_id] = state
            result = {
                "type": "result",
                "transcript": transcript,
                **outcome,
                **state,
            }
            cache_turn_result(turn_id, result)
            await websocket.send_json(result)
    except WebSocketDisconnect:
        pass
    finally:
        if reader_task is not None:
            reader_task.cancel()
        if prisma is not None:
            await prisma.close()

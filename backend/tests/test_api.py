import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ["GNANI_API_KEY"] = ""

from fastapi.testclient import TestClient

from backend.main import VOICE_LINES, app, prisma_stream_headers


class FakePrismaSocket:
    def __init__(self):
        self.events = asyncio.Queue()
        self.frames = []

    async def recv(self):
        return json.dumps({
            "type": "connected",
            "config": {"sample_rate": 16000, "model": "prisma-v3.0"},
        })

    def __aiter__(self):
        return self

    async def __anext__(self):
        event = await self.events.get()
        if event is None:
            raise StopAsyncIteration
        return event

    async def send(self, payload):
        if isinstance(payload, bytes):
            self.frames.append(payload)
        elif json.loads(payload).get("type") == "commit":
            transcript = json.dumps({
                "type": "transcript",
                "text": "ಎರಡು ಇಡ್ಲಿ ಮತ್ತು ಒಂದು ಕಾಫಿ",
                "segment_id": "test-segment",
                "detected_language_code": "kn-IN",
            })
            await self.events.put(transcript)
            await self.events.put(transcript)

    async def close(self):
        await self.events.put(None)


class SessionApiTests(unittest.TestCase):
    def test_kiosk_dialogue_lines_are_available_for_timbre(self):
        self.assertIn("order_added", VOICE_LINES)
        self.assertIn("order_review", VOICE_LINES)
        self.assertIn("order_confirmed", VOICE_LINES)
        self.assertIn("ಖಚಿತವಾಗಿದೆ", VOICE_LINES["order_confirmed"])
        self.assertIn("ಸಂಖ್ಯೆ ಹೇಳಿ", VOICE_LINES["greeting"])
        self.assertIn("ಅಷ್ಟೇ", VOICE_LINES["order_added"])
        self.assertIn("ಖಚಿತಪಡಿಸಿ", VOICE_LINES["order_review"])
        self.assertIn("ಸಂಖ್ಯೆಯನ್ನು ಸ್ಪಷ್ಟವಾಗಿ ಹೇಳಿ", VOICE_LINES["retry"])
        self.assertNotIn("water_greeting", VOICE_LINES)

    def test_prisma_headers_include_the_darshini_menu(self):
        with patch.dict(
            os.environ,
            {"GNANI_API_KEY": "test-key", "GNANI_STT_MODEL": "prisma-v3.0"},
        ):
            headers = prisma_stream_headers()
        self.assertEqual(headers["language_code"], "indic-auto")
        self.assertEqual(headers["x-sample-rate"], "16000")
        keyterms = json.loads(headers["keyterms"])
        self.assertIn("ಇಡ್ಲಿ", keyterms)
        self.assertIn("இட்லி", keyterms)
        self.assertIn("ఇడ్లీ", keyterms)
        self.assertIn("Tamil, Telugu", headers["topic"])

    def test_prisma_v25_uses_the_selected_native_language(self):
        for language, expected_code in (("kn", "kn-IN"), ("ta", "ta-IN"), ("te", "te-IN")):
            with self.subTest(language=language), patch.dict(
                os.environ,
                {"GNANI_API_KEY": "test-key", "GNANI_STT_MODEL": "prisma-v2.5"},
            ):
                self.assertEqual(prisma_stream_headers(language)["language_code"], expected_code)

    def test_create_session_returns_native_menu_names_for_supported_locales(self):
        with TestClient(app) as client:
            kannada = client.post("/api/session?language=kn").json()
            tamil = client.post("/api/session?language=ta").json()
            telugu = client.post("/api/session?language=te").json()
            self.assertEqual(kannada["language"], "kn")
            self.assertEqual(kannada["menu"][0]["localized_title"], "ಇಡ್ಲಿ")
            self.assertEqual(kannada["menu"][16]["localized_title"], "ಚಹಾ")
            self.assertEqual(tamil["language"], "ta")
            self.assertEqual(tamil["line"], "வணக்கம்! என்ன வேண்டும்? உணவுப் பொருளையும் எண்ணிக்கையையும் சொல்லுங்கள்.")
            self.assertEqual(telugu["language"], "te")
            self.assertEqual(telugu["line"], "నమస్కారం! మీకు ఏమి కావాలి? పదార్థం పేరు, సంఖ్య చెప్పండి.")
            self.assertEqual(tamil["menu"][0]["localized_title"], "இட்லி")
            self.assertEqual(telugu["menu"][0]["localized_title"], "ఇడ్లీ")
            self.assertEqual(client.post("/api/session?language=xx").status_code, 422)

    def test_kannada_receipt_uses_kannada_item_names(self):
        with TestClient(app) as client:
            session = client.post("/api/session?language=kn").json()
            with client.websocket_connect(f"/ws/session/{session['session_id']}") as socket:
                socket.send_json({"type": "transcript", "text": "ಎರಡು ಇಡ್ಲಿ ಮತ್ತು ಒಂದು ಕಾಫಿ"})
                socket.receive_json()
                socket.send_json({"type": "review_order"})
                socket.receive_json()
                socket.send_json({"type": "confirm_order"})
                result = socket.receive_json()

            self.assertEqual(
                [item["title"] for item in result["bill"]["items"]],
                ["ಇಡ್ಲಿ", "ಕಾಫಿ"],
            )

    def test_tamil_and_telugu_websocket_orders_and_language_switch_preserve_basket(self):
        with TestClient(app) as client:
            session = client.post("/api/session?language=ta").json()
            with client.websocket_connect(f"/ws/session/{session['session_id']}") as socket:
                socket.send_json({"type": "transcript", "text": "இரண்டு இட்லி மற்றும் ஒரு காபி"})
                tamil_result = socket.receive_json()
                self.assertEqual(tamil_result["order"], {"idli": 2, "coffee": 1})
                self.assertIn("சேர்த்துவிட்டேன்", tamil_result["line"])

                socket.send_json({"type": "set_language", "language": "te"})
                telugu_result = socket.receive_json()
                self.assertEqual(telugu_result["order"], {"idli": 2, "coffee": 1})
                self.assertEqual(telugu_result["language"], "te")
                self.assertEqual(telugu_result["menu"][0]["localized_title"], "ఇడ్లీ")
                self.assertIn("సరే", telugu_result["line"])

                socket.send_json({"type": "transcript", "text": "ఒక కాఫీ తీసేయండి"})
                removed = socket.receive_json()
                self.assertEqual(removed["order"], {"idli": 2})

    def test_timbre_voice_route_uses_language_voice_and_localized_line(self):
        class FakeResponse:
            content = b"RIFFtest"
            headers = {"content-type": "audio/wav"}
            is_error = False

        class FakeAsyncClient:
            def __init__(self, **kwargs):
                self.timeout = kwargs["timeout"]

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                del args
                return None

            async def post(self, url, headers, json):
                requests.append({"url": url, "headers": headers, "payload": json})
                return FakeResponse()

        requests = []
        with tempfile.TemporaryDirectory() as cache_dir:
            with patch("backend.main.httpx.AsyncClient", FakeAsyncClient), patch(
                "backend.main.VOICE_CACHE", Path(cache_dir)
            ), patch.dict(os.environ, {"GNANI_API_KEY": "test-key", "GNANI_TTS_MODEL": "timbre-v2.5"}):
                with TestClient(app) as client:
                    tamil = client.get("/api/voice/greeting?language=ta")
                    telugu = client.get("/api/voice/greeting?language=te")
                    with patch.dict(os.environ, {"GNANI_TTS_MODEL": "timbre-v3.0"}):
                        telugu_v3 = client.get("/api/voice/greeting?language=te")
        self.assertEqual(tamil.status_code, 200)
        self.assertEqual(telugu.status_code, 200)
        self.assertEqual(telugu_v3.status_code, 200)
        self.assertEqual(
            [(request["payload"]["voice"], request["payload"]["language"]) for request in requests],
            [("Noopur", "ta-IN"), ("Yukti", "te-IN"), ("Shivani", "te-IN")],
        )
        self.assertIn("வணக்கம்", requests[0]["payload"]["text"])
        self.assertIn("నమస్కారం", requests[1]["payload"]["text"])

    def test_typed_turns_review_and_confirm_over_websocket(self):
        with TestClient(app) as client:
            session = client.post("/api/session").json()
            self.assertEqual(session["scene_key"], "order")
            self.assertEqual(session["line_key"], "greeting")
            self.assertFalse(session["speech_enabled"])
            self.assertEqual(len(session["menu"]), 20)
            self.assertNotIn("score", session)

            with client.websocket_connect(f"/ws/session/{session['session_id']}") as socket:
                socket.send_json({"type": "transcript", "text": "ಎರಡು ಇಡ್ಲಿ"})
                first = socket.receive_json()
                self.assertEqual(first["type"], "result")
                self.assertEqual(first["order"], {"idli": 2})

                socket.send_json({"type": "transcript", "text": "one coffee"})
                second = socket.receive_json()
                self.assertEqual(second["order"], {"idli": 2, "coffee": 1})
                self.assertEqual(second["scene"]["order_total"], 85)

                socket.send_json({"type": "review_order"})
                review = socket.receive_json()
                self.assertEqual(review["type"], "result")
                self.assertTrue(review["reviewing"])
                self.assertFalse(review["complete"])
                self.assertEqual(review["scene"]["stage_key"], "review")

                socket.send_json({"type": "confirm_order"})
                receipt = socket.receive_json()
                self.assertTrue(receipt["complete"])
                self.assertEqual(receipt["bill"]["total"], 85)
                self.assertEqual(receipt["bill"]["currency"], "INR")

    def test_websocket_voice_turn_can_remove_and_reduce_existing_items(self):
        with TestClient(app) as client:
            session = client.post("/api/session").json()
            with client.websocket_connect(f"/ws/session/{session['session_id']}") as socket:
                socket.send_json({"type": "transcript", "text": "two idlis and one coffee"})
                added = socket.receive_json()
                self.assertEqual(added["order"], {"idli": 2, "coffee": 1})

                socket.send_json({"type": "transcript", "text": "I don't want idli"})
                removed = socket.receive_json()
                self.assertEqual(removed["order"], {"coffee": 1})
                self.assertEqual(removed["line_key"], "order_removed")

                socket.send_json({"type": "transcript", "text": "reduce coffee to zero"})
                reduced = socket.receive_json()
                self.assertEqual(reduced["order"], {})
                self.assertEqual(reduced["line_key"], "order_changed")

                socket.send_json({"type": "transcript", "text": "three idli and one coffee"})
                added_again = socket.receive_json()
                self.assertEqual(added_again["order"], {"idli": 3, "coffee": 1})

                socket.send_json({"type": "transcript", "text": "reduce 3 idli to 1 idli"})
                set_quantity = socket.receive_json()
                self.assertEqual(set_quantity["order"], {"idli": 1, "coffee": 1})

                socket.send_json({"type": "transcript", "text": "cancel my order"})
                canceled = socket.receive_json()
                self.assertEqual(canceled["order"], {})
                self.assertTrue(canceled["order_updated"])

    def test_websocket_voice_turn_supports_kannada_edits_and_cancellation(self):
        with TestClient(app) as client:
            session = client.post("/api/session").json()
            with client.websocket_connect(f"/ws/session/{session['session_id']}") as socket:
                socket.send_json({"type": "transcript", "text": "ಮೂರು ಇಡ್ಲಿ ಮತ್ತು ಎರಡು ಕಾಫಿ"})
                added = socket.receive_json()
                self.assertEqual(added["order"], {"idli": 3, "coffee": 2})

                socket.send_json({"type": "transcript", "text": "ಒಂದು ಇಡ್ಲಿಯನ್ನು ತೆಗೆದುಹಾಕಿ"})
                removed = socket.receive_json()
                self.assertEqual(removed["order"], {"idli": 2, "coffee": 2})

                socket.send_json({"type": "transcript", "text": "ಇನ್ನೂ ಎರಡು ಇಡ್ಲಿ ಸೇರಿಸಿ"})
                increased = socket.receive_json()
                self.assertEqual(increased["order"], {"idli": 4, "coffee": 2})

                socket.send_json({"type": "transcript", "text": "ಮೂರು ಇಡ್ಲಿ ಒಂದು ಇಡ್ಲಿಗೆ ಕಡಿಮೆ ಮಾಡಿ"})
                set_quantity = socket.receive_json()
                self.assertEqual(set_quantity["order"], {"idli": 1, "coffee": 2})

                socket.send_json({"type": "transcript", "text": "ನನ್ನ ಆರ್ಡರ್ ರದ್ದು ಮಾಡಿ"})
                canceled = socket.receive_json()
                self.assertEqual(canceled["order"], {})

    def test_websocket_turn_id_prevents_duplicate_additions(self):
        with TestClient(app) as client:
            session = client.post("/api/session").json()
            with client.websocket_connect(f"/ws/session/{session['session_id']}") as socket:
                request = {
                    "type": "transcript",
                    "turn_id": "customer-turn-1",
                    "text": "one coffee",
                }
                socket.send_json(request)
                first = socket.receive_json()
                self.assertEqual(first["order"], {"coffee": 1})
                self.assertNotIn("replayed", first)

                socket.send_json({
                    "type": "transcript",
                    "turn_id": "customer-turn-2",
                    "text": "one coffee",
                })
                second_turn = socket.receive_json()
                self.assertEqual(second_turn["order"], {"coffee": 2})

                socket.send_json(request)
                replay = socket.receive_json()
                self.assertTrue(replay["replayed"])
                self.assertEqual(second_turn["order"], {"coffee": 2})
                self.assertEqual(replay["order"], {"coffee": 2})

    def test_websocket_quantity_limit_rejection_does_not_partially_apply(self):
        with TestClient(app) as client:
            session = client.post("/api/session").json()
            with client.websocket_connect(f"/ws/session/{session['session_id']}") as socket:
                socket.send_json({"type": "transcript", "text": "ten idli"})
                added = socket.receive_json()
                self.assertEqual(added["order"], {"idli": 10})

                socket.send_json({"type": "transcript", "text": "one coffee and one idli"})
                rejected = socket.receive_json()
                self.assertEqual(rejected["order"], {"idli": 10})
                self.assertEqual(rejected["line_key"], "quantity_limit")
                self.assertTrue(rejected["quantity_limit_exceeded"])

    def test_basket_controls_update_order_before_confirmation(self):
        with TestClient(app) as client:
            session = client.post("/api/session").json()
            with client.websocket_connect(f"/ws/session/{session['session_id']}") as socket:
                socket.send_json({"type": "adjust_item", "key": "masala_dosa", "delta": 2})
                added = socket.receive_json()
                self.assertEqual(added["order"], {"masala_dosa": 2})
                self.assertEqual(added["scene"]["order_total"], 160)

                socket.send_json({"type": "review_order"})
                socket.receive_json()
                socket.send_json({"type": "adjust_item", "key": "masala_dosa", "delta": -1})
                edited = socket.receive_json()
                self.assertTrue(edited["reviewing"])
                self.assertEqual(edited["order"], {"masala_dosa": 1})
                self.assertEqual(edited["scene"]["order_total"], 80)

                socket.send_json({"type": "transcript", "text": "keep shopping"})
                canceled_review = socket.receive_json()
                self.assertFalse(canceled_review["reviewing"])

    def test_unknown_session_and_invalid_menu_controls_are_explicit(self):
        with TestClient(app) as client:
            invalid = client.post("/api/session?scene_key=water")
            self.assertEqual(invalid.status_code, 404)

            session = client.post("/api/session").json()
            with client.websocket_connect(f"/ws/session/{session['session_id']}") as socket:
                socket.send_json({"type": "adjust_item", "key": "not-a-menu-item", "delta": 1})
                error = socket.receive_json()
                self.assertEqual(error["type"], "error")
                self.assertIn("no longer available", error["message"])

    def test_prisma_realtime_pcm_round_trip(self):
        prisma_socket = FakePrismaSocket()

        async def fake_connect(uri, **kwargs):
            self.assertEqual(uri, "wss://api.vachana.ai/stt/v3/stream")
            headers = kwargs["additional_headers"]
            self.assertEqual(headers["model"], "prisma-v3.0")
            self.assertEqual(headers["language_code"], "indic-auto")
            self.assertEqual(headers["x-sample-rate"], "16000")
            return prisma_socket

        with patch.dict(
            os.environ,
            {"GNANI_API_KEY": "test-key", "GNANI_STT_MODEL": "prisma-v3.0"},
        ), patch("backend.main.websocket_connect", new=fake_connect):
            with TestClient(app) as client:
                session = client.post("/api/session").json()
                with client.websocket_connect(f"/ws/session/{session['session_id']}") as socket:
                    socket.send_json({"type": "start_audio", "turn_id": "audio-turn-1"})
                    self.assertEqual(socket.receive_json()["type"], "recording_ready")
                    socket.send_bytes(bytes(1024))
                    socket.send_json({"type": "stop_audio", "turn_id": "audio-turn-1"})
                    live_messages = []
                    result = socket.receive_json()
                    while result["type"] == "live_transcript":
                        live_messages.append(result)
                        result = socket.receive_json()
                    self.assertEqual(len(live_messages), 2)
                    self.assertEqual(live_messages[0]["text"], live_messages[1]["text"])
                    self.assertEqual(result["type"], "result")
                    self.assertEqual(result["transcript"], "ಎರಡು ಇಡ್ಲಿ ಮತ್ತು ಒಂದು ಕಾಫಿ")
                    self.assertEqual(result["order"], {"idli": 2, "coffee": 1})
                    self.assertEqual(len(prisma_socket.frames), 1)
                    self.assertEqual(len(prisma_socket.frames[0]), 1024)

                    socket.send_json({"type": "stop_audio", "turn_id": "audio-turn-1"})
                    replay = socket.receive_json()
                    self.assertTrue(replay["replayed"])
                    self.assertEqual(replay["order"], {"idli": 2, "coffee": 1})

    def test_customer_can_cancel_listening_and_use_touch_controls(self):
        prisma_socket = FakePrismaSocket()

        async def fake_connect(uri, **kwargs):
            self.assertEqual(uri, "wss://api.vachana.ai/stt/v3/stream")
            self.assertEqual(kwargs["open_timeout"], 15)
            return prisma_socket

        with patch.dict(os.environ, {"GNANI_API_KEY": "test-key"}), patch(
            "backend.main.websocket_connect", new=fake_connect
        ):
            with TestClient(app) as client:
                session = client.post("/api/session").json()
                with client.websocket_connect(f"/ws/session/{session['session_id']}") as socket:
                    socket.send_json({"type": "start_audio"})
                    self.assertEqual(socket.receive_json()["type"], "recording_ready")
                    socket.send_json({"type": "cancel_audio"})
                    self.assertEqual(socket.receive_json()["type"], "recording_cancelled")
                    socket.send_json({"type": "adjust_item", "key": "idli", "delta": 2})
                    result = socket.receive_json()
                    self.assertEqual(result["order"], {"idli": 2})


if __name__ == "__main__":
    unittest.main()

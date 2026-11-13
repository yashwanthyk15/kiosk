# Multilingual Ordering Kiosk

Multilingual Ordering Kiosk is a voice-first self-ordering kiosk prototype for a Bengaluru darshini. Customers can browse a 20-item sample menu, build or edit a basket by speaking or using on-screen controls, review the subtotal, explicitly confirm the order, and receive an itemized INR receipt. The language selector localizes the interface and counter responses in Kannada, Tamil, or Telugu. English and code-switching remain accepted for order input in every mode. This MVP has no accounts, payment processing, or live restaurant integration; menu prices are illustrative.

## Order flow

1. In Kannada mode, follow the three on-screen steps: start the order, allow microphone access if prompted, then say an item and quantity. The page shows sample phrases and explains how to adjust and confirm the basket. After starting, customers can also type instead of speaking.
2. When speech is configured, Srinivas greets the customer and the app listens automatically.
3. Select Kannada, Tamil, or Telugu for the interface and counter response. Add items and quantities in that language, English, or a mixture. Each item is capped at 10. The basket and subtotal update after each understood request, and the counter immediately tells the customer what to say next.
4. Edit quantities using voice or the basket controls. The deterministic intent parser maps different wordings and word orders to add, set, decrease, remove, or no-change actions. Kannada examples include “ಇಡ್ಲಿ ಒಂದನ್ನು ಕಡಿಮೆ ಮಾಡಿ”, “ಒಂದನ್ನು ಕಡಿಮೆ ಮಾಡಿ ಇಡ್ಲಿ”, “ಇಡ್ಲಿ ಒಂದೇ ಇರಲಿ”, and “ಇಡ್ಲಿ ಒಂದು ಸಾಕು”. Tamil examples include “இரண்டு இட்லி மற்றும் ஒரு காபி” and “ஒரு இட்லியை நீக்குங்கள்”; Telugu examples include “రెండు ఇడ్లీలు మరియు ఒక కాఫీ” and “ఒక ఇడ్లీ తీసేయండి”. Unclear changes leave the basket untouched and ask for clarification.
5. Choose **Review order** (or say “ಅಷ್ಟೇ” / “that’s all”). Review does not place the order.
6. Explicitly confirm to place the order and generate the receipt. The customer can return to editing before confirmation.

## Run locally

Requirements: Node.js 20+ and Python 3.10+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

In another terminal:

```powershell
npm install
npm run dev
```

Open the Vite URL shown in the terminal. The basket can be built with typed Kannada, Tamil, Telugu, or English even when Gnani credentials are not configured. Live microphone input and Timbre character audio require a server-side `GNANI_API_KEY`.

## Gnani speech (optional)

Set these variables in the backend environment; never put the API key in frontend variables or source control:

```text
GNANI_API_KEY=your-gnani-key
GNANI_STT_MODEL=prisma-v3.0
GNANI_TTS_MODEL=timbre-v2.5
GNANI_TTS_VOICE=Kavin
```

Prisma uses its realtime WebSocket endpoint (`/stt/v3/stream`) through the backend proxy. The browser sends mono 16 kHz PCM frames to the backend; the Gnani key stays server-side. Prisma v3.0 uses `indic-auto` and receives the menu aliases in all three Indian languages as key terms. Prisma v2.5 uses the selected language code. When the customer pauses, the browser commits the turn and the recognized request is passed to the same ordering logic used by typed input.

Timbre uses its REST endpoint with Kavin for Kannada, Noopur for Tamil, and Yukti for Telugu when using Timbre v2.5. Timbre v3.0 uses Shivani for all three languages. The requested language code accompanies each line, and audio is cached under `backend/.cache/voice`. Tamil and Telugu voices and language codes are listed in the [Gnani voice catalog](https://docs.gnani.ai/api/TTS/available-voices.md); multilingual Prisma v3 behavior is described in the [Prisma v3 documentation](https://docs.gnani.ai/api/STT/models/prisma-v3.md). This confirms documented support, not live account availability or tested audio quality.

Ordering uses the local Kannada, Tamil, Telugu, and English phrase matcher and deterministic intent parser. It recognizes localized menu names, common aliases, quantities (including native-script digits), and maps tested phrases to canonical add, set, decrease, remove, or unchanged actions. Item names may come before or after their quantities; each quantity is assigned to only one item mention, and conjunctions such as “coffee and 3 poori” keep the quantity with the following item. This is bounded language-specific logic, not complete language understanding; only covered phrases and inflections are guaranteed by tests. Removing without a quantity clears that item; a spoken quantity subtracts only that amount. Corrections replace a false start only when the target is unambiguous. Vague references prompt for the item instead of changing the basket. Mixed requests preserve unrelated items; an over-limit item rejects the entire spoken turn. Repeated turn IDs are not applied twice, and repeated Prisma segment IDs are ignored within a recording. Customer transcripts are not sent to an external language model.

## Checks

```powershell
python -m unittest backend.tests.test_game backend.tests.test_api
python -m compileall -q backend
npm run build
```

## Deploy

- **Frontend:** deploy the Vite project to Vercel. Set `VITE_API_URL` to the Render service origin.
- **Backend:** deploy `backend.main:app` on Render with `pip install -r requirements.txt` and `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`. Configure `GNANI_API_KEY` and `FRONTEND_ORIGINS` in Render environment settings.

Sessions are in-memory for this single-player MVP and reset when the backend restarts. No account data or audio recordings are persisted; only the explicitly generated character voice lines are cached. Orders are prototypes and are not sent to a restaurant or payment provider.

# Multilingual Ordering Kiosk — Project Handoff

Read this document first to understand the Multilingual Ordering Kiosk without needing to rediscover the project from source. It is the current product, architecture, behavior, runtime, safety, and continuation reference. It contains no API keys or secret values. If a detail here conflicts with the code, inspect the named source files and update this handoff when behavior changes.

## Product

Multilingual Ordering Kiosk is a voice-first self-ordering kiosk prototype for a Bengaluru darshini. A customer can select Kannada, Tamil, or Telugu for localized UI and counter responses, then order in that language, English, or a mixture. Customers can review the basket and subtotal, edit items, explicitly confirm, and see an itemized INR receipt.

This is a prototype, not a live restaurant POS: no accounts, payment processing, kitchen/restaurant integration, inventory or persistent order storage. Menu and prices are illustrative. No LLM is used to interpret customer orders.

**Product safety principle:** never silently guess what item or quantity the customer meant. Ambiguous edits should preserve the current basket and ask a short clarification. Order changes are not final until the customer explicitly reviews and confirms.

## Stack and layout

- Frontend: React 18 + Vite, plain CSS, `lucide-react`.
- Backend: FastAPI, in-memory sessions, REST setup/health routes, WebSocket ordering and audio route.
- Speech recognition: Gnani Prisma v3.0 realtime WebSocket, proxied by the backend.
- Character speech: Gnani Timbre REST: v2.5 uses Kavin (Kannada), Noopur (Tamil), and Yukti (Telugu); v3.0 uses Shivani for all three. Synthesized lines are cached locally.
- Order interpretation: deterministic Python matching and dialogue logic in Kannada, Tamil, Telugu, and English; no Gemini or OpenAI integration.
- Main source files:
  - `src/App.jsx`: kiosk UI, transcript display, WebSocket state, voice playback and listening flow.
  - `src/useMicrophone.js`: microphone capture, mono 16 kHz PCM frames, silence detection.
  - `src/api.js`: frontend API/WebSocket/voice URLs.
  - `src/locales.js`: language options, localized UI copy, and language-specific examples.
  - `backend/main.py`: FastAPI endpoints, Prisma proxy, session handling, Timbre cache.
  - `backend/menu.py`: 20-item menu, localized labels, and Kannada/Tamil/Telugu aliases.
  - `backend/matching.py`: Kannada/Tamil/Telugu/English normalization, menu-name and quantity matching.
  - `backend/dialogue.py`: basket operations, phrase/action logic, review, confirmation and bill.
  - `backend/tests/test_game.py`: matcher and dialogue behavior tests.
  - `backend/tests/test_api.py`: REST/WebSocket/backend integration tests.
  - `README.md`: user-facing setup and behavior notes.
  - `PROJECT_HANDOFF.md`: this continuation guide. Update it when behavior, validation, setup, or limitations change.

## How a customer turn works

1. `src/App.jsx` creates a session with `POST /api/session?language=kn|ta|te`, opens `/ws/session/{session_id}`, and uses the returned localized menu/state. A `set_language` WebSocket event switches display and response language without clearing the basket. Session and order state are held in backend process memory.
2. With speech enabled, the browser starts microphone capture and sends 512-sample, 16-bit mono PCM frames (1024 bytes each) at 16 kHz. `src/useMicrophone.js` detects a pause, then the frontend sends `stop_audio`.
3. `backend/main.py` proxies audio to Gnani Prisma. Prisma v3.0 uses `indic-auto` and multilingual menu keyterms; Prisma v2.5 uses the selected language code. Transcript segments are shown in the live transcript; repeated non-empty Prisma `segment_id`s are ignored within that recording. The committed transcript is passed into `backend.dialogue.process_turn`.
4. `backend/matching.py` normalizes Kannada/Tamil/Telugu digits and text, finds menu aliases and quantities, and returns item spans and match details. `backend/dialogue.py` assigns actions, updates an isolated copy of the basket, and returns canonical state plus localized response text.
5. The backend WebSocket sends a `result` message. The frontend displays server basket/receipt and, when voice is enabled, plays the matching Timbre line before listening again.
6. During review, only explicit confirmation places the prototype order. The server creates the receipt; it does not transmit the order to a restaurant.

### Backend interfaces

- `GET /api/health`: reports backend availability and whether `GNANI_API_KEY` is configured (`speech_enabled`).
- `POST /api/session?scene_key=order&language=kn|ta|te`: creates an in-memory locale-specific order session and returns state, localized menu labels, greeting, and speech availability.
- `GET /api/voice/{line_key}?language=kn|ta|te`: synthesizes or serves a cached Timbre response for a localized dialogue line.
- `WS /ws/session/{session_id}` accepts JSON events:
  - `{"type":"transcript","text":"...","turn_id":"..."}`: typed or already-transcribed request. The UI generates a unique ID.
  - `{"type":"start_audio","turn_id":"..."}`, followed by binary PCM frames and `{"type":"stop_audio","turn_id":"..."}`: live Prisma turn.
  - `{"type":"cancel_audio"}`: discard current recording.
  - `{"type":"review_order"}`, `{"type":"cancel_review"}`, `{"type":"confirm_order"}`, `{"type":"clear_order"}`.
  - `{"type":"set_language","language":"kn|ta|te"}` changes the selected locale without resetting the basket.
  - `{"type":"adjust_item","key":"idli","delta":1}`: direct basket-control change.
  - Server emits `live_transcript`, `recording_ready`, `speech_start`, `stt_processing`, `result`, `recording_cancelled`, or explicit `error` messages.
- A `result` includes order state and server-built `scene`; relevant flags include `order_updated`, `order_review`, `order_confirmed`, `clarification_required`, and `quantity_limit_exceeded`. The UI trusts server state over local interpretation.
- On requests with `turn_id`, the backend caches up to 100 results per session. A duplicate `transcript`/`stop_audio` ID does not apply the order again; the replay response carries the *current* authoritative basket, not the historical snapshot. Cache and sessions are lost on backend restart.

## Implemented behavior

- Add menu items and quantities by voice, typed input, or item controls. Each menu item is capped at 10.
- Remove an item entirely or subtract a spoken amount; subtraction clamps at zero.
- Set an item's final quantity, including zero.
- Increase an existing quantity and handle multiple item edits in a turn.
- Clear the whole basket separately from removing one menu item.
- Review the order without placing it; confirmation is a separate action. Before confirmation, return to editing.
- Generate an itemized INR receipt.
- English, Kannada, Tamil, and Telugu matching for configured menu names, aliases, quantities, native-script digits, tested inflections, and edit phrases. The 20 menu entries have Tamil/Telugu names/aliases and localized display labels.
- Quantity assignment supports both item-first and quantity-first lists. Each quantity token is consumed by at most one item mention; conjunctions preserve phrases such as “coffee and 3 poori” as one coffee and three pooris. Common speech variants “bisibele bath” and “bisbele bath” map to bisi bele bath.
- UI and counter dialogue localization for Kannada-English, Tamil, and Telugu. Timbre uses Kavin for Kannada, Noopur for Tamil, and Yukti for Telugu on v2.5; v3.0 uses Shivani. TTS support is documented, but speech audio has not been live-tested for the newly added languages.
- Spoken item mentions are resolved into canonical `add`, `set`, `decrease`, `remove`, or `unchanged` intents before basket mutation. Kannada coverage includes alternate verb/quantity order, “ಒಂದೇ ಇರಲಿ” / “ಒಂದು ಸಾಕು” final-quantity forms, add-another phrasing, and negated edits. Ambiguous requests remain non-mutating and ask for clarification.
- Explicit corrections like “three idli, actually make that two” discard the false start. If several items could be the correction target, ask instead of guessing.
- Additive requests (“add one more”) are distinguished from setting a final quantity (“make it one”).
- Vague references (“remove one”, “cancel it”, “the last item”) ask the customer to name the item.
- Mixed “keep” and negated actions change only the explicitly requested items. Negated whole-order cancellation does not clear the basket.
- Empty, partial, and unclear speech does not change the basket. Quantity overflow raises a clear error before applying any part of a mixed request; removing more than ordered clamps at zero.
- Tested Kannada-English code-switching, e.g. “ಎರಡು idli remove ಮಾಡಿ”, is supported.
- Representative Tamil and Telugu add, remove, decrease, set-to-quantity/zero, correction, whole-order cancellation, ambiguity, limit, review, confirmation, and receipt behavior is covered by deterministic tests. These are bounded phrase rules, not general handling of every dialect or inflection.
- Explicitly requested negative confirmation does not place an order. Confirmation still requires the review stage; a completed order cannot be edited.
- Prisma transcript segments with repeated `segment_id` values are deduplicated during a recording. Frontend transcript/audio turns carry unique request IDs; the backend caches the last 100 results per session to avoid applying a duplicate turn twice. A replay response contains the current authoritative basket.
- Transcript display highlights matched terms; backend is authoritative for order state.
- In Kannada mode, a prominent, colorful first-visit guide appears before the basket with steps, sample spoken requests, microphone permission guidance, and the typed-input alternative. The Kannada menu hides romanized labels; controls and guidance use larger type and touch targets.

### Intent and mutation rules

- Add/no modifier: the spoken quantity is added to the existing quantity.
- Explicit set wording (“set/change/make it …”) assigns the final quantity. “Reduce ... to ...” is a set, not a subtraction. Tested duplicate-item set requests suppress the repeated target item mention.
- Remove without an amount removes the named item. Remove with an amount subtracts that many. Explicit set to zero removes it.
- Decrease/reduce with an amount subtracts that amount and clamps at zero.
- Maximum is 10 per item. A spoken multi-item request exceeding the limit returns a spoken limit line with `order_updated:false`; none of the request is applied. Direct touch-control overflow still reports a WebSocket `error`.
- “Remove all idli” targets idli only; whole-basket cancellation requires an explicit whole-order phrase.
- Correction handling is bounded to explicit English markers (`actually`, `I mean`, `scratch that`, `wait`, `sorry`). It can replace a false-start quantity when there is one clear item target; if multiple targets or missing corrected intent make it ambiguous, it asks for clarification.
- Confirmation requires `reviewing == true`; confirmed orders reject additional edits. A recognized negated confirm should not confirm.

Examples covered by tests:

- “remove two idlis”, “I don’t want idli”, “ಎರಡು ಇಡ್ಲಿಯನ್ನು ತೆಗೆದುಹಾಕಿ”
- “reduce idli to one”, “reduce 3 idli to 1 idli”
- “ಇಡ್ಲಿ ಒಂದನ್ನು ಕಡಿಮೆ ಮಾಡಿ”, “ಒಂದನ್ನು ಕಡಿಮೆ ಮಾಡಿ ಇಡ್ಲಿ”
- “ಇಡ್ಲಿ ಒಂದೇ ಇರಲಿ”, “ಇಡ್ಲಿ ಒಂದು ಸಾಕು”, “ಇನ್ನೊಂದು ಇಡ್ಲಿ ಸೇರಿಸಿ”
- “ಇಡ್ಲಿ ಕಡಿಮೆ ಮಾಡಬೇಡಿ” leaves the basket unchanged.
- “ಮೂರು ಇಡ್ಲಿ ಒಂದು ಇಡ್ಲಿಗೆ ಕಡಿಮೆ ಮಾಡಿ”
- “ಇಡ್ಲಿಯನ್ನು ಮೂರರಿಂದ ಒಂದಕ್ಕೆ ಇಳಿಸಿ”
- “ಇನ್ನೂ ಎರಡು ಇಡ್ಲಿ ಸೇರಿಸಿ”, “ಇಡ್ಲಿ ಒಂದನ್ನು ಹೆಚ್ಚಿಸಿ”
- “cancel my order”, “ನನ್ನ ಆರ್ಡರ್ ರದ್ದು ಮಾಡಿ”
- “three idli, actually make that two”; ambiguous corrections do not change the basket.
- “remove one”, “make it two”, “cancel it”; all request item clarification.
- “remove one idli and keep coffee”; idli changes and coffee stays unchanged.
- “ಎರಡು idli remove ಮಾಡಿ”, “one coffee ಸೇರಿಸಿ”
- “bisbele bath 2, cfee 3, poori 1” assigns 2 bisi bele baths, 3 coffees, and 1 puri.
- Removing or changing idli leaves coffee/vada quantities intact.

These are deterministic phrase rules, not general language understanding, semantic matching, or complete Kannada grammar support. A new voice phrase should be added only after checking the exact transcript Prisma produced and adding a regression test for it. The listed phrases prove only those test cases; they do not prove every dialect, inflection, menu word, or STT transcription works.

## Current validation and runtime

Latest backend verification after the item-first quantity matching fix:

- `python -m unittest discover -s backend/tests`: **67 tests passed**.
- `python -m compileall -q backend`: passed.
- `npm run build`: passed in the previous frontend validation; the latest change is backend-only.
- Browser check in Kannada mode confirmed the guide appears before the basket, shows example phrases, and has an enabled start button.
- `GET http://127.0.0.1:8000/api/health`: `{"status":"ok","speech_enabled":true}`.
- Local Vite page: `http://127.0.0.1:5173/`.
- The frontend now attaches a unique turn ID to both typed and microphone requests. The backend replays duplicate turn responses without reapplying them; newer basket state wins on delayed replays.
- Gnani docs list Timbre v2.5 Tamil/Telugu voices and Prisma v3 as multilingual/code-mix capable. Account access, live STT accuracy, and real TTS quality/credits have not been tested for these languages.
- Browser verification switched the selector to Tamil and Telugu and confirmed localized greetings/menu labels; no microphone/provider request was made for that check.
- Local server processes may stop when the terminal/session ends; check before assuming they are still active.

The workspace is Windows. The environment reported that this folder is not a Git repository; check again before using Git commands.

## Run locally

From the project root in PowerShell, backend:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal, frontend:

```powershell
npm install
npm run dev
```

Useful checks from the project root:

```powershell
python -m unittest discover -s backend/tests
python -m compileall -q backend
npm run build
```

## Speech configuration and secrets

There is a local `.env` file, and the last backend health check indicated speech was enabled. Do not print, copy, or paste its contents into chat. It should contain a server-side `GNANI_API_KEY`; optional settings documented in `README.md` are:

```text
GNANI_STT_MODEL=prisma-v3.0
GNANI_TTS_MODEL=timbre-v2.5
GNANI_TTS_VOICE=Kavin
```

The backend loads `.env` from the project root using `python-dotenv`. Do not print or paste the `.env` contents, put Gnani credentials in Vite/frontend environment variables, or commit them. `.env` should remain ignored by Git.

Prisma uses `wss://api.vachana.ai/stt/v3/stream`, with multilingual auto language detection, menu key terms, and mono 16 kHz PCM. Timbre uses `https://api.vachana.ai/api/v1/tts/inference`; generated audio is cached in `backend/.cache/voice`. Timbre v2.5 voices are Kavin (Kannada), Noopur (Tamil), and Yukti (Telugu); v3.0 uses Shivani for all three. Speech can incur provider credits; typed input and tests do not need speech credits.

Gemini/OpenAI matching integrations were deliberately removed after provider access/credit issues. Do not restore them unless explicitly requested. An old Gemini key was exposed in a prior tool output and rotation was advised; its rotation status is unknown. Rotate it if it could still be valid. This is a security follow-up, not a reason to expose or search for the key.

## Remaining limitations and next work

All ten previously identified edge-case categories now have initial implementation and regression coverage. Treat the rules as bounded and test-driven, not as “solved” for all natural speech:

- Correction markers include tested English, Tamil, and Telugu formulations; Kannada correction formulations and many regional variants still need verified LIVE TRANSCRIPTs and tests. The parser should clarify if it cannot identify one correction target.
- Tamil/Telugu matching has deterministic coverage for all configured menu labels and representative phrases, not exhaustive coverage of every dialect, inflection, code-switch, or Prisma transcription. Adding grammar-wide or broad fuzzy matching can cause unintended basket edits; prefer a verified alias/phrase plus regression test.
- “Last item” and other pronouns deliberately ask the customer to name an item; there is no conversational referent history. Do not silently add conversational memory without a clear product decision and tests.
- Duplicate idempotency requires the client to reuse the same `turn_id` for a retried request. The app gives each typed/audio turn a unique ID, but there is no durable cross-restart retry. Cache is in-memory, bounded to 100 IDs per session, and lost on backend restart; sessions themselves are also in-memory.
- Prisma can still misrecognize a phrase. To diagnose a live issue, record the exact LIVE TRANSCRIPT, basket before the turn, and basket after the turn. Do not spend Gnani credits for deterministic parser tests.
- Voice requests over the item limit now return a spoken rejection and leave the entire mixed turn unapplied. Touch-control over-limit changes still return a WebSocket error.
- Audio capture requires browser `AudioContext` to supply exactly 16 kHz; silence detection currently uses deprecated `ScriptProcessorNode` and fixed RMS/silence thresholds. An AudioWorklet migration or capture tuning is separate follow-up work.
- No live Prisma/Timbre test has been done for the new languages, and production hosting/deployment has not been verified from this handoff. Unit/WebSocket tests use deterministic transcripts and do not consume provider credits.

General product safety rule: when item or quantity intent is ambiguous, ask for clarification rather than guessing or silently changing the basket. Keep tests focused on `process_turn` first, then add a WebSocket regression test for behavior that crosses the API route.

For a real speech failure, capture the exact displayed LIVE TRANSCRIPT, the basket before the turn, and the resulting basket. That separates a speech-recognition error from an order-matcher error.

## Current starting instruction for the next chat

Use this prompt in the next chat; it supersedes any older prompt or test count in prior conversation summaries:

> Continue the Multilingual Ordering Kiosk project from `PROJECT_HANDOFF.md`; read it first and start with my latest specific request. Do not expose `.env` values or restore Gemini/OpenAI. Tamil/Telugu UI, dialogue, menu aliases, and deterministic phrase rules were added alongside Kannada/English. The latest backend validation had 67 tests passing and `compileall` passing; the frontend build passed before the latest backend-only change. Gnani docs list Tamil/Telugu STT/TTS support, but real account access, live recognition, and audio quality still need user-confirmed testing. Preserve the rule that ambiguous requests leave the basket unchanged. Reproduce bugs deterministically, add focused tests (and WebSocket integration tests for server behavior), run relevant validation, and distinguish speech-recognition errors from matcher errors.

### Older prompt from the previous handoff (obsolete; do not use)

> Continue the Multilingual Ordering Kiosk project using `PROJECT_HANDOFF.md` and `README.md`. First inspect the current workspace and verify whether the local backend is running. Do not expose `.env` values or restore Gemini/OpenAI. The last validated backend suite had 47 passing tests and the Vite production build passed. The ten previously identified voice edge-case categories have initial fixes/tests; review the current source and strengthen any incomplete behavior without weakening the rule that ambiguous requests leave the basket unchanged. Reproduce behavior with deterministic tests before changing code, add WebSocket tests for API behavior, run the full backend suite, compile check, and frontend build as relevant, and distinguish real Prisma transcript problems from matcher failures.

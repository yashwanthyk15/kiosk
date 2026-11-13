import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowUpRight,
  Check,
  ChevronRight,
  Keyboard,
  Mic,
  Minus,
  Plus,
  RotateCcw,
  ReceiptText,
  Send,
  ShoppingBag,
  Volume2,
  X,
} from "lucide-react";
import { socketUrl, startSession, voiceUrl } from "./api.js";
import { EXAMPLES, localizeError, SUPPORTED_LANGUAGES, UI_TEXT } from "./locales.js";
import { useMicrophone } from "./useMicrophone.js";

function HighlightedTranscript({ text, terms = [], placeholder }) {
  if (!text) return <span className="transcript-placeholder">{placeholder}</span>;
  const escaped = terms.map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const expression = escaped.length ? new RegExp(`(${escaped.join("|")})`, "giu") : null;
  if (!expression) return <>{text}</>;
  return text.split(expression).map((part, index) =>
    terms.some((term) => term.toLocaleLowerCase() === part.toLocaleLowerCase()) ? (
      <mark key={`${part}-${index}`}>{part}</mark>
    ) : (
      <span key={`${part}-${index}`}>{part}</span>
    ),
  );
}

function KioskGuide({ text, examples, onStart, disabled }) {
  return (
    <div className="start-order-panel kiosk-start-panel">
      <div className="kiosk-guide" aria-label={text.guideTitle}>
        <h3>{text.guideTitle}</h3>
        <div className="kiosk-guide-steps">
          <div className="kiosk-guide-step">
            <span className="kiosk-step-number step-green">1</span>
            <span><b>{text.guideSpeak}</b><small>{text.guideSpeakHelp}</small></span>
          </div>
          <div className="kiosk-guide-step">
            <span className="kiosk-step-number step-orange">2</span>
            <span><b>{text.guideSay}</b><small>{text.guideSayHelp}</small></span>
          </div>
          <div className="kiosk-guide-step">
            <span className="kiosk-step-number step-blue">3</span>
            <span><b>{text.guideCheck}</b><small>{text.guideCheckHelp}</small></span>
          </div>
        </div>
        <div className="kiosk-phrases">
          <b>{text.guideExamples}</b>
          {examples.map((example) => <span key={example.text}>{example.text}</span>)}
        </div>
        <p className="kiosk-type-tip"><Keyboard size={14} /> {text.guideTypeHelp}</p>
      </div>
      <button type="button" onClick={onStart} disabled={disabled}>
        <Mic size={16} /> {text.start}
      </button>
    </div>
  );
}

export default function App() {
  const [game, setGame] = useState(null);
  const [selectedLanguage, setSelectedLanguage] = useState("kn");
  const [socket, setSocket] = useState(null);
  const [draft, setDraft] = useState("");
  const [transcript, setTranscript] = useState("");
  const [matchedTerms, setMatchedTerms] = useState([]);
  const [status, setStatus] = useState("Connecting to the counter…");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [micStarting, setMicStarting] = useState(false);
  const [voiceBusy, setVoiceBusy] = useState(false);
  const [voicePlaying, setVoicePlaying] = useState(false);
  const [visitStarted, setVisitStarted] = useState(false);
  const mic = useMicrophone();
  const socketRef = useRef(null);
  const audioRef = useRef(null);
  const voiceCacheRef = useRef(new Map());
  const visitStartedRef = useRef(false);
  const visitCompleteRef = useRef(false);
  const voiceEnabledRef = useRef(false);
  const languageRef = useRef("kn");
  const captureAfterVoiceRef = useRef(false);
  const captureActiveRef = useRef(false);
  const audioTurnIdRef = useRef(null);
  const micStartTimerRef = useRef(null);
  const micReadyRef = useRef(false);

  const playVoice = useCallback(async (lineKey, lineText) => {
    if (!lineKey || !lineText || !voiceEnabledRef.current) return false;
    setVoiceBusy(true);
    setError("");
    try {
      const cacheKey = `${lineKey}:${lineText}`;
      let audio = voiceCacheRef.current.get(cacheKey);
      if (!audio) {
        audio = new Audio(voiceUrl(lineKey, lineText, languageRef.current));
        audio.preload = "auto";
        audio.dataset.line = lineKey;
        audio.onplay = () => {
          setVoicePlaying(true);
          setVoiceBusy(false);
        };
        audio.onended = () => setVoicePlaying(false);
        audio.onerror = () => {
          setVoicePlaying(false);
          setVoiceBusy(false);
          setError("Couldn't load the counter voice. You can still continue with the text.");
        };
        voiceCacheRef.current.set(cacheKey, audio);
      }
      if (audioRef.current && audioRef.current !== audio) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      }
      audioRef.current = audio;
      audio.currentTime = 0;
      setVoicePlaying(true);
      await new Promise((resolve, reject) => {
        const handleEnded = () => {
          audio.removeEventListener("ended", handleEnded);
          audio.removeEventListener("error", handleError);
          resolve();
        };
        const handleError = () => {
          audio.removeEventListener("ended", handleEnded);
          audio.removeEventListener("error", handleError);
          reject(new Error("Couldn't load the counter voice. You can still continue with the text."));
        };
        audio.addEventListener("ended", handleEnded);
        audio.addEventListener("error", handleError);
        audio.play().catch(handleError);
      });
      return true;
    } catch (reason) {
      setVoicePlaying(false);
      setError(reason.message || "Couldn't play the counter voice.");
      return false;
    } finally {
      setVoiceBusy(false);
    }
  }, []);

  const stopCustomerTurn = useCallback(() => {
    if (!captureActiveRef.current) return;
    captureActiveRef.current = false;
    captureAfterVoiceRef.current = false;
    micReadyRef.current = false;
    setBusy(true);
    setStatus(UI_TEXT[languageRef.current].statusPause);
    mic.stop(() => {
      const connection = socketRef.current;
      if (connection?.readyState === WebSocket.OPEN) {
        connection.send(JSON.stringify({
          type: "stop_audio",
          turn_id: audioTurnIdRef.current,
        }));
      } else {
        setBusy(false);
        setError("The counter connection closed before your words could be sent. Start a new order.");
      }
    });
  }, [mic.stop]);

  const startCapture = useCallback(() => {
    const connection = socketRef.current;
    if (
      !micReadyRef.current ||
      !captureAfterVoiceRef.current ||
      captureActiveRef.current ||
      connection?.readyState !== WebSocket.OPEN
    ) return;
    try {
      mic.beginCapture(
        (frame) => {
          if (connection.readyState === WebSocket.OPEN) connection.send(frame);
        },
        () => setStatus(UI_TEXT[languageRef.current].statusHearing),
        stopCustomerTurn,
      );
      captureActiveRef.current = true;
      setMicStarting(false);
      setStatus(UI_TEXT[languageRef.current].statusListening);
    } catch (reason) {
      mic.stop();
      micReadyRef.current = false;
      captureActiveRef.current = false;
      setMicStarting(false);
      setError(reason.message);
    }
  }, [mic.beginCapture, mic.stop, stopCustomerTurn]);

  const startListening = useCallback(async ({ deferUntilVoiceEnds = false } = {}) => {
    const connection = socketRef.current;
    if (visitCompleteRef.current) return false;
    if (!visitStartedRef.current || !connection || connection.readyState !== WebSocket.OPEN) {
      setError(UI_TEXT[languageRef.current].statusError);
      return false;
    }
    if (!voiceEnabledRef.current) {
      setError(UI_TEXT[languageRef.current].errorMic);
      return false;
    }
    setTranscript("");
    setMatchedTerms([]);
    captureAfterVoiceRef.current = !deferUntilVoiceEnds;
    captureActiveRef.current = false;
    micReadyRef.current = false;
    setError("");
    setMicStarting(true);
    setStatus(UI_TEXT[languageRef.current].statusMicConnect);
    const turnId = crypto.randomUUID();
    audioTurnIdRef.current = turnId;
    try {
      const started = await mic.start(() => {
        if (connection.readyState === WebSocket.OPEN) {
          connection.send(JSON.stringify({ type: "start_audio", turn_id: turnId }));
        }
      });
      if (!started) return false;
      if (!micReadyRef.current) {
        if (micStartTimerRef.current) clearTimeout(micStartTimerRef.current);
        micStartTimerRef.current = window.setTimeout(() => {
          if (micReadyRef.current) return;
          captureAfterVoiceRef.current = false;
          mic.cancelPendingStart();
          mic.stop();
          setMicStarting(false);
          setError("Prisma did not become ready in time. Check the backend connection and try again.");
          setStatus(UI_TEXT[languageRef.current].statusError);
        }, 30000);
      }
      return true;
    } catch (reason) {
      captureAfterVoiceRef.current = false;
      mic.cancelPendingStart();
      setMicStarting(false);
      setError(reason.message);
      setStatus(UI_TEXT[languageRef.current].errorMic);
      return false;
    }
  }, [mic.cancelPendingStart, mic.start, mic.stop]);

  const speakAndListen = useCallback(async (lineKey, lineText) => {
    if (!visitStartedRef.current || !voiceEnabledRef.current) return;
    captureAfterVoiceRef.current = false;
    await playVoice(lineKey, lineText);
    if (visitStartedRef.current && !visitCompleteRef.current) void startListening();
  }, [playVoice, startListening]);

  const begin = useCallback(async (sceneKey = "order", language = languageRef.current) => {
    setError("");
    setBusy(true);
    try {
      socketRef.current?.close();
      socketRef.current = null;
      setSocket(null);
      visitCompleteRef.current = false;
      micReadyRef.current = false;
      captureActiveRef.current = false;
      captureAfterVoiceRef.current = false;
      audioTurnIdRef.current = null;
      mic.stop();
      const session = await startSession(sceneKey, language);
      languageRef.current = session.language || language;
      setSelectedLanguage(languageRef.current);
      voiceEnabledRef.current = Boolean(session.voice_enabled);
      setGame(session);
      setTranscript("");
      setMatchedTerms([]);
      setVisitStarted(false);
      visitStartedRef.current = false;
      setStatus(UI_TEXT[languageRef.current].statusConnected);
      const connection = new WebSocket(socketUrl(session.session_id));
      socketRef.current = connection;
      connection.onopen = () => {
        setSocket(connection);
        setStatus(UI_TEXT[languageRef.current].statusConnected);
      };
      connection.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.type === "error") {
          if (micStartTimerRef.current) clearTimeout(micStartTimerRef.current);
          micStartTimerRef.current = null;
          micReadyRef.current = false;
          captureActiveRef.current = false;
          captureAfterVoiceRef.current = false;
          mic.stop();
          setMicStarting(false);
          setError(localizeError(message.message, languageRef.current));
          if (message.message.includes("Prisma did not detect speech.")) {
            setStatus(UI_TEXT[languageRef.current].statusNotCaught);
            setBusy(false);
            window.setTimeout(() => {
              if (visitStartedRef.current) void startListening();
            }, 900);
            return;
          }
          setStatus(UI_TEXT[languageRef.current].statusConnected);
          setBusy(false);
          return;
        }
        if (message.type === "recording_cancelled") {
          micReadyRef.current = false;
          captureActiveRef.current = false;
          captureAfterVoiceRef.current = false;
          setMicStarting(false);
          return;
        }
        if (message.type === "recording_ready") {
          micReadyRef.current = true;
          if (micStartTimerRef.current) clearTimeout(micStartTimerRef.current);
          micStartTimerRef.current = null;
          setMicStarting(false);
          if (captureAfterVoiceRef.current) startCapture();
          else setStatus(UI_TEXT[languageRef.current].speaking);
          return;
        }
        if (message.type === "live_transcript") {
          setTranscript(message.text);
          return;
        }
        if (message.type === "speech_start") {
          setStatus(UI_TEXT[languageRef.current].statusPrisma);
          return;
        }
        if (message.type === "stt_processing") {
          setStatus(UI_TEXT[languageRef.current].statusTranscribing);
          return;
        }
        if (message.type !== "result") return;
        visitCompleteRef.current = Boolean(message.complete);
        captureActiveRef.current = false;
        captureAfterVoiceRef.current = false;
        micReadyRef.current = false;
        setMicStarting(false);
        setTranscript(message.transcript);
        setMatchedTerms(message.matched_terms || []);
        setGame((current) => ({ ...current, ...message }));
        if (message.language) {
          languageRef.current = message.language;
          setSelectedLanguage(message.language);
        }
        setDraft("");
        if (visitStartedRef.current && voiceEnabledRef.current && !message.replayed) {
          void speakAndListen(message.line_key, message.line);
        }
        const text = UI_TEXT[message.language || languageRef.current];
        setStatus(message.complete
          ? text.orderConfirmed
          : message.order_review
            ? text.statusReview
          : message.quantity_limit_exceeded
            ? text.statusLimit
          : message.clarification_required
            ? text.statusClarify
          : message.language_changed
            ? text.statusConnected
          : message.order_updated
            ? text.statusBasket
          : message.matched
            ? text.statusBasket
            : text.statusRetry);
        setBusy(false);
      };
      connection.onerror = () => {
        if (socketRef.current !== connection) return;
        if (micStartTimerRef.current) clearTimeout(micStartTimerRef.current);
        micStartTimerRef.current = null;
        micReadyRef.current = false;
        captureActiveRef.current = false;
        captureAfterVoiceRef.current = false;
        mic.stop();
        setMicStarting(false);
        setError(UI_TEXT[languageRef.current].statusError);
        setStatus(UI_TEXT[languageRef.current].statusError);
        setBusy(false);
      };
      connection.onclose = () => {
        if (socketRef.current !== connection) return;
        if (micStartTimerRef.current) clearTimeout(micStartTimerRef.current);
        micStartTimerRef.current = null;
        micReadyRef.current = false;
        captureActiveRef.current = false;
        captureAfterVoiceRef.current = false;
        setSocket((current) => current === connection ? null : current);
        setMicStarting(false);
        setBusy(false);
        mic.stop();
        setStatus(UI_TEXT[languageRef.current].statusError);
      };
    } catch (reason) {
      setError(reason.message);
    } finally {
      setBusy(false);
    }
  }, [mic.stop, speakAndListen, startCapture, startListening]);

  useEffect(() => {
    begin();
    return () => {
      if (micStartTimerRef.current) clearTimeout(micStartTimerRef.current);
      socketRef.current?.close();
    };
  }, [begin]);

  function stopListeningForInteraction() {
    if (!mic.recording && !micStarting) return;
    mic.cancelPendingStart();
    mic.stop();
    micReadyRef.current = false;
    captureActiveRef.current = false;
    captureAfterVoiceRef.current = false;
    setMicStarting(false);
    if (micStartTimerRef.current) clearTimeout(micStartTimerRef.current);
    micStartTimerRef.current = null;
    const connection = socketRef.current;
    if (connection?.readyState === WebSocket.OPEN) {
      connection.send(JSON.stringify({ type: "cancel_audio" }));
    }
  }

  function sendText(text = draft) {
    const clean = text.trim();
    if (!clean || !socket || socket.readyState !== WebSocket.OPEN || busy || game?.complete) return;
    stopListeningForInteraction();
    setError("");
    setBusy(true);
    setStatus(UI_TEXT[languageRef.current].statusSending);
    socket.send(JSON.stringify({
      type: "transcript",
      turn_id: crypto.randomUUID(),
      text: clean,
    }));
  }

  function startOrdering() {
    if (visitStartedRef.current || !socket || socket.readyState !== WebSocket.OPEN) return;
    visitStartedRef.current = true;
    setVisitStarted(true);
    if (!voiceEnabledRef.current) {
      setStatus(UI_TEXT[languageRef.current].statusSpeechUnavailable);
      return;
    }
    void startListening({ deferUntilVoiceEnds: true });
    void playVoice(game?.line_key || "greeting", game?.line).then(() => {
      if (!visitStartedRef.current) return;
      captureAfterVoiceRef.current = true;
      startCapture();
    });
  }

  function startNewOrder() {
    visitStartedRef.current = false;
    visitCompleteRef.current = false;
    setVisitStarted(false);
    captureAfterVoiceRef.current = false;
    captureActiveRef.current = false;
    void begin("order", languageRef.current);
  }

  function changeLanguage(language) {
    if (!SUPPORTED_LANGUAGES.some((option) => option.code === language)) return;
    if (socket?.readyState === WebSocket.OPEN) {
      languageRef.current = language;
      setSelectedLanguage(language);
      if (game?.language === language) return;
      setBusy(true);
      setError("");
      socket.send(JSON.stringify({ type: "set_language", language }));
      return;
    }
    if (!game) {
      languageRef.current = language;
      setSelectedLanguage(language);
      void begin("order", language);
      return;
    }
    languageRef.current = game.language || "kn";
    setSelectedLanguage(languageRef.current);
    setError(UI_TEXT[languageRef.current].statusError);
  }

  function sendControl(event) {
    if (!socket || socket.readyState !== WebSocket.OPEN || busy || game?.complete) return;
    stopListeningForInteraction();
    setError("");
    setBusy(true);
    setStatus(UI_TEXT[languageRef.current].statusUpdating);
    socket.send(JSON.stringify(event));
  }

  const ordered = game?.complete;
  const menu = game?.menu || [];
  const basketItems = game?.scene?.goal_items || [];
  const text = UI_TEXT[selectedLanguage];
  const examples = EXAMPLES[selectedLanguage];
  const controlsDisabled = !visitStarted || busy || voiceBusy || voicePlaying || ordered;

  return (
    <main className="app-shell" lang={{ kn: "kn", ta: "ta", te: "te" }[selectedLanguage]}>
      <header className="topbar">
        <a className="brand" href="/" aria-label="Multilingual Ordering Kiosk home">
          <span className="brand-mark"><ShoppingBag size={16} aria-hidden="true" /></span>
          <span>Order<span className="brand-light">kiosk</span></span>
        </a>
        <div className="topbar-right">
          <span className="lesson-pill"><span className="pulse-dot" /> {text.lesson}</span>
          <label className="language-picker">
            <span>{text.language}</span>
            <select
              aria-label={text.language}
              value={selectedLanguage}
              disabled={busy || mic.recording || micStarting || voiceBusy || voicePlaying}
              onChange={(event) => changeLanguage(event.target.value)}
            >
              {SUPPORTED_LANGUAGES.map((option) => (
                <option key={option.code} value={option.code}>{option.label}</option>
              ))}
            </select>
          </label>
          <button className="help-button" aria-label={text.help} title={text.help}>?</button>
        </div>
      </header>

      <div className="page-content">
        <div className="breadcrumb"><span>{text.service}</span><ChevronRight size={13} /><span>{text.lesson}</span><ChevronRight size={13} /><b>{text.menu}</b></div>
        <section className="intro-row">
          <div>
            <div className="eyebrow"><span className="eyebrow-line" /> {text.eyebrow}</div>
            <h1>{text.headline}<br /><em>{text.headlineAccent}</em></h1>
            <p className="intro-copy">{text.intro}</p>
          </div>
          <div className="round-card">
            <span className="round-icon"><ShoppingBag size={16} /></span>
            <span><b>{text.checkout}</b><small>{text.steps}</small></span>
          </div>
        </section>

        <section className="game-layout">
          <div className="scene-column">
            <div className="scene" aria-label={text.sceneLabel}>
              <div className="scene-sun" />
              <div className="scene-window">
                <span className="window-caption">{text.hotFresh}</span>
                <div className="window-shelf" />
                <div className="steam steam-one" /><div className="steam steam-two" />
                <div className="idli-tray"><span /><span /><span /></div>
              </div>
              <div className="scene-wall-line" />
              <div className="counter-person">
                <div className="person-hair" />
                <div className="person-head"><span className="person-eye" /><span className="person-smile" /></div>
                <div className="person-neck" />
                <div className="person-body"><span className="shirt-collar" /><span className="shirt-button" /></div>
                <div className="person-arm" />
              </div>
              <div className="counter-top" />
              <div className="counter-front"><span className="counter-stripe" /><span className="counter-label">ದರ್ಶಿನಿ</span></div>
              <div className="coffee-cup"><span className="cup-steam" /><span className="cup-handle" /></div>
              <div className="scene-floor" />
              <div className="scene-caption"><span className="scene-live"><i /> {text.open}</span><span>ಬೆಂಗಳೂರು · ದರ್ಶಿನಿ</span></div>
              <div className="speech-bubble">{game?.line || text.greeting}<i /></div>
              <span className="sun-sparkle sparkle-one">✳</span><span className="sun-sparkle sparkle-two">✳</span>
            </div>
            <div className="character-card">
              <div className="avatar">ಶ್ರೀ</div>
              <div className="character-copy"><b>{text.character}</b><span>{text.characterHelp}</span></div>
              <span className="character-status"><i /> {text.ready}</span>
            </div>
          </div>

          <div className="order-column">
            {selectedLanguage === "kn" && !visitStarted && (
              <KioskGuide
                text={text}
                examples={examples}
                onStart={startOrdering}
                disabled={!game || busy || !socket || socket.readyState !== WebSocket.OPEN}
              />
            )}
            <div className="goal-card">
              <div className="goal-head">
                <div><span className="section-label">{ordered ? text.orderComplete : game?.reviewing ? text.confirmCheck : text.basketPrices}</span><h2>{ordered ? text.thanks : game?.reviewing ? text.reviewOrder : text.buildOrder}</h2></div>
                <span className="goal-stamp">{ordered ? <Check size={17} /> : <ShoppingBag size={17} />}</span>
              </div>
              {!ordered && <p className="goal-hint">{text.basketHint}</p>}

              {ordered && game?.bill ? (
                <div className="bill-receipt">
                  <div className="bill-heading"><ReceiptText size={15} /><b>{text.receipt}</b><span>₹ INR</span></div>
                  <div className="bill-table-head"><span>{text.item}</span><span>{text.qty}</span><span>{text.rate}</span><span>{text.amount}</span></div>
                  {game.bill.items.map((item) => (
                    <div className="bill-line" key={item.key}>
                      <span>{item.title}</span><span>{item.quantity}</span><span>₹{item.unit_price}</span><b>₹{item.line_total}</b>
                    </div>
                  ))}
                  <div className="bill-total"><span>{text.total}</span><b>₹{game.bill.total}</b></div>
                  <p>{text.samplePrices}</p>
                  <button className="order-action-button" type="button" onClick={startNewOrder} disabled={busy}><RotateCcw size={14} /> {text.newOrder}</button>
                </div>
              ) : (
                <div className="menu-selector">
                  <section className="basket-panel" aria-label={text.basketLabel}>
                    <div className="spoken-order-heading"><b><ShoppingBag size={13} /> {text.yourOrder}</b><span>{basketItems.length} {basketItems.length === 1 ? text.itemOne : text.itemMany}</span></div>
                    {basketItems.length ? (
                      <div className="basket-items">
                        {basketItems.map((item) => (
                          <div className="basket-item" key={item.key}>
                            <span className="basket-item-copy"><b>{item.localized_title || item.title}</b><small>₹{item.price} {text.each}</small></span>
                            <button type="button" aria-label={`${text.back}: ${item.localized_title || item.title}`} disabled={controlsDisabled} onClick={() => sendControl({ type: "adjust_item", key: item.key, delta: -1 })}><Minus size={13} /></button>
                            <span className="basket-quantity">{item.quantity}</span>
                            <button type="button" aria-label={`${text.yourOrder}: ${item.localized_title || item.title}`} disabled={controlsDisabled || item.quantity >= 10} onClick={() => sendControl({ type: "adjust_item", key: item.key, delta: 1 })}><Plus size={13} /></button>
                            <b className="basket-line-total">₹{item.line_total}</b>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="empty-basket">{text.emptyBasket}</p>
                    )}
                    <div className="order-subtotal"><span>{text.subtotal}</span><b>₹{game?.scene?.order_total ?? 0}</b></div>
                  </section>

                  {!game?.reviewing && (
                    <>
                      <div className="menu-list-heading">
                        <span>{text.menu} <small>{text.menuPrices}</small></span>
                        <span>{text.upTo}</span>
                      </div>
                      <div className="menu-list">
                        {menu.map((item) => {
                          const quantity = game?.order?.[item.key] || 0;
                          return (
                            <div className={`menu-row ${quantity ? "selected" : ""}`} key={item.key}>
                              <span className="menu-item-copy">
                                <b>{item.localized_title || item.title}</b>
                                {selectedLanguage !== "kn" && <small>{item.kannada} · {item.romanization}</small>}
                              </span>
                              <span className="menu-item-price">₹{item.price}</span>
                              <span className="menu-quantity-controls">
                                {quantity > 0 && <button type="button" aria-label={`${text.removeOne} ${item.localized_title || item.title}`} disabled={controlsDisabled} onClick={() => sendControl({ type: "adjust_item", key: item.key, delta: -1 })}><Minus size={12} /></button>}
                                <span>{quantity || "—"}</span>
                                <button type="button" aria-label={`${text.addOne} ${item.localized_title || item.title}`} disabled={controlsDisabled || quantity >= 10} onClick={() => sendControl({ type: "adjust_item", key: item.key, delta: 1 })}><Plus size={12} /></button>
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </>
                  )}

                  {game?.reviewing ? (
                    <div className="checkout-actions">
                      <p>{text.confirmPrompt}</p>
                      <button className="order-action-button" type="button" disabled={controlsDisabled} onClick={() => sendControl({ type: "confirm_order" })}><Check size={14} /> {text.confirm} · ₹{game?.scene?.order_total ?? 0}</button>
                      <button className="secondary-order-button" type="button" disabled={controlsDisabled} onClick={() => sendControl({ type: "cancel_review" })}>{text.back}</button>
                    </div>
                  ) : (
                    <button className="order-action-button" type="button" disabled={controlsDisabled || !basketItems.length} onClick={() => sendControl({ type: "review_order" })}>{text.review} <ArrowUpRight size={14} /></button>
                  )}
                  {transcript && game?.matched === false && (
                    <div className="order-match-feedback" role="status">
                      <b>{text.noItem}</b>
                      <small>{text.examplesHint}</small>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="conversation-card">
              <div className="conversation-head"><span className="section-label">{text.assistant}</span></div>
              <div className="character-line"><div className="tiny-avatar">ಶ್ರೀ</div><div><span className="speaker-name">{text.speaker} <i>{text.counter}</i></span><p>{game?.line || text.greeting}</p>{selectedLanguage !== "kn" && <small>{game?.line_english || "Namaskara! What would you like to order?"}</small>}</div></div>
              {!visitStarted && selectedLanguage !== "kn" && (
                <div className="start-order-panel">
                  <p>{text.startHelp}</p>
                  <button type="button" onClick={startOrdering} disabled={!game || busy || !socket || socket.readyState !== WebSocket.OPEN}>
                    <Mic size={16} /> {text.start}
                  </button>
                </div>
              )}
              <div className={`transcript-box ${transcript ? "has-transcript" : ""}`}>
                <span className="transcript-label">{text.transcript}</span>
                <p lang={{ kn: "kn-IN", ta: "ta-IN", te: "te-IN" }[selectedLanguage]}>
                  {mic.recording && !transcript
                    ? <span className="transcript-placeholder">{text.listenPrompt}</span>
                    : <HighlightedTranscript text={transcript} terms={matchedTerms} placeholder={text.listenPrompt} />}
                </p>
                {mic.recording && (
                  <div className="voice-waveform" role="img" aria-label={text.recording}>
                    {Array.from({ length: 25 }, (_, index) => <i key={index} style={{ "--bar-index": index }} />)}
                    <span>{text.recording}</span>
                  </div>
                )}
                {transcript && <span className={`transcript-status ${game?.matched ? "success" : "retry"}`}>{game?.matched ? game?.complete ? text.orderConfirmed : game?.order_updated ? text.basketUpdated : text.understood : text.notUnderstood}</span>}
              </div>
              <div className="turn-status"><span className={busy || mic.recording || micStarting || voicePlaying ? "status-dot thinking" : "status-dot"} />{!visitStarted ? text.statusReady : voicePlaying ? text.speaking : mic.recording ? text.listeningStatus : status}</div>
              {error && <div className="error-message"><X size={14} />{error}</div>}
              {visitStarted && !ordered && <div className={`automatic-turn ${mic.recording ? "listening" : voicePlaying ? "speaking" : ""}`} role="status"><span className="automatic-turn-dot" />{mic.recording ? text.automaticListening : voicePlaying ? text.automaticSpeaking : micStarting ? text.preparing : busy ? text.processing : text.readyForOrder}</div>}
              {visitStarted && !ordered && error && game?.speech_enabled && !mic.recording && !micStarting && !voicePlaying && (
                <button className="retry-listening" type="button" onClick={() => void startListening()} disabled={busy}>{text.retryListening}</button>
              )}
              <div className="text-order">
                <form onSubmit={(event) => { event.preventDefault(); sendText(); }}>
                  <input value={draft} onChange={(event) => setDraft(event.target.value)} placeholder={text.placeholder} aria-label={text.typeOrder} disabled={!visitStarted || busy || ordered || voiceBusy || voicePlaying} />
                  <button type="submit" aria-label={text.sendOrder} disabled={!visitStarted || !draft.trim() || busy || ordered || voiceBusy || voicePlaying}><Send size={15} /></button>
                </form>
                <div className="example-row"><span>{text.try}</span>{examples.map((example) => <button key={example.text} onClick={() => sendText(example.text)} disabled={!visitStarted || busy || ordered || voiceBusy || voicePlaying} title={example.text}>{example.label}<ArrowUpRight size={11} /></button>)}</div>
              </div>
              {game?.hint && !ordered && <div className="hint-card">{game.hint}</div>}
              <div className="conversation-foot"><span><span className="lock-dot" /> {text.noAccount}</span><span>{text.madeFor} <span className="heart">♥</span></span></div>
            </div>
          </div>
        </section>

        <footer className="page-footer"><span>{text.footer}</span><span>{text.footerBrand}</span></footer>
      </div>
    </main>
  );
}

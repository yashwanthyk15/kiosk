import { useCallback, useEffect, useRef, useState } from "react";

const SAMPLE_RATE = 16000;
const SAMPLES_PER_FRAME = 512;
const SPEECH_RMS_THRESHOLD = 0.015;
const SILENCE_FRAMES_TO_STOP = 44;

function toPcmFrame(samples) {
  const frame = new ArrayBuffer(SAMPLES_PER_FRAME * 2);
  const view = new DataView(frame);
  for (let index = 0; index < SAMPLES_PER_FRAME; index += 1) {
    const sample = Math.max(-1, Math.min(1, samples[index]));
    view.setInt16(index * 2, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
  }
  return frame;
}

export function useMicrophone() {
  const [recording, setRecording] = useState(false);
  const streamRef = useRef(null);
  const contextRef = useRef(null);
  const sourceRef = useRef(null);
  const processorRef = useRef(null);
  const silentGainRef = useRef(null);
  const startAttemptRef = useRef(0);

  const start = useCallback(async (onStarted) => {
    if (!navigator.mediaDevices?.getUserMedia || !window.AudioContext) {
      throw new Error("This browser does not support microphone recording.");
    }

    const attempt = ++startAttemptRef.current;
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
    } catch (error) {
      if (error.name === "NotAllowedError" || error.name === "SecurityError") {
        throw new Error("Microphone access is blocked for this page. Allow microphone access for 127.0.0.1 in your browser's site settings, then refresh.");
      }
      if (error.name === "NotFoundError" || error.name === "DevicesNotFoundError") {
        throw new Error("No microphone was found. Connect a microphone and try again.");
      }
      if (error.name === "NotReadableError" || error.name === "TrackStartError") {
        throw new Error("The microphone is busy in another app. Close apps using it and try again.");
      }
      throw new Error(`Could not access the microphone: ${error.message}`);
    }
    if (attempt !== startAttemptRef.current) {
      stream.getTracks().forEach((track) => track.stop());
      return false;
    }

    let context;
    try {
      context = new AudioContext({ sampleRate: SAMPLE_RATE });
      await context.resume();
      if (context.sampleRate !== SAMPLE_RATE) {
        throw new Error(`Your browser supplied ${context.sampleRate} Hz audio; 16 kHz is required for live Prisma streaming.`);
      }

      const source = context.createMediaStreamSource(stream);
      const processor = context.createScriptProcessor(SAMPLES_PER_FRAME, 1, 1);
      const silentGain = context.createGain();
      silentGain.gain.value = 0;

      streamRef.current = stream;
      contextRef.current = context;
      sourceRef.current = source;
      processorRef.current = processor;
      silentGainRef.current = silentGain;

      onStarted();
      return true;
    } catch (error) {
      stream.getTracks().forEach((track) => track.stop());
      if (context && context.state !== "closed") await context.close();
      throw error;
    }
  }, []);

  const beginCapture = useCallback((onFrame, onSpeechStart, onSilence) => {
    if (!sourceRef.current || !processorRef.current || !silentGainRef.current) {
      throw new Error("Microphone is not ready to record.");
    }
    let speechDetected = false;
    let silenceFrames = 0;
    let silenceHandled = false;
    processorRef.current.onaudioprocess = (event) => {
      const samples = event.inputBuffer.getChannelData(0);
      onFrame(toPcmFrame(samples));
      const squareSum = samples.reduce((sum, sample) => sum + sample * sample, 0);
      const rms = Math.sqrt(squareSum / samples.length);
      if (rms >= SPEECH_RMS_THRESHOLD) {
        silenceFrames = 0;
        if (!speechDetected) {
          speechDetected = true;
          onSpeechStart?.();
        }
      } else if (speechDetected && !silenceHandled) {
        silenceFrames += 1;
        if (silenceFrames >= SILENCE_FRAMES_TO_STOP) {
          silenceHandled = true;
          onSilence?.();
        }
      }
    };
    sourceRef.current.connect(processorRef.current);
    processorRef.current.connect(silentGainRef.current);
    silentGainRef.current.connect(contextRef.current.destination);
    setRecording(true);
  }, []);

  const cancelPendingStart = useCallback(() => {
    startAttemptRef.current += 1;
  }, []);

  const stop = useCallback((onStopped) => {
    startAttemptRef.current += 1;
    processorRef.current?.disconnect();
    silentGainRef.current?.disconnect();
    sourceRef.current?.disconnect();
    streamRef.current?.getTracks().forEach((track) => track.stop());
    if (contextRef.current && contextRef.current.state !== "closed") {
      void contextRef.current.close();
    }
    processorRef.current = null;
    silentGainRef.current = null;
    sourceRef.current = null;
    streamRef.current = null;
    contextRef.current = null;
    setRecording(false);
    onStopped?.();
  }, []);

  useEffect(() => () => {
    processorRef.current?.disconnect();
    silentGainRef.current?.disconnect();
    sourceRef.current?.disconnect();
    streamRef.current?.getTracks().forEach((track) => track.stop());
    if (contextRef.current && contextRef.current.state !== "closed") {
      void contextRef.current.close();
    }
  }, []);

  return { recording, start, beginCapture, cancelPendingStart, stop };
}

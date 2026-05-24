'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

// ── Minimal Web Speech API types ──────────────────────────────────────────
// TypeScript's DOM lib doesn't ship SpeechRecognition types (it's not in the
// official spec), so we declare just the slice we use.
interface SpeechRecognitionResultLike {
  readonly isFinal: boolean;
  readonly length: number;
  [index: number]: { readonly transcript: string };
}

interface SpeechRecognitionEventLike extends Event {
  readonly resultIndex: number;
  readonly results: {
    readonly length: number;
    [index: number]: SpeechRecognitionResultLike;
  };
}

interface SpeechRecognitionErrorEventLike extends Event {
  readonly error: string;
}

interface SpeechRecognitionLike extends EventTarget {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start(): void;
  stop(): void;
  abort(): void;
  onresult: ((e: SpeechRecognitionEventLike) => void) | null;
  onerror: ((e: SpeechRecognitionErrorEventLike) => void) | null;
  onend: (() => void) | null;
}

type SpeechRecognitionCtor = new () => SpeechRecognitionLike;

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionCtor;
    webkitSpeechRecognition?: SpeechRecognitionCtor;
  }
}

type Callbacks = {
  /** Live, not-yet-final transcript chunk. */
  onInterim?: (text: string) => void;
  /** Finalized transcript chunk (committed by the engine). */
  onFinal?: (text: string) => void;
};

/**
 * Wraps the browser Web Speech API for live speech-to-text dictation.
 *
 * The caller controls how transcript merges into its own input via the
 * `onInterim`/`onFinal` callbacks — this hook just streams text out. The mic
 * is free and runs in-browser (no backend, no quota). Unsupported browsers
 * (e.g. Firefox) report `isSupported === false` so the UI can hide the mic.
 */
export function useSpeechInput({ onInterim, onFinal }: Callbacks = {}) {
  const [isSupported, setIsSupported] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  // Keep the latest callbacks in refs so the recognition instance (created
  // once) always calls through to the current closure without re-binding.
  const onInterimRef = useRef(onInterim);
  const onFinalRef = useRef(onFinal);
  onInterimRef.current = onInterim;
  onFinalRef.current = onFinal;

  useEffect(() => {
    const SR =
      typeof window !== 'undefined'
        ? window.SpeechRecognition || window.webkitSpeechRecognition
        : undefined;
    if (!SR) {
      setIsSupported(false);
      return;
    }
    setIsSupported(true);

    const recognition = new SR();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang =
      (typeof navigator !== 'undefined' && navigator.language) || 'en-US';

    recognition.onresult = (e) => {
      let interim = '';
      let final = '';
      for (let i = e.resultIndex; i < e.results.length; i += 1) {
        const result = e.results[i];
        const transcript = result[0]?.transcript ?? '';
        if (result.isFinal) final += transcript;
        else interim += transcript;
      }
      if (final) onFinalRef.current?.(final);
      if (interim) onInterimRef.current?.(interim);
    };

    recognition.onerror = (e) => {
      // `not-allowed`/`service-not-allowed` → the user denied mic permission.
      if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
        setError('Microphone permission denied.');
      } else if (e.error !== 'aborted' && e.error !== 'no-speech') {
        setError('Voice input hit a snag. Try again.');
      }
      setIsListening(false);
    };

    recognition.onend = () => setIsListening(false);

    recognitionRef.current = recognition;

    return () => {
      recognition.onresult = null;
      recognition.onerror = null;
      recognition.onend = null;
      try {
        recognition.abort();
      } catch {
        // ignore — already stopped/teardown
      }
      recognitionRef.current = null;
    };
  }, []);

  const start = useCallback(() => {
    const recognition = recognitionRef.current;
    if (!recognition || isListening) return;
    setError(null);
    try {
      recognition.start();
      setIsListening(true);
    } catch {
      // start() throws if called while already started — treat as listening.
      setIsListening(true);
    }
  }, [isListening]);

  const stop = useCallback(() => {
    const recognition = recognitionRef.current;
    if (!recognition) return;
    try {
      recognition.stop();
    } catch {
      // ignore
    }
    setIsListening(false);
  }, []);

  return { isSupported, isListening, start, stop, error };
}

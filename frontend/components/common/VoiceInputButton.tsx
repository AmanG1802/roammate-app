'use client';

import { useCallback, useEffect, useRef } from 'react';
import { Mic } from 'lucide-react';
import { motion, useReducedMotion } from 'framer-motion';
import clsx from 'clsx';
import { twMerge } from 'tailwind-merge';
import { useSpeechInput } from '@/hooks/useSpeechInput';

type Props = {
  /** Current input value the transcript is dictated into. */
  value: string;
  /** Called with the merged value (base + transcript) as the user speaks. */
  onChange: (value: string) => void;
  disabled?: boolean;
  className?: string;
};

/** Join a base string with new dictated text, inserting a space if needed. */
function merge(base: string, addition: string): string {
  if (!base) return addition;
  if (/\s$/.test(base)) return base + addition;
  return `${base} ${addition}`;
}

/**
 * Mic button for live speech-to-text dictation into a text input. Shared by
 * all three AI chats. Renders nothing where the Web Speech API is unsupported
 * (e.g. Firefox), so callers can drop it in unconditionally.
 *
 * Behaviour is fill-the-box: on start it snapshots the current `value` as a
 * base, then streams `onChange(base + transcript)` so the user can edit before
 * sending. No auto-send.
 */
export default function VoiceInputButton({ value, onChange, disabled, className }: Props) {
  const reduceMotion = useReducedMotion();

  // Snapshot of `value` when listening began, plus finalized chunks accumulated
  // during this session. Interim chunks are layered on top transiently.
  const baseRef = useRef('');
  const finalRef = useRef('');

  const { isSupported, isListening, start, stop } = useSpeechInput({
    onFinal: (text) => {
      finalRef.current = merge(finalRef.current, text.trim());
      onChange(merge(baseRef.current, finalRef.current));
    },
    onInterim: (text) => {
      const committed = merge(baseRef.current, finalRef.current);
      onChange(merge(committed, text.trim()));
    },
  });

  // Stop recording if the parent disables the mic mid-session (e.g. the
  // message was sent and the input cleared) so we don't restore stale text.
  useEffect(() => {
    if (disabled && isListening) stop();
  }, [disabled, isListening, stop]);

  const toggle = useCallback(() => {
    if (isListening) {
      stop();
      // Drop any dangling interim text — commit base + finalized only.
      onChange(merge(baseRef.current, finalRef.current));
      return;
    }
    baseRef.current = value;
    finalRef.current = '';
    start();
  }, [isListening, stop, start, value, onChange]);

  if (!isSupported) return null;

  return (
    <button
      type="button"
      onClick={toggle}
      disabled={disabled}
      aria-label={isListening ? 'Stop voice input' : 'Start voice input'}
      aria-pressed={isListening}
      className={twMerge(
        clsx(
          'relative shrink-0 flex items-center justify-center rounded-xl p-2.5 transition-colors disabled:opacity-40 disabled:cursor-not-allowed',
          isListening
            ? 'bg-rose-500 text-white'
            : 'text-slate-400 hover:text-indigo-600',
          className,
        ),
      )}
    >
      {/* Pulsing ring while recording (gated behind reduced-motion). */}
      {isListening && !reduceMotion && (
        <motion.span
          aria-hidden
          className="absolute inset-0 rounded-xl bg-rose-500"
          initial={{ opacity: 0.5, scale: 1 }}
          animate={{ opacity: 0, scale: 1.6 }}
          transition={{ duration: 1.4, repeat: Infinity, ease: 'easeOut' }}
        />
      )}
      <Mic className="relative w-4 h-4" />
    </button>
  );
}

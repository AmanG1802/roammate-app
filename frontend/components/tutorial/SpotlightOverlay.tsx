'use client';

import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Info, Sparkles, X } from 'lucide-react';

type TargetRect = { x: number; y: number; width: number; height: number };

const PADDING = 10;
const POPOVER_GAP = 16;
const POPOVER_WIDTH = 360;

export type SpotlightOverlayProps = {
  open: boolean;
  targetSelector?: string;
  title: string;
  body: string;
  stepIndex: number; // 0-based
  totalSteps: number;
  onPrev?: () => void;
  onNext: () => void;
  onSkip: () => void;
  isLast?: boolean;
  /** Hide the Next button entirely — for steps that wait on an external
   *  signal to advance (e.g. preview shown, Create-trip clicked). */
  hideNext?: boolean;
  tryIt?: { label: string; onClick: () => void; loading?: boolean };
};

// Render a step body, swapping the `{info}` token for the inline tooltip
// (info) icon so copy can reference the in-app control by its glyph.
function renderBody(body: string): React.ReactNode {
  if (!body.includes('{info}')) return body;
  const parts = body.split('{info}');
  return parts.map((part, i) => (
    <span key={i}>
      {part}
      {i < parts.length - 1 && (
        <Info
          size={14}
          className="inline-block align-text-bottom mx-0.5 text-indigo-600"
          aria-label="info"
        />
      )}
    </span>
  ));
}

export default function SpotlightOverlay({
  open,
  targetSelector,
  title,
  body,
  stepIndex,
  totalSteps,
  onPrev,
  onNext,
  onSkip,
  isLast,
  hideNext,
  tryIt,
}: SpotlightOverlayProps) {
  const [mounted, setMounted] = useState(false);
  const [rect, setRect] = useState<TargetRect | null>(null);
  // True once we've given up waiting for a target that never appears — fall back
  // to a centred popover so the tour can never get stuck on a blank scrim.
  const [fallback, setFallback] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => setMounted(true), []);

  // Track the target element. On every step (selector) change we clear the old
  // rect first so the spotlight never animates across the screen from the
  // previous target — it simply appears on the new one once measured. We also
  // wait for the element to exist (it may still be navigating/mounting) and
  // re-measure on scroll / resize / DOM mutation.
  useLayoutEffect(() => {
    setRect(null);
    setFallback(false);
    if (!open || !targetSelector) return;

    let raf = 0;
    let scrolled = false;
    const measure = () => {
      const el = document.querySelector(targetSelector) as HTMLElement | null;
      if (!el) {
        setRect(null);
        return;
      }
      const r = el.getBoundingClientRect();
      // Scroll an offscreen target into view once, then let the next ticks
      // re-measure its settled position before we reveal the spotlight.
      if (!scrolled && (r.top < 0 || r.bottom > window.innerHeight)) {
        scrolled = true;
        el.scrollIntoView({ block: 'center', behavior: 'smooth' });
        return;
      }
      if (r.width === 0 && r.height === 0) return; // not laid out yet
      setRect({ x: r.left, y: r.top, width: r.width, height: r.height });
    };
    const onTick = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(measure);
    };
    measure();
    window.addEventListener('scroll', onTick, true);
    window.addEventListener('resize', onTick);
    const obs = new MutationObserver(onTick);
    obs.observe(document.body, { subtree: true, childList: true, attributes: true });
    const id = window.setInterval(measure, 300); // safety net while page loads
    // If the target never resolves (e.g. a section that won't render), reveal a
    // centred popover after a short grace period rather than dimming forever.
    const fallbackTimer = window.setTimeout(() => setFallback(true), 2500);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('scroll', onTick, true);
      window.removeEventListener('resize', onTick);
      obs.disconnect();
      window.clearInterval(id);
      window.clearTimeout(fallbackTimer);
    };
  }, [open, targetSelector]);

  // ESC = skip, ←/→ = prev/next.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onSkip();
      } else if (e.key === 'ArrowRight') {
        onNext();
      } else if (e.key === 'ArrowLeft' && onPrev) {
        onPrev();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onNext, onPrev, onSkip]);

  if (!mounted || !open) return null;

  const vw = typeof window !== 'undefined' ? window.innerWidth : 1280;
  const vh = typeof window !== 'undefined' ? window.innerHeight : 800;

  // Hold the popover (and ring) back until the target is measured, so each
  // popup lands directly on its element rather than flashing centre-screen
  // first. Targetless steps and the fallback path show immediately/centred.
  const popoverVisible = !targetSelector || !!rect || fallback;

  // Cutout rect (padded). When no rect, center popover on screen.
  const cutout = rect
    ? {
        x: Math.max(0, rect.x - PADDING),
        y: Math.max(0, rect.y - PADDING),
        width: Math.min(vw, rect.width + PADDING * 2),
        height: Math.min(vh, rect.height + PADDING * 2),
      }
    : null;

  // Popover position: prefer right of the target, then left, then below, else
  // above/clamped. Left placement keeps right-edge targets (the brainstorm bin,
  // the Concierge panel) from being covered by the popover.
  let popoverStyle: React.CSSProperties;
  if (cutout) {
    const fitsRight = cutout.x + cutout.width + POPOVER_GAP + POPOVER_WIDTH < vw - 16;
    const fitsLeft = cutout.x - POPOVER_GAP - POPOVER_WIDTH > 16;
    const fitsBelow = cutout.y + cutout.height + POPOVER_GAP + 220 < vh - 16;
    if (fitsRight) {
      popoverStyle = {
        left: cutout.x + cutout.width + POPOVER_GAP,
        top: Math.min(cutout.y, vh - 280),
        width: POPOVER_WIDTH,
      };
    } else if (fitsLeft) {
      popoverStyle = {
        left: cutout.x - POPOVER_GAP - POPOVER_WIDTH,
        top: Math.min(cutout.y, vh - 280),
        width: POPOVER_WIDTH,
      };
    } else if (fitsBelow) {
      popoverStyle = {
        left: Math.min(cutout.x, vw - POPOVER_WIDTH - 16),
        top: cutout.y + cutout.height + POPOVER_GAP,
        width: POPOVER_WIDTH,
      };
    } else {
      popoverStyle = {
        left: Math.max(16, Math.min(cutout.x, vw - POPOVER_WIDTH - 16)),
        top: Math.max(16, cutout.y - POPOVER_GAP - 240),
        width: POPOVER_WIDTH,
      };
    }
  } else {
    popoverStyle = {
      left: (vw - POPOVER_WIDTH) / 2,
      top: vh / 2 - 140,
      width: POPOVER_WIDTH,
    };
  }

  const node = (
    <AnimatePresence>
      {open && (
        <motion.div
          key="tutorial-overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
          className="fixed inset-0 z-[100] pointer-events-none"
          aria-modal="true"
          role="dialog"
          aria-label="Roammate guided tour"
        >
          {/* SVG mask scrim with rounded cutout. pointer-events: none so the
              spotlighted target underneath is interactive. */}
          <svg width={vw} height={vh} className="absolute inset-0" style={{ pointerEvents: 'none' }}>
            <defs>
              <mask id="tutorial-mask">
                <rect width="100%" height="100%" fill="white" />
                {cutout && (
                  <motion.rect
                    initial={false}
                    animate={{
                      x: cutout.x,
                      y: cutout.y,
                      width: cutout.width,
                      height: cutout.height,
                    }}
                    transition={{ type: 'spring', stiffness: 280, damping: 30 }}
                    rx={14}
                    ry={14}
                    fill="black"
                  />
                )}
              </mask>
            </defs>
            <rect
              width="100%"
              height="100%"
              fill="rgba(15, 23, 42, 0.62)"
              mask="url(#tutorial-mask)"
            />
            {cutout && (
              <motion.rect
                initial={false}
                animate={{
                  x: cutout.x,
                  y: cutout.y,
                  width: cutout.width,
                  height: cutout.height,
                }}
                transition={{ type: 'spring', stiffness: 280, damping: 30 }}
                rx={14}
                ry={14}
                fill="transparent"
                stroke="rgba(99, 102, 241, 0.85)"
                strokeWidth={2}
              />
            )}
          </svg>

          {/* Popover — re-enables pointer events for its own subtree. Held back
              until the target is measured so it appears on the right element. */}
          {popoverVisible && (
          <motion.div
            ref={popoverRef}
            key={`popover-${targetSelector ?? 'center'}`}
            initial={{ opacity: 0, y: 10, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 6, scale: 0.98 }}
            transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
            className="absolute rounded-2xl bg-white shadow-2xl border border-slate-100 p-5 pointer-events-auto"
            style={popoverStyle}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-indigo-600">
                <Sparkles size={14} />
                Step {stepIndex + 1} of {totalSteps}
              </div>
              <button
                onClick={onSkip}
                className="text-slate-400 hover:text-slate-600 transition-colors"
                aria-label="Skip tour"
              >
                <X size={18} />
              </button>
            </div>
            <h3 className="text-base font-semibold text-slate-900">{title}</h3>
            <p className="text-sm text-slate-600 mt-1.5 leading-relaxed">{renderBody(body)}</p>

            {tryIt && (
              <button
                onClick={tryIt.onClick}
                disabled={tryIt.loading}
                className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium px-3 py-1.5 rounded-lg border border-indigo-200 text-indigo-700 hover:bg-indigo-50 disabled:opacity-60"
              >
                {tryIt.loading ? 'Working…' : tryIt.label}
              </button>
            )}

            {/* Step dots */}
            <div className="mt-5 flex items-center gap-1.5">
              {Array.from({ length: totalSteps }).map((_, i) => (
                <span
                  key={i}
                  className={`h-1.5 rounded-full transition-all ${
                    i === stepIndex
                      ? 'w-5 bg-indigo-600'
                      : i < stepIndex
                        ? 'w-1.5 bg-indigo-300'
                        : 'w-1.5 bg-slate-200'
                  }`}
                />
              ))}
            </div>

            <div className="mt-4 flex items-center justify-between">
              <button
                onClick={onSkip}
                className="text-sm text-slate-500 hover:text-slate-700"
              >
                Skip tour
              </button>
              <div className="flex items-center gap-2">
                {onPrev && stepIndex > 0 && (
                  <button
                    onClick={onPrev}
                    className="text-sm font-medium px-3 py-1.5 rounded-lg text-slate-700 hover:bg-slate-100"
                  >
                    Back
                  </button>
                )}
                {!hideNext && (
                  <button
                    onClick={onNext}
                    className="text-sm font-medium px-4 py-1.5 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm"
                  >
                    {isLast ? 'Finish' : 'Next'}
                  </button>
                )}
              </div>
            </div>
          </motion.div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );

  return createPortal(node, document.body);
}

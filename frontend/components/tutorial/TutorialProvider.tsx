'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { Trash2 } from 'lucide-react';
import { useTutorial } from '@/hooks/useTutorial';
import { useTripStore } from '@/lib/store';
import SpotlightOverlay from './SpotlightOverlay';
import WelcomeModal from './WelcomeModal';
import {
  TUTORIAL_STEPS,
  TUTORIAL_TOTAL,
  expandRoute,
  urlMatches,
  type TutorialStep,
} from './steps';

/**
 * Top-level coordinator. Mounted inside the authenticated layout. Decides
 * whether to show the WelcomeModal, the SpotlightOverlay, or the final
 * "delete tutorial trip?" prompt; advances the backend step on each step
 * change so we can resume after reloads.
 */
export default function TutorialDriver() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const search = searchParams?.toString() ?? '';
  const tutorial = useTutorial();
  const [welcomeOpen, setWelcomeOpen] = useState(false);
  const [starting, setStarting] = useState(false);
  const [tryItLoading, setTryItLoading] = useState(false);
  const [finishPromptOpen, setFinishPromptOpen] = useState(false);
  const lastPushedHrefRef = useRef<string | null>(null);

  // After client-side navigation (e.g. /login → /dashboard) the auth cookie
  // may have just been set. Re-fetch tutorial status when the path changes
  // so `isAuthed` flips true after login.
  useEffect(() => {
    tutorial.refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  // Decide whether to show the welcome modal. Only ever pops for an
  // authenticated user (auth gate via `isAuthed`) and only on the dashboard.
  useEffect(() => {
    if (tutorial.isLoading) return;
    if (!tutorial.isAuthed) {
      setWelcomeOpen(false);
      return;
    }
    if (tutorial.status === 'not_started' && pathname?.startsWith('/dashboard')) {
      setWelcomeOpen(true);
    } else {
      setWelcomeOpen(false);
    }
  }, [tutorial.status, tutorial.isLoading, tutorial.isAuthed, pathname]);

  const currentStep = useMemo<TutorialStep | null>(() => {
    if (!tutorial.isAuthed) return null;
    if (tutorial.status !== 'in_progress') return null;
    const idx = Math.max(0, Math.min(TUTORIAL_TOTAL - 1, (tutorial.step || 1) - 1));
    return TUTORIAL_STEPS[idx] ?? null;
  }, [tutorial.isAuthed, tutorial.status, tutorial.step]);

  // The overlay must only appear once the browser is actually on the step's
  // page/mode — otherwise the popover flashes on the previous screen while the
  // router navigates. We hold it back until the URL matches.
  const routeReady = useMemo(() => {
    if (!currentStep) return false;
    const href = expandRoute(currentStep.route, tutorial.trip_id);
    if (!href) return true;
    return urlMatches(href, pathname, search);
  }, [currentStep, tutorial.trip_id, pathname, search]);

  // Step 9 spotlights the Concierge chat panel — open the drawer when we land on
  // the concierge step, and close it again on any other step (only while the
  // tour is active, so we never touch a drawer the user opened themselves).
  useEffect(() => {
    if (!currentStep) return;
    const store = useTripStore.getState();
    if (currentStep.id === 'concierge' && routeReady) {
      if (!store.conciergeOpen) store.openConcierge(null);
    } else if (store.conciergeOpen) {
      store.closeConcierge();
    }
  }, [currentStep, routeReady]);

  // Navigate to the step's target route when needed. We compare the *full*
  // URL (path + query) so mode-switching pushes actually fire.
  useEffect(() => {
    if (!currentStep) return;
    const href = expandRoute(currentStep.route, tutorial.trip_id);
    if (!href) return;
    if (urlMatches(href, pathname, search)) return;
    if (lastPushedHrefRef.current === href) return;
    lastPushedHrefRef.current = href;
    router.push(href);
  }, [currentStep, tutorial.trip_id, pathname, search, router]);

  // Reset the dedupe latch when the URL actually catches up.
  useEffect(() => {
    if (!lastPushedHrefRef.current) return;
    if (urlMatches(lastPushedHrefRef.current, pathname, search)) {
      lastPushedHrefRef.current = null;
    }
  }, [pathname, search]);

  // Listen for external advance / completion signals (e.g. plan-trip demo
  // emits a "preview shown" event, Create-trip click emits a "created" event).
  useEffect(() => {
    function onAdvance(evt: Event) {
      const detail = (evt as CustomEvent).detail as { to?: number } | undefined;
      if (detail?.to != null) {
        tutorial.advance(detail.to);
      } else if (currentStep) {
        const next = Math.min(TUTORIAL_TOTAL, currentStep.step + 1);
        tutorial.advance(next);
      }
    }
    window.addEventListener('tutorial:advance', onAdvance as EventListener);
    return () => window.removeEventListener('tutorial:advance', onAdvance as EventListener);
  }, [tutorial, currentStep]);

  const handleStart = useCallback(async () => {
    setStarting(true);
    try {
      await tutorial.start();
      setWelcomeOpen(false);
    } finally {
      setStarting(false);
    }
  }, [tutorial]);

  const handleSkipWelcome = useCallback(async () => {
    await tutorial.skip();
    setWelcomeOpen(false);
  }, [tutorial]);

  const handleSkip = useCallback(async () => {
    await tutorial.skip();
  }, [tutorial]);

  const handlePrev = useCallback(async () => {
    if (!currentStep) return;
    const target = Math.max(1, currentStep.step - 1);
    await tutorial.advance(target);
  }, [currentStep, tutorial]);

  const handleNext = useCallback(async () => {
    if (!currentStep) return;
    if (currentStep.step >= TUTORIAL_TOTAL) {
      await tutorial.complete();
      setFinishPromptOpen(true);
      return;
    }
    await tutorial.advance(currentStep.step + 1);
  }, [currentStep, tutorial]);

  const handleTryIt = useCallback(async () => {
    if (!currentStep?.tryIt) return;
    const action = currentStep.tryIt.action;

    // Demo step: kick the planner into its simulated-plan flow. The planner
    // itself fires `tutorial:advance` once the preview is on screen, then
    // again when the user clicks "Create Trip and Take Me There".
    if (action === 'plan-trip-demo') {
      window.dispatchEvent(new CustomEvent('tutorial:plan-demo'));
      return;
    }

    if (!tutorial.trip_id) return;
    setTryItLoading(true);
    try {
      // Drive the live panel so the message + reply animate in place, instead
      // of firing a silent API call the user never sees.
      if (action === 'brainstorm-send-sample') {
        window.dispatchEvent(new CustomEvent('tutorial:brainstorm-send', {
          detail: { message: 'What about a rainy-day plan for Day 2?' },
        }));
      } else if (action === 'concierge-send-sample') {
        useTripStore.getState().openConcierge(null);
        // Let the drawer mount before it receives the send event.
        setTimeout(() => {
          window.dispatchEvent(new CustomEvent('tutorial:concierge-send', {
            detail: { message: 'What is the move tonight?' },
          }));
        }, 350);
      }
    } finally {
      setTryItLoading(false);
    }
  }, [currentStep, tutorial.trip_id]);

  const handleDeleteFinish = useCallback(async () => {
    await tutorial.deleteTutorialTrip();
    setFinishPromptOpen(false);
    router.push('/dashboard');
  }, [tutorial, router]);

  const handleKeepFinish = useCallback(() => {
    setFinishPromptOpen(false);
    router.push('/dashboard');
  }, [router]);

  if (tutorial.isLoading) return null;

  const isLast = currentStep?.step === TUTORIAL_TOTAL;
  const hideNextChrome = !!currentStep?.manualAdvance;

  return (
    <>
      <WelcomeModal
        open={welcomeOpen}
        starting={starting}
        onStart={handleStart}
        onSkip={handleSkipWelcome}
      />
      <SpotlightOverlay
        open={!!currentStep && routeReady}
        targetSelector={currentStep?.target}
        title={currentStep?.title ?? ''}
        body={currentStep?.body ?? ''}
        stepIndex={currentStep ? currentStep.step - 1 : 0}
        totalSteps={TUTORIAL_TOTAL}
        onPrev={currentStep && currentStep.step > 1 ? handlePrev : undefined}
        onNext={handleNext}
        onSkip={handleSkip}
        isLast={isLast}
        hideNext={hideNextChrome}
        tryIt={
          currentStep?.tryIt
            ? {
                label: currentStep.tryIt.label,
                onClick: handleTryIt,
                loading: tryItLoading,
              }
            : undefined
        }
      />
      <AnimatePresence>
        {finishPromptOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[110] bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4"
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.97, y: 8 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.98 }}
              transition={{ type: 'spring', stiffness: 280, damping: 26 }}
              className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6"
            >
              <h3 className="text-lg font-semibold text-slate-900">Tour complete</h3>
              <p className="mt-1.5 text-sm text-slate-600">
                Want to remove the tutorial trip now, or keep it around to poke at
                later? You can always replay the tour from your profile.
              </p>
              <div className="mt-5 flex items-center justify-end gap-2">
                <button
                  onClick={handleKeepFinish}
                  className="text-sm font-medium px-3.5 py-2 rounded-lg text-slate-700 hover:bg-slate-100"
                >
                  Keep for now
                </button>
                <button
                  onClick={handleDeleteFinish}
                  className="inline-flex items-center gap-1.5 text-sm font-semibold px-3.5 py-2 rounded-lg bg-rose-600 text-white hover:bg-rose-700"
                >
                  <Trash2 size={14} />
                  Delete tutorial trip
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

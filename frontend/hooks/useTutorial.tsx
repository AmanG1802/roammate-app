'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { api } from '@/lib/api';

export type TutorialStatus =
  | 'not_started'
  | 'in_progress'
  | 'completed'
  | 'skipped';

export type TutorialState = {
  status: TutorialStatus;
  step: number;
  trip_id: number | null;
  platform: 'web' | 'ios';
};

type Ctx = TutorialState & {
  isLoading: boolean;
  isActive: boolean;
  /** True only when /api/tutorial/status returned 2xx — i.e. a logged-in user. */
  isAuthed: boolean;
  start: () => Promise<TutorialState>;
  advance: (step: number) => Promise<TutorialState>;
  skip: () => Promise<TutorialState>;
  complete: () => Promise<TutorialState>;
  replay: () => Promise<TutorialState>;
  reset: () => Promise<TutorialState>;
  deleteTutorialTrip: () => Promise<TutorialState>;
  refresh: () => Promise<void>;
};

const TutorialContext = createContext<Ctx | null>(null);

const DEFAULT_STATE: TutorialState = {
  status: 'not_started',
  step: 0,
  trip_id: null,
  platform: 'web',
};

export function TutorialProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<TutorialState>(DEFAULT_STATE);
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthed, setIsAuthed] = useState(false);
  const loadedOnce = useRef(false);

  const refresh = useCallback(async () => {
    try {
      const data = await api<TutorialState>('/api/tutorial/status');
      setState(data);
      setIsAuthed(true);
    } catch {
      // Anonymous, not logged in, or backend down — treat as default and
      // keep `isAuthed` false so the driver stays dormant on /login etc.
      setState(DEFAULT_STATE);
      setIsAuthed(false);
    } finally {
      setIsLoading(false);
      loadedOnce.current = true;
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const post = useCallback(
    async (path: string, method: 'POST' | 'PATCH' | 'DELETE', body?: unknown) => {
      const data = await api<TutorialState>(path, {
        method,
        ...(body !== undefined ? { json: body } : {}),
      });
      setState(data);
      return data;
    },
    [],
  );

  const start = useCallback(() => post('/api/tutorial/start', 'POST'), [post]);
  const advance = useCallback(
    (step: number) => post('/api/tutorial/step', 'PATCH', { step }),
    [post],
  );
  const skip = useCallback(() => post('/api/tutorial/skip', 'POST'), [post]);
  const complete = useCallback(() => post('/api/tutorial/complete', 'POST'), [post]);
  const replay = useCallback(() => post('/api/tutorial/replay', 'POST'), [post]);
  const reset = useCallback(() => post('/api/tutorial/reset', 'POST'), [post]);
  const deleteTutorialTrip = useCallback(
    () => post('/api/tutorial/trip', 'DELETE'),
    [post],
  );

  const value = useMemo<Ctx>(
    () => ({
      ...state,
      isLoading,
      isAuthed,
      isActive: state.status === 'in_progress',
      start,
      advance,
      skip,
      complete,
      replay,
      reset,
      deleteTutorialTrip,
      refresh,
    }),
    [state, isLoading, isAuthed, start, advance, skip, complete, replay, reset, deleteTutorialTrip, refresh],
  );

  return (
    <TutorialContext.Provider value={value}>{children}</TutorialContext.Provider>
  );
}

export function useTutorial(): Ctx {
  const ctx = useContext(TutorialContext);
  if (!ctx) {
    throw new Error('useTutorial must be used within a TutorialProvider');
  }
  return ctx;
}

export function useTutorialOptional(): Ctx | null {
  return useContext(TutorialContext);
}

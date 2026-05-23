import type { Route } from 'next';

export type TutorialStepId =
  | 'dashboard'
  | 'plan-trip'
  | 'plan-preview'
  | 'trip-overview'
  | 'timeline'
  | 'brainstorm-chat'
  | 'brainstorm-bin'
  | 'idea-bin'
  | 'concierge'
  | 'wrap-up';

export type TryItAction =
  | 'plan-trip-demo'
  | 'brainstorm-send-sample'
  | 'concierge-send-sample';

export type TutorialStep = {
  id: TutorialStepId;
  step: number; // 1-based, matches backend tutorial_step
  title: string;
  body: string;
  /** CSS selector used by the overlay; falls back to centered tooltip. */
  target?: string;
  /**
   * Path the driver should be on for this step.
   *   "trip:landing"    → /trips/{id}
   *   "trip:plan"       → /trips?id={id}&mode=plan
   *   "trip:brainstorm" → /trips?id={id}&mode=brainstorm
   *   "trip:concierge"  → /trips?id={id}&mode=concierge
   * Plain strings pass through as absolute routes.
   */
  route?: string;
  /** Show a "Next" button when true; otherwise the step is advanced by an
   *  external signal (e.g. plan-trip preview shown, Create-trip clicked). */
  manualAdvance?: boolean;
  tryIt?: { label: string; action: TryItAction };
};

export const TUTORIAL_STEPS: TutorialStep[] = [
  {
    id: 'dashboard',
    step: 1,
    title: 'Welcome to Roammate',
    body: 'This is your home. Trips you create or join show up here — let’s plan your first one.',
    target: '[data-tutorial="dashboard-trips-grid"]',
    route: '/dashboard',
  },
  {
    id: 'plan-trip',
    step: 2,
    title: 'AI-powered trip planning',
    body: 'Every trip starts here — give the planner a vibe or a city and it sketches the bones. Hit Try Now to watch it work.',
    target: '[data-tutorial="new-trip-btn"]',
    route: '/dashboard',
    tryIt: { label: 'Try Now', action: 'plan-trip-demo' },
  },
  {
    id: 'plan-preview',
    step: 3,
    title: 'Your trip preview',
    body: 'The planner returns a preview with a name, duration, and brainstorm items. When you’re happy, hit "Create Trip and Take Me There".',
    target: '[data-tutorial="plan-preview-card"]',
    route: '/dashboard',
    manualAdvance: true, // advanced when the user clicks Create on the preview
  },
  {
    id: 'trip-overview',
    step: 4,
    title: 'Your trip at a glance',
    body: 'Members, dates, and the trip summary live here. Tap a sub-page to dive in.',
    target: '[data-tutorial="trip-overview-header"]',
    route: 'trip:landing',
  },
  {
    id: 'brainstorm-chat',
    step: 5,
    title: 'Brainstorm with AI',
    body: 'Chat with Roammate to discover places. Each conversation is private to you.',
    target: '[data-tutorial="brainstorm-chat-input"]',
    route: 'trip:brainstorm',
    tryIt: { label: 'Send a sample message', action: 'brainstorm-send-sample' },
  },
  {
    id: 'brainstorm-bin',
    step: 6,
    title: 'Your brainstorm bin',
    body: 'Ideas you save from chat land here. Promote the good ones into the shared Idea Bin.',
    target: '[data-tutorial="brainstorm-bin-list"]',
    route: 'trip:brainstorm',
  },
  {
    id: 'timeline',
    step: 7,
    title: 'Day-by-day timeline',
    body: 'Your itinerary, sorted by day. Conflicts and travel times surface automatically here.',
    target: '[data-tutorial="timeline-day-1"]',
    route: 'trip:plan',
  },
  {
    id: 'idea-bin',
    step: 8,
    title: 'Shared ideas → timeline',
    body: 'The Idea Bin is shared with the group. Promote an idea, then refresh the route to see the map redraw.',
    target: '[data-tutorial="idea-bin-list"]',
    route: 'trip:plan',
  },
  {
    id: 'concierge',
    step: 9,
    title: 'Meet Concierge',
    body: 'Your on-trip copilot — reroutes, recommendations, on-the-fly help. Normally Plus, but the tour gives you a free taste.',
    target: '[data-tutorial="concierge-panel"]',
    route: 'trip:concierge',
    tryIt: { label: 'Send a sample message', action: 'concierge-send-sample' },
  },
  {
    id: 'wrap-up',
    step: 10,
    title: 'You’re all set',
    body: 'That’s the tour. Keep the tutorial trip around or remove it now?',
    route: '/dashboard',
  },
];

export const TUTORIAL_TOTAL = TUTORIAL_STEPS.length;

/** Expand the step's route into an absolute href, plugging in the trip id. */
export function expandRoute(route: string | undefined, tripId: number | null): Route | null {
  if (!route) return null;
  if (!route.startsWith('trip:')) return route as Route;
  if (tripId == null) return '/dashboard' as Route;
  const rest = route.slice('trip:'.length);
  switch (rest) {
    case 'landing':
      return (`/trips/${tripId}`) as Route;
    case 'plan':
      return (`/trips?id=${tripId}&mode=plan`) as Route;
    case 'brainstorm':
      return (`/trips?id=${tripId}&mode=brainstorm`) as Route;
    case 'concierge':
      return (`/trips?id=${tripId}&mode=concierge`) as Route;
    case 'people':
      return (`/trips?id=${tripId}&mode=people`) as Route;
    default:
      return (`/trips/${tripId}`) as Route;
  }
}

/** True when the browser's current URL already matches the expanded href. */
export function urlMatches(href: string, pathname: string | null, search: string | null): boolean {
  if (!pathname) return false;
  const [hrefPath, hrefQuery = ''] = href.split('?');
  if (pathname !== hrefPath) return false;
  if (!hrefQuery) return true;
  const params = new URLSearchParams(hrefQuery);
  const current = new URLSearchParams(search ?? '');
  return Array.from(params.entries()).every(([k, v]) => current.get(k) === v);
}

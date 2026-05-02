import { useReducedMotion, type Transition, type Variants } from "framer-motion";

export const motionTokens = {
  duration: {
    fast: 0.15,
    base: 0.22,
    slow: 0.32,
  },
  ease: {
    out: [0.16, 1, 0.3, 1] as [number, number, number, number],
    inOut: [0.65, 0, 0.35, 1] as [number, number, number, number],
  },
  spring: {
    snappy: { type: "spring", stiffness: 380, damping: 32, mass: 0.6 } as Transition,
    gentle: { type: "spring", stiffness: 220, damping: 26, mass: 0.8 } as Transition,
  },
} as const;

export const fadeUp: Variants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -4 },
};

export const fadeScale: Variants = {
  initial: { opacity: 0, scale: 0.98 },
  animate: { opacity: 1, scale: 1 },
  exit: { opacity: 0, scale: 0.99 },
};

export const fadeOnly: Variants = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
};

export const directionalSlide = (direction: 1 | -1): Variants => ({
  initial: { opacity: 0, y: 12 * direction },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 * direction },
});

export const staggerContainer = (stagger = 0.04, delayChildren = 0): Variants => ({
  initial: {},
  animate: {
    transition: { staggerChildren: stagger, delayChildren },
  },
});

/**
 * Wraps useReducedMotion so consumers get safe fallbacks. When the user has
 * prefers-reduced-motion enabled we collapse durations to ~0 and disable
 * non-opacity transforms — content still appears, just without movement.
 */
export function useAppMotion() {
  const reduce = useReducedMotion();

  const transition = (preset: Transition = { duration: motionTokens.duration.base, ease: motionTokens.ease.out }): Transition =>
    reduce ? { duration: 0 } : preset;

  const variants = (v: Variants): Variants => {
    if (!reduce) return v;
    const stripTransform = (state: Record<string, unknown> | undefined) => {
      if (!state) return state;
      const { x, y, scale, rotate, rotateX, rotateY, ...rest } = state as Record<string, unknown>;
      return rest;
    };
    return Object.fromEntries(
      Object.entries(v).map(([k, val]) => [k, stripTransform(val as Record<string, unknown>)])
    ) as Variants;
  };

  return { reduce: !!reduce, transition, variants };
}

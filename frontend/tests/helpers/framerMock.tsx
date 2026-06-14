/**
 * Shared framer-motion stub for component tests.
 *
 * Renders motion.* elements as plain DOM nodes (dropping animation-only props
 * and forwarding refs). Components are cached per tag so `motion.div` keeps a
 * stable identity across renders — without this React remounts the subtree on
 * every render and swaps out DOM nodes, detaching anything tests hold.
 *
 * Usage:  vi.mock('framer-motion', () => import('../helpers/framerMock'));
 */
import React from 'react';

const MOTION_PROPS = new Set([
  'initial', 'animate', 'exit', 'layout', 'layoutId', 'transition',
  'whileHover', 'whileTap', 'whileFocus', 'whileInView', 'whileDrag',
  'viewport', 'variants', 'drag', 'dragConstraints', 'dragElastic',
  'onAnimationComplete', 'onAnimationStart', 'custom',
]);

function make(tag: string) {
  return React.forwardRef((props: Record<string, unknown>, ref: React.Ref<HTMLElement>) => {
    const clean: Record<string, unknown> = {};
    for (const k in props) if (!MOTION_PROPS.has(k)) clean[k] = props[k];
    return React.createElement(tag, { ...clean, ref });
  });
}

const cache: Record<string, unknown> = {};

export const motion = new Proxy(
  {},
  { get: (_t, tag: string) => (cache[tag] ??= make(tag)) },
) as Record<string, React.ElementType>;

export const AnimatePresence = ({ children }: { children: React.ReactNode }) => <>{children}</>;

// framer-motion also exports these; provide harmless stubs.
export const useReducedMotion = () => true;
export const useAnimation = () => ({ start: () => Promise.resolve(), stop: () => {}, set: () => {} });
export const LayoutGroup = ({ children }: { children: React.ReactNode }) => <>{children}</>;

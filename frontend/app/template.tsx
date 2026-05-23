'use client';

/**
 * Root page-transition template. App Router re-mounts the template on every
 * navigation, so wrapping children in a motion element gives us a soft
 * fade/slide on route changes (landing → /pricing, landing → /login, etc).
 *
 * Honours prefers-reduced-motion via useAppMotion.
 */
import { motion } from 'framer-motion';
import { useAppMotion, motionTokens } from '@/lib/motion';

export default function Template({ children }: { children: React.ReactNode }) {
  const { reduce } = useAppMotion();
  // IMPORTANT: animate `opacity` only. Properties like `transform`, `filter`,
  // `will-change`, and `backdrop-filter` turn an element into a containing
  // block for fixed-positioned descendants, which would cause `position: fixed`
  // navbars rendered inside the page to scroll away with the page.
  return (
    <motion.div
      initial={reduce ? false : { opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4, ease: motionTokens.ease.out }}
    >
      {children}
    </motion.div>
  );
}

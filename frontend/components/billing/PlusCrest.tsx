'use client';

/**
 * The Plus brand crest: a rounded square with the indigo→fuchsia→amber
 * brand gradient and a subtle conic-gradient shimmer overlay. Reserved
 * exclusively for Plus surfaces (paywall hero, profile row when subscribed,
 * subscription page). Never appears on free-tier surfaces.
 */
import { Sparkles } from 'lucide-react';

interface PlusCrestProps {
  size?: number;
  className?: string;
  iconClassName?: string;
}

export function PlusCrest({ size = 56, className = '', iconClassName = '' }: PlusCrestProps) {
  return (
    <div
      className={`relative rounded-2xl overflow-hidden shrink-0 ${className}`}
      style={{
        width: size,
        height: size,
        backgroundImage: 'linear-gradient(135deg, #4F46E5 0%, #D946EF 55%, #F59E0B 100%)',
        boxShadow: '0 8px 24px -8px rgba(79, 70, 229, 0.45)',
      }}
      aria-hidden
    >
      {/* Slowly rotating conic-gradient shimmer — paused under prefers-reduced-motion. */}
      <div
        className="absolute inset-0 plus-crest-shimmer mix-blend-overlay opacity-60"
        style={{
          backgroundImage:
            'conic-gradient(from 0deg, rgba(255,255,255,0.0), rgba(255,255,255,0.45), rgba(255,255,255,0.0) 60%, rgba(255,255,255,0.4), rgba(255,255,255,0.0))',
        }}
      />
      <div className="absolute inset-0 flex items-center justify-center">
        <Sparkles
          className={`text-white drop-shadow ${iconClassName}`}
          style={{ width: size * 0.45, height: size * 0.45 }}
          strokeWidth={2.2}
        />
      </div>
    </div>
  );
}


/**
 * The "Roammate Plus" wordmark with the brand gradient applied as text.
 * Use anywhere we name the product publicly.
 */
export function PlusWordmark({ className = '' }: { className?: string }) {
  return (
    <span
      className={`bg-clip-text text-transparent font-black tracking-tight ${className}`}
      style={{
        backgroundImage: 'linear-gradient(135deg, #4F46E5 0%, #D946EF 55%, #F59E0B 100%)',
      }}
    >
      Roammate Plus
    </span>
  );
}

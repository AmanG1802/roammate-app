'use client';

import { createContext, useContext, useEffect, useState } from 'react';

type Breakpoint = 'sm' | 'md' | 'lg';

interface OverlayCtx {
  breakpoint: Breakpoint;
}

const Ctx = createContext<OverlayCtx>({ breakpoint: 'lg' });

export function useMapBreakpoint(): Breakpoint {
  return useContext(Ctx).breakpoint;
}

function resolveBreakpoint(width: number): Breakpoint {
  if (width < 640) return 'sm';
  if (width < 1024) return 'md';
  return 'lg';
}

interface MapOverlayLayerProps {
  children: React.ReactNode;
}

/**
 * Pointer-events transparent wrapper that gives map overlays a shared
 * coordinate system + breakpoint context. Slot children opt back into
 * pointer events via `pointer-events-auto` (the *Slot helpers below do
 * this for you).
 *
 * The breakpoint is derived from the rendered map container, not the
 * viewport — when the map is rendered inside a narrow side panel we
 * want the small-screen layout even on a wide screen.
 */
export default function MapOverlayLayer({ children }: MapOverlayLayerProps) {
  const [bp, setBp] = useState<Breakpoint>('lg');
  const [ref, setRef] = useState<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!ref) return;
    const update = () => setBp(resolveBreakpoint(ref.clientWidth));
    update();
    const ro = new ResizeObserver(update);
    ro.observe(ref);
    return () => ro.disconnect();
  }, [ref]);

  return (
    <Ctx.Provider value={{ breakpoint: bp }}>
      <div ref={setRef} className="pointer-events-none absolute inset-0 z-20">
        {children}
      </div>
    </Ctx.Provider>
  );
}

function Slot({
  className,
  children,
}: {
  className: string;
  children: React.ReactNode;
}) {
  return (
    <div className={`pointer-events-auto absolute ${className}`}>{children}</div>
  );
}

MapOverlayLayer.TopLeft = function TopLeft({ children }: { children: React.ReactNode }) {
  return <Slot className="top-3 left-3 sm:top-4 sm:left-4">{children}</Slot>;
};

MapOverlayLayer.TopCenter = function TopCenter({ children }: { children: React.ReactNode }) {
  return (
    <Slot className="top-3 left-1/2 -translate-x-1/2 sm:top-4 flex flex-col items-center gap-1.5">
      {children}
    </Slot>
  );
};

MapOverlayLayer.TopRight = function TopRight({ children }: { children: React.ReactNode }) {
  return (
    <Slot className="top-3 right-3 sm:top-4 sm:right-4 flex flex-row items-center gap-1.5 md:flex-col md:gap-2">
      {children}
    </Slot>
  );
};

MapOverlayLayer.BottomLeft = function BottomLeft({ children }: { children: React.ReactNode }) {
  return <Slot className="bottom-4 left-3 sm:left-4 sm:bottom-6">{children}</Slot>;
};

MapOverlayLayer.BottomCenter = function BottomCenter({ children }: { children: React.ReactNode }) {
  return (
    <Slot className="bottom-4 left-1/2 -translate-x-1/2 sm:bottom-6 flex flex-col items-center gap-1.5">
      {children}
    </Slot>
  );
};

MapOverlayLayer.BottomRight = function BottomRight({ children }: { children: React.ReactNode }) {
  return <Slot className="bottom-4 right-3 sm:right-4 sm:bottom-6">{children}</Slot>;
};

/** Full-width banner slot used on mobile for toasts so the centered pill
 *  doesn't overflow narrow viewports. */
MapOverlayLayer.TopBanner = function TopBanner({ children }: { children: React.ReactNode }) {
  return (
    <Slot className="top-3 left-3 right-3 sm:top-4 sm:left-1/2 sm:right-auto sm:-translate-x-1/2 sm:max-w-md flex justify-center">
      {children}
    </Slot>
  );
};

'use client';

import { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence, LayoutGroup } from 'framer-motion';
import { Check, RotateCcw, Save } from 'lucide-react';
import { usePersonaCatalog, type PersonaCatalogItem } from '@/contexts/PersonaCatalogContext';

type PersonaPickerProps = {
  initial: string[];
  onSave: (selected: string[]) => Promise<void>;
  layout?: 'page' | 'onboarding';
};

function arraysEqual(a: string[], b: string[]) {
  if (a.length !== b.length) return false;
  const sa = [...a].sort();
  const sb = [...b].sort();
  return sa.every((v, i) => v === sb[i]);
}

function sortedCatalog(catalog: PersonaCatalogItem[], selected: string[]): PersonaCatalogItem[] {
  const sel = catalog.filter((c) => selected.includes(c.slug));
  const unsel = catalog.filter((c) => !selected.includes(c.slug));
  return [...sel, ...unsel];
}

export default function PersonaPicker({ initial, onSave, layout = 'page' }: PersonaPickerProps) {
  const { catalog, isLoading } = usePersonaCatalog();
  const [selected, setSelected] = useState<string[]>(initial);
  const [savedSelected, setSavedSelected] = useState<string[]>(initial);
  const [orderedCatalog, setOrderedCatalog] = useState<PersonaCatalogItem[]>([]);
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved'>('idle');
  const [showFireToast, setShowFireToast] = useState(false);
  const prevCount = useRef(initial.length);

  // Initialize ordered catalog
  useEffect(() => {
    if (catalog.length) setOrderedCatalog(sortedCatalog(catalog, initial));
  }, [catalog, initial]);

  useEffect(() => {
    setSelected(initial);
    setSavedSelected(initial);
  }, [initial]);

  useEffect(() => {
    if (selected.length >= 5 && prevCount.current < 5) {
      setShowFireToast(true);
      setTimeout(() => setShowFireToast(false), 2500);
    }
    prevCount.current = selected.length;
  }, [selected]);

  const dirty = !arraysEqual(selected, savedSelected);

  const toggle = (slug: string) => {
    setSelected((prev) =>
      prev.includes(slug) ? prev.filter((s) => s !== slug) : [...prev, slug]
    );
  };

  const handleSave = async () => {
    setSaveState('saving');
    await onSave(selected);
    setSavedSelected(selected);
    // Reorder: selected first, then unselected — both in catalog order
    setOrderedCatalog(sortedCatalog(catalog, selected));
    setSaveState('saved');
    setTimeout(() => setSaveState('idle'), 2000);
  };

  const handleReset = () => {
    setSelected(savedSelected);
  };

  if (isLoading) {
    return (
      <div className="flex flex-wrap justify-center gap-2.5 py-4 w-3/5 mx-auto">
        {Array.from({ length: 14 }).map((_, i) => (
          <div key={i} className="h-10 w-28 rounded-xl bg-slate-100 animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      {layout === 'page' && (
        <div>
          <h2 className="text-xl font-black text-slate-900">What makes you tick?</h2>
          <p className="text-sm text-slate-500 mt-1">
            Select your travel personas — your concierge adapts to them.
          </p>
        </div>
      )}

      {selected.length === 0 && layout === 'page' && (
        <p className="text-xs text-slate-400 italic text-center -mb-2">
          Pick at least one — your concierge gets smarter the more it knows.
        </p>
      )}

      {/* Free-flowing wrap layout — max 4 items per row, centered, 60% width bound */}
      <LayoutGroup>
        <div className="w-[60%] mx-auto flex flex-wrap justify-center gap-2.5">
          {orderedCatalog.map((item) => {
            const isSelected = selected.includes(item.slug);
            return (
              <motion.button
                key={item.slug}
                layout
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.18, layout: { duration: 0.25, ease: 'easeInOut' } }}
                onClick={() => toggle(item.slug)}
                role="checkbox"
                aria-checked={isSelected}
                className={`relative flex items-center gap-2 py-2.5 px-4 rounded-xl border text-sm font-bold transition-all duration-150 cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500
                  ${isSelected
                    ? 'border-indigo-600 border-2 bg-indigo-50 text-indigo-800 shadow-sm shadow-indigo-100 scale-[1.03]'
                    : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:shadow-sm'
                  }`}
              >
                <span className="text-base leading-none shrink-0" role="img" aria-hidden>{item.icon}</span>
                <span className="leading-tight">{item.label}</span>
                {isSelected && (
                  <span className="absolute -top-1.5 -right-1.5 w-4 h-4 bg-indigo-600 rounded-full flex items-center justify-center shadow">
                    <Check className="w-2.5 h-2.5 text-white" strokeWidth={3} />
                  </span>
                )}
              </motion.button>
            );
          })}
        </div>
      </LayoutGroup>

      <AnimatePresence>
        {showFireToast && (
          <motion.p
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="text-center text-sm font-bold text-orange-500"
          >
            🔥 You&apos;re getting specific!
          </motion.p>
        )}
      </AnimatePresence>

      {layout === 'page' && (
        <div className="flex items-center justify-center gap-3 pt-2 border-t border-slate-100">
          <button
            onClick={handleReset}
            disabled={!dirty}
            className="flex items-center gap-1.5 px-4 py-2 text-sm font-bold text-slate-500 border border-slate-200 rounded-xl hover:bg-slate-50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Reset
          </button>
          <button
            onClick={handleSave}
            disabled={!dirty || saveState === 'saving'}
            className="flex items-center gap-1.5 px-5 py-2 text-sm font-bold bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer shadow-sm shadow-indigo-200"
          >
            <Save className="w-3.5 h-3.5" />
            {saveState === 'saving' ? 'Saving…' : saveState === 'saved' ? 'Saved ✓' : 'Save'}
          </button>
        </div>
      )}
    </div>
  );
}

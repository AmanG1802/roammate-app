'use client';

import { useEffect } from 'react';
import { Loader2 } from 'lucide-react';
import PersonaPicker from '@/components/PersonaPicker';
import { PersonaCatalogProvider } from '@/contexts/PersonaCatalogContext';
import { useProfile } from '@/hooks/useProfile';

export default function PersonaPage() {
  const { profile, isLoading, fetchProfile, updatePersonas } = useProfile();

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  const handleSave = async (selected: string[]) => {
    const ok = await updatePersonas(selected);
    if (ok) {
      // Show toast feedback
      const msg = selected.length === 0
        ? 'Preferences cleared.'
        : `${selected.length} persona${selected.length > 1 ? 's' : ''} saved!`;
      // Simple browser notification since react-hot-toast may not be installed
      const banner = document.createElement('div');
      banner.textContent = `✓ ${msg}`;
      banner.style.cssText =
        'position:fixed;bottom:24px;right:24px;background:#4f46e5;color:white;font-weight:800;font-size:13px;padding:10px 18px;border-radius:12px;z-index:9999;box-shadow:0 4px 20px rgba(0,0,0,0.15)';
      document.body.appendChild(banner);
      setTimeout(() => banner.remove(), 2500);
    }
  };

  if (isLoading || !profile) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
      </div>
    );
  }

  return (
    <div>
      <PersonaCatalogProvider>
        <PersonaPicker
          initial={profile.personas ?? []}
          onSave={handleSave}
          layout="page"
        />
      </PersonaCatalogProvider>
    </div>
  );
}

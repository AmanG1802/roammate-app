'use client';

import { useEffect, useState } from 'react';
import { Loader2, RotateCcw } from 'lucide-react';
import { useRouter } from 'next/navigation';
import EditProfile from '@/components/EditProfile';
import { useProfile } from '@/hooks/useProfile';
import { useTutorial } from '@/hooks/useTutorial';

export default function EditProfilePage() {
  const { profile, isLoading, fetchProfile, updateProfile, deleteAccount } = useProfile();
  const { reset } = useTutorial();
  const router = useRouter();
  const [replaying, setReplaying] = useState(false);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  const handleReplay = async () => {
    setReplaying(true);
    try {
      // Reset to a pristine pre-Welcome state, then land on the dashboard so the
      // "Welcome to Roammate" banner shows again before Step 1.
      await reset();
      router.push('/dashboard');
    } finally {
      setReplaying(false);
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
      <h1 className="text-2xl font-black text-slate-900 mb-6">Edit Profile</h1>
      <EditProfile
        profile={profile}
        onUpdate={updateProfile}
        onDeleteAccount={deleteAccount}
      />

      <section className="mt-10 rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
        <div className="flex items-start gap-4">
          <div className="h-10 w-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0">
            <RotateCcw size={18} />
          </div>
          <div className="flex-1">
            <h2 className="text-base font-semibold text-slate-900">Replay tutorial</h2>
            <p className="text-sm text-slate-600 mt-1 leading-relaxed">
              Walks you through Roammate again on a fresh NYC tutorial trip. Your
              other trips aren&apos;t touched.
            </p>
          </div>
          <button
            onClick={handleReplay}
            disabled={replaying}
            className="text-sm font-semibold px-4 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm disabled:opacity-60"
          >
            {replaying ? 'Resetting…' : 'Replay tour'}
          </button>
        </div>
      </section>
    </div>
  );
}

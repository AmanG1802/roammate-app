'use client';

import { useEffect } from 'react';
import { Loader2 } from 'lucide-react';
import EditProfile from '@/components/EditProfile';
import { useProfile } from '@/hooks/useProfile';

export default function EditProfilePage() {
  const { profile, isLoading, fetchProfile, updateProfile, deleteAccount } = useProfile();

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

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
    </div>
  );
}

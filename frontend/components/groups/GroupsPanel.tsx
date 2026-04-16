'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { Users, Plus, Loader2, Check, XCircle, ChevronLeft, X, Mail, Trash2, Link2, MapPin, Lightbulb } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const API = process.env.NEXT_PUBLIC_API_URL ?? '';

function auth(): Record<string, string> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function authJson(): Record<string, string> {
  return { ...auth(), 'Content-Type': 'application/json' };
}

type Group = {
  id: number;
  name: string;
  owner_id: number;
  created_at: string;
  my_role: string;
  member_count: number;
  trip_count: number;
};

type GroupDetail = {
  id: number;
  name: string;
  owner_id: number;
  created_at: string;
  my_role: string;
};

type GroupMember = {
  id: number;
  group_id: number;
  user_id: number;
  role: string;
  status: string;
  user: { id: number; name: string; email: string };
};

type GroupInvitation = {
  id: number;
  group_id: number;
  role: string;
  group: { id: number; name: string };
  inviter: { name: string; email: string } | null;
};

type GroupTrip = { id: number; name: string; start_date: string | null };

type Idea = {
  id: number;
  trip_id: number;
  title: string;
  place_id?: string | null;
  lat?: number | null;
  lng?: number | null;
  time_hint?: string | null;
  added_by?: string | null;
};

export default function GroupsPanel({ onInvitationsChange }: { onInvitationsChange?: (count: number) => void } = {}) {
  const [view, setView] = useState<{ kind: 'list' } | { kind: 'detail'; id: number }>({ kind: 'list' });
  const [groups, setGroups] = useState<Group[]>([]);
  const [invitations, setInvitations] = useState<GroupInvitation[]>([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [g, inv] = await Promise.all([
        fetch(`${API}/groups/`, { headers: auth() }).then((r) => (r.ok ? r.json() : [])),
        fetch(`${API}/groups/invitations/pending`, { headers: auth() }).then((r) => (r.ok ? r.json() : [])),
      ]);
      setGroups(g);
      setInvitations(inv);
      onInvitationsChange?.(inv.length);
    } finally {
      setLoading(false);
    }
  }, [onInvitationsChange]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  if (view.kind === 'detail') {
    return (
      <GroupDetailView
        groupId={view.id}
        onBack={() => { setView({ kind: 'list' }); fetchAll(); }}
      />
    );
  }

  return (
    <>
      <div className="flex items-start justify-between mb-8 gap-6">
        <div>
          <h2 className="text-3xl font-black text-slate-900 mb-1">Groups</h2>
          <p className="text-slate-500 font-medium">
            {groups.length === 0 ? 'Create a group to plan trips with the same crew over and over.' : `You're in ${groups.length} ${groups.length === 1 ? 'group' : 'groups'}.`}
          </p>
        </div>
        <button
          onClick={() => setCreateOpen(true)}
          className="flex items-center gap-2 px-5 py-2.5 bg-slate-900 text-white rounded-xl font-black text-sm hover:bg-indigo-600 transition-all shadow-lg shadow-indigo-100"
        >
          <Plus className="w-4 h-4" />
          New Group
        </button>
      </div>

      {invitations.length > 0 && (
        <section className="mb-10">
          <h3 className="text-xs font-black uppercase tracking-widest text-slate-400 mb-3">Pending group invites</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {invitations.map((inv) => (
              <GroupInviteCard key={inv.id} inv={inv} onChange={fetchAll} />
            ))}
          </div>
        </section>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-10 h-10 text-indigo-600 animate-spin" />
        </div>
      ) : groups.length === 0 && invitations.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <div className="w-20 h-20 bg-indigo-50 rounded-[2rem] flex items-center justify-center mb-6">
            <Users className="w-10 h-10 text-indigo-300" />
          </div>
          <h3 className="text-2xl font-black text-slate-900 mb-2">No groups yet.</h3>
          <p className="text-slate-500 font-medium max-w-sm mb-6">
            Start a group for your family, your ski crew, or that friend you always travel with. Ideas and trips live forever.
          </p>
          <button
            onClick={() => setCreateOpen(true)}
            className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-black text-sm hover:bg-indigo-700 transition-all"
          >
            Create your first group
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {groups.map((g) => (
            <motion.button
              key={g.id}
              whileHover={{ y: -4 }}
              onClick={() => setView({ kind: 'detail', id: g.id })}
              className="text-left bg-white rounded-[2rem] border border-slate-100 p-7 shadow-sm hover:shadow-xl hover:border-indigo-100 transition-all group"
            >
              <div className="text-5xl mb-5">👥</div>
              <h3 className="text-xl font-black text-slate-900 leading-tight group-hover:text-indigo-600 transition-colors mb-2 truncate">
                {g.name}
              </h3>
              <div className="flex items-center gap-4 text-xs font-bold text-slate-400">
                <span>{g.member_count} {g.member_count === 1 ? 'member' : 'members'}</span>
                <span>·</span>
                <span>{g.trip_count} {g.trip_count === 1 ? 'trip' : 'trips'}</span>
              </div>
            </motion.button>
          ))}
        </div>
      )}

      <CreateGroupModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={(gid) => {
          setCreateOpen(false);
          fetchAll();
          setView({ kind: 'detail', id: gid });
        }}
      />
    </>
  );
}

function GroupInviteCard({ inv, onChange }: { inv: GroupInvitation; onChange: () => void }) {
  const [busy, setBusy] = useState(false);
  const accept = async () => {
    setBusy(true);
    try { await fetch(`${API}/groups/invitations/${inv.id}/accept`, { method: 'POST', headers: auth() }); }
    finally { setBusy(false); onChange(); }
  };
  const decline = async () => {
    setBusy(true);
    try { await fetch(`${API}/groups/invitations/${inv.id}/decline`, { method: 'DELETE', headers: auth() }); }
    finally { setBusy(false); onChange(); }
  };
  return (
    <div className="bg-white rounded-2xl border border-slate-100 p-5 shadow-sm">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-10 h-10 rounded-xl bg-indigo-50 flex items-center justify-center text-lg">👥</div>
        <div>
          <h4 className="text-base font-black text-slate-900 leading-tight">{inv.group.name}</h4>
          {inv.inviter && (
            <p className="text-xs text-slate-500 font-medium">from <strong className="text-slate-700">{inv.inviter.name}</strong></p>
          )}
        </div>
      </div>
      <div className="flex gap-2">
        <button
          onClick={accept}
          disabled={busy}
          className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-indigo-600 text-white rounded-lg font-black text-xs hover:bg-indigo-500 transition-all disabled:opacity-50"
        >
          {busy ? <Loader2 className="w-3 h-3 animate-spin" /> : <><Check className="w-3 h-3" /> Accept</>}
        </button>
        <button
          onClick={decline}
          disabled={busy}
          className="flex items-center justify-center gap-1.5 px-3 py-2 bg-slate-100 text-slate-500 rounded-lg font-black text-xs hover:bg-rose-50 hover:text-rose-500 transition-all disabled:opacity-50"
        >
          <XCircle className="w-3 h-3" /> Decline
        </button>
      </div>
    </div>
  );
}

function CreateGroupModal({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: (id: number) => void }) {
  const [name, setName] = useState('');
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setSaving(true); setErr('');
    try {
      const res = await fetch(`${API}/groups/`, { method: 'POST', headers: authJson(), body: JSON.stringify({ name }) });
      if (res.ok) {
        const data = await res.json();
        setName('');
        onCreated(data.id);
      } else {
        const j = await res.json().catch(() => null);
        setErr(j?.detail ?? `Failed (${res.status})`);
      }
    } catch { setErr('Network error'); } finally { setSaving(false); }
  };

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-slate-900/40 backdrop-blur-sm">
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            className="bg-white rounded-[2.5rem] w-full max-w-lg p-10 shadow-2xl relative"
          >
            <button onClick={onClose} className="absolute top-6 right-6 p-2 text-slate-400 hover:text-slate-600">
              <X className="w-6 h-6" />
            </button>
            <h3 className="text-3xl font-black text-slate-900 mb-2">New Group.</h3>
            <p className="text-slate-500 font-medium mb-8">Who do you travel with?</p>
            <form onSubmit={submit} className="space-y-5">
              <input
                autoFocus
                required
                type="text"
                placeholder="e.g. Ski Crew, Family 2026"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-2xl text-lg font-bold focus:bg-white focus:ring-4 focus:ring-indigo-50 focus:border-indigo-200 outline-none transition-all"
              />
              <button
                type="submit"
                disabled={saving || !name.trim()}
                className="w-full py-5 bg-slate-900 text-white rounded-2xl font-black text-lg hover:bg-indigo-600 transition-all shadow-xl shadow-indigo-100 disabled:opacity-50 flex items-center justify-center gap-3"
              >
                {saving ? <Loader2 className="w-6 h-6 animate-spin" /> : 'Create Group'}
              </button>
              {err && <p className="text-rose-500 text-sm font-bold text-center">{err}</p>}
            </form>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

function GroupDetailView({ groupId, onBack }: { groupId: number; onBack: () => void }) {
  const [group, setGroup] = useState<GroupDetail | null>(null);
  const [members, setMembers] = useState<GroupMember[]>([]);
  const [trips, setTrips] = useState<GroupTrip[]>([]);
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'members' | 'trips' | 'ideas'>('members');
  const [inviteOpen, setInviteOpen] = useState(false);
  const [attachOpen, setAttachOpen] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(false);

  const refetch = useCallback(async () => {
    setLoading(true);
    try {
      const [g, m, t, i] = await Promise.all([
        fetch(`${API}/groups/${groupId}`, { headers: auth() }).then((r) => r.ok ? r.json() : null),
        fetch(`${API}/groups/${groupId}/members`, { headers: auth() }).then((r) => r.ok ? r.json() : []),
        fetch(`${API}/groups/${groupId}/trips`, { headers: auth() }).then((r) => r.ok ? r.json() : []),
        fetch(`${API}/groups/${groupId}/ideas`, { headers: auth() }).then((r) => r.ok ? r.json() : []),
      ]);
      setGroup(g); setMembers(m); setTrips(t); setIdeas(i);
    } finally { setLoading(false); }
  }, [groupId]);

  useEffect(() => { refetch(); }, [refetch]);

  const isAdmin = group?.my_role === 'admin';

  const handleDelete = async () => {
    await fetch(`${API}/groups/${groupId}`, { method: 'DELETE', headers: auth() });
    onBack();
  };

  const handleRemoveMember = async (memberId: number) => {
    await fetch(`${API}/groups/${groupId}/members/${memberId}`, { method: 'DELETE', headers: auth() });
    refetch();
  };

  const handleDetachTrip = async (tripId: number) => {
    await fetch(`${API}/groups/${groupId}/trips/${tripId}`, { method: 'DELETE', headers: auth() });
    refetch();
  };

  if (loading && !group) {
    return <div className="flex items-center justify-center py-20"><Loader2 className="w-10 h-10 text-indigo-600 animate-spin" /></div>;
  }
  if (!group) {
    return (
      <div className="py-16 text-center">
        <p className="text-slate-500 font-bold mb-4">Group not found.</p>
        <button onClick={onBack} className="px-4 py-2 bg-slate-100 rounded-xl font-black text-sm">Back</button>
      </div>
    );
  }

  return (
    <>
      <button onClick={onBack} className="flex items-center gap-1.5 text-sm font-black text-slate-500 hover:text-slate-900 mb-6">
        <ChevronLeft className="w-4 h-4" /> All groups
      </button>

      <div className="flex items-start justify-between mb-8 gap-6">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-12 h-12 bg-indigo-50 rounded-2xl flex items-center justify-center text-2xl">👥</div>
            <h2 className="text-3xl font-black text-slate-900">{group.name}</h2>
          </div>
          <p className="text-slate-500 font-medium">
            {members.filter((m) => m.status === 'accepted').length} {members.filter((m) => m.status === 'accepted').length === 1 ? 'member' : 'members'} · {trips.length} {trips.length === 1 ? 'trip' : 'trips'}
          </p>
        </div>
        {isAdmin && (
          <button
            onClick={() => setDeleteConfirm(true)}
            className="px-4 py-2 text-slate-400 hover:text-rose-500 hover:bg-rose-50 rounded-xl font-black text-sm transition-colors flex items-center gap-1.5"
          >
            <Trash2 className="w-4 h-4" /> Delete group
          </button>
        )}
      </div>

      <div className="flex gap-2 border-b border-slate-100 mb-8">
        {(['members', 'trips', 'ideas'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-3 font-black text-sm capitalize border-b-2 transition-colors ${
              tab === t ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-slate-400 hover:text-slate-700'
            }`}
          >
            {t === 'ideas' ? 'Shared Library' : t}
          </button>
        ))}
      </div>

      {tab === 'members' && (
        <MembersTab
          members={members}
          isAdmin={!!isAdmin}
          onInvite={() => setInviteOpen(true)}
          onRemove={handleRemoveMember}
        />
      )}

      {tab === 'trips' && (
        <TripsTab
          trips={trips}
          isAdmin={!!isAdmin}
          onAttach={() => setAttachOpen(true)}
          onDetach={handleDetachTrip}
        />
      )}

      {tab === 'ideas' && <IdeasTab ideas={ideas} hasTrips={trips.length > 0} />}

      <InviteToGroupModal
        open={inviteOpen}
        groupId={groupId}
        onClose={() => setInviteOpen(false)}
        onInvited={() => { setInviteOpen(false); refetch(); }}
      />

      <AttachTripModal
        open={attachOpen}
        groupId={groupId}
        onClose={() => setAttachOpen(false)}
        onAttached={() => { setAttachOpen(false); refetch(); }}
      />

      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-[420px] p-6">
            <h3 className="text-base font-black text-slate-900 mb-1">Delete &ldquo;{group.name}&rdquo;?</h3>
            <p className="text-sm text-slate-500 mb-5">
              Members will be removed and attached trips will be detached (but the trips themselves will stay).
            </p>
            <div className="flex gap-2">
              <button onClick={handleDelete} className="flex-1 py-3 bg-rose-600 text-white rounded-xl text-sm font-black hover:bg-rose-500 transition-all">
                Delete Group
              </button>
              <button onClick={() => setDeleteConfirm(false)} className="flex-1 py-3 bg-slate-100 text-slate-600 rounded-xl text-sm font-black hover:bg-slate-200 transition-all">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function MembersTab({ members, isAdmin, onInvite, onRemove }: { members: GroupMember[]; isAdmin: boolean; onInvite: () => void; onRemove: (id: number) => void }) {
  return (
    <div>
      {isAdmin && (
        <button
          onClick={onInvite}
          className="mb-4 flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-xl font-black text-sm hover:bg-indigo-700 transition-all"
        >
          <Mail className="w-4 h-4" /> Invite member
        </button>
      )}
      <div className="bg-white rounded-2xl border border-slate-100 divide-y divide-slate-50">
        {members.map((m) => (
          <div key={m.id} className="flex items-center gap-4 p-4">
            <div className="w-10 h-10 rounded-full bg-indigo-600 flex items-center justify-center text-white font-black text-xs">
              {m.user.name?.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2) || '?'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-black text-slate-900 truncate">{m.user.name || m.user.email}</p>
              <p className="text-xs text-slate-400 font-bold truncate">{m.user.email}</p>
            </div>
            <span className={`px-2.5 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest ${
              m.role === 'admin' ? 'bg-indigo-50 text-indigo-600' : 'bg-slate-100 text-slate-500'
            }`}>
              {m.role}
            </span>
            {m.status === 'invited' && (
              <span className="px-2.5 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest bg-amber-50 text-amber-600">pending</span>
            )}
            {isAdmin && m.status === 'accepted' && m.role !== 'admin' && (
              <button onClick={() => onRemove(m.id)} className="p-1.5 text-slate-300 hover:text-rose-500 rounded-lg">
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function TripsTab({ trips, isAdmin, onAttach, onDetach }: { trips: GroupTrip[]; isAdmin: boolean; onAttach: () => void; onDetach: (id: number) => void }) {
  if (trips.length === 0) {
    return (
      <div className="py-16 text-center">
        <div className="w-16 h-16 bg-slate-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <MapPin className="w-8 h-8 text-slate-300" />
        </div>
        <h4 className="text-lg font-black text-slate-900 mb-2">No trips yet</h4>
        <p className="text-sm text-slate-500 font-medium max-w-sm mx-auto mb-5">
          Attach existing trips here to build this group&apos;s shared library over time.
        </p>
        {isAdmin && (
          <button onClick={onAttach} className="px-5 py-2.5 bg-indigo-600 text-white rounded-xl font-black text-sm hover:bg-indigo-700 transition-all flex items-center gap-2 mx-auto">
            <Link2 className="w-4 h-4" /> Attach a trip
          </button>
        )}
      </div>
    );
  }
  return (
    <div>
      {isAdmin && (
        <button
          onClick={onAttach}
          className="mb-4 flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-xl font-black text-sm hover:bg-indigo-700 transition-all"
        >
          <Link2 className="w-4 h-4" /> Attach a trip
        </button>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {trips.map((t) => (
          <div key={t.id} className="bg-white rounded-2xl border border-slate-100 p-5 flex items-center justify-between">
            <div className="min-w-0">
              <p className="text-base font-black text-slate-900 truncate">{t.name}</p>
              <p className="text-xs text-slate-400 font-bold">
                {t.start_date ? new Date(t.start_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'Dates TBD'}
              </p>
            </div>
            {isAdmin && (
              <button onClick={() => onDetach(t.id)} title="Detach trip" className="p-1.5 text-slate-300 hover:text-rose-500 rounded-lg ml-2">
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function IdeasTab({ ideas, hasTrips }: { ideas: Idea[]; hasTrips: boolean }) {
  if (ideas.length === 0) {
    return (
      <div className="py-16 text-center">
        <div className="w-16 h-16 bg-amber-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <Lightbulb className="w-8 h-8 text-amber-300" />
        </div>
        <h4 className="text-lg font-black text-slate-900 mb-2">
          {hasTrips ? 'No ideas yet' : 'Attach a trip to start your library'}
        </h4>
        <p className="text-sm text-slate-500 font-medium max-w-sm mx-auto">
          Ideas from all trips attached to this group show up here — your shared travel memory.
        </p>
      </div>
    );
  }
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {ideas.map((idea) => (
        <div key={idea.id} className="bg-white rounded-2xl border border-slate-100 p-5">
          <p className="text-base font-black text-slate-900 leading-tight mb-1">{idea.title}</p>
          {idea.added_by && (
            <p className="text-xs text-slate-400 font-bold">added by {idea.added_by}</p>
          )}
        </div>
      ))}
    </div>
  );
}

function InviteToGroupModal({ open, groupId, onClose, onInvited }: { open: boolean; groupId: number; onClose: () => void; onInvited: () => void }) {
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<'admin' | 'member'>('member');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true); setErr('');
    try {
      const res = await fetch(`${API}/groups/${groupId}/invite`, {
        method: 'POST', headers: authJson(), body: JSON.stringify({ email, role }),
      });
      if (res.ok) { setEmail(''); onInvited(); }
      else {
        const j = await res.json().catch(() => null);
        setErr(j?.detail ?? `Failed (${res.status})`);
      }
    } finally { setBusy(false); }
  };

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-slate-900/40 backdrop-blur-sm">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }}
            className="bg-white rounded-3xl w-full max-w-md p-8 shadow-2xl relative"
          >
            <button onClick={onClose} className="absolute top-4 right-4 p-2 text-slate-400 hover:text-slate-600">
              <X className="w-5 h-5" />
            </button>
            <h3 className="text-2xl font-black text-slate-900 mb-1">Invite member</h3>
            <p className="text-slate-500 font-medium text-sm mb-6">They&apos;ll get a notification to accept.</p>
            <form onSubmit={submit} className="space-y-4">
              <input
                autoFocus required type="email" placeholder="friend@example.com"
                value={email} onChange={(e) => setEmail(e.target.value)}
                className="w-full px-5 py-3.5 bg-slate-50 border border-slate-100 rounded-xl text-base font-bold focus:bg-white focus:ring-4 focus:ring-indigo-50 focus:border-indigo-200 outline-none"
              />
              <select
                value={role}
                onChange={(e) => setRole(e.target.value as 'admin' | 'member')}
                className="w-full px-5 py-3.5 bg-slate-50 border border-slate-100 rounded-xl text-base font-bold"
              >
                <option value="member">Member</option>
                <option value="admin">Admin</option>
              </select>
              <button
                type="submit" disabled={busy || !email}
                className="w-full py-3.5 bg-indigo-600 text-white rounded-xl font-black text-base hover:bg-indigo-700 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {busy ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Send invite'}
              </button>
              {err && <p className="text-rose-500 text-sm font-bold text-center">{err}</p>}
            </form>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

function AttachTripModal({ open, groupId, onClose, onAttached }: { open: boolean; groupId: number; onClose: () => void; onAttached: () => void }) {
  const [trips, setTrips] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [attachingId, setAttachingId] = useState<number | null>(null);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    fetch(`${API}/trips/`, { headers: auth() })
      .then((r) => r.ok ? r.json() : [])
      .then((data) => setTrips(data.filter((t: any) => t.my_role === 'admin' && !t.group_id)))
      .finally(() => setLoading(false));
  }, [open]);

  const attach = async (tripId: number) => {
    setAttachingId(tripId);
    try {
      await fetch(`${API}/groups/${groupId}/trips/${tripId}`, { method: 'POST', headers: auth() });
      onAttached();
    } finally { setAttachingId(null); }
  };

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-slate-900/40 backdrop-blur-sm">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }}
            className="bg-white rounded-3xl w-full max-w-md p-8 shadow-2xl relative max-h-[80vh] overflow-hidden flex flex-col"
          >
            <button onClick={onClose} className="absolute top-4 right-4 p-2 text-slate-400 hover:text-slate-600">
              <X className="w-5 h-5" />
            </button>
            <h3 className="text-2xl font-black text-slate-900 mb-1">Attach a trip</h3>
            <p className="text-slate-500 font-medium text-sm mb-5">
              Pick one of your admin trips. Only trips not already in another group are shown.
            </p>
            <div className="overflow-y-auto flex-1 -mx-2 px-2">
              {loading ? (
                <div className="flex items-center justify-center py-10">
                  <Loader2 className="w-6 h-6 text-indigo-600 animate-spin" />
                </div>
              ) : trips.length === 0 ? (
                <p className="text-sm text-slate-400 font-bold text-center py-8">
                  No eligible trips. Create one or detach it from another group first.
                </p>
              ) : (
                <div className="space-y-2">
                  {trips.map((t) => (
                    <button
                      key={t.id}
                      onClick={() => attach(t.id)}
                      disabled={attachingId === t.id}
                      className="w-full flex items-center justify-between text-left p-4 bg-slate-50 rounded-xl hover:bg-indigo-50 transition-colors disabled:opacity-50"
                    >
                      <div>
                        <p className="text-sm font-black text-slate-900">{t.name}</p>
                        <p className="text-xs text-slate-400 font-bold">
                          {t.start_date ? new Date(t.start_date).toLocaleDateString() : 'Dates TBD'}
                        </p>
                      </div>
                      {attachingId === t.id ? (
                        <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
                      ) : (
                        <Link2 className="w-4 h-4 text-indigo-600" />
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

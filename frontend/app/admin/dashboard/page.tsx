'use client';

import { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Users, Zap, Map, LogOut, Loader2, Search, ChevronDown, RefreshCw } from 'lucide-react';
import useAdminAuth from '@/hooks/useAdminAuth';

const API = process.env.NEXT_PUBLIC_API_URL ?? '';

type Section = 'users' | 'token-usage' | 'maps-usage';

// ── Helpers ──────────────────────────────────────────────────────────────────

function KpiCard({ label, value, subtitle }: { label: string; value: string | number; subtitle?: string }) {
  return (
    <div className="bg-white rounded-lg p-4 shadow-sm border border-slate-200">
      <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-bold text-slate-900 mt-1">{value}</p>
      {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
    </div>
  );
}

function SkeletonRows({ cols }: { cols: number }) {
  return (
    <>
      {Array.from({ length: 5 }).map((_, i) => (
        <tr key={i} className="animate-pulse">
          {Array.from({ length: cols }).map((_, j) => (
            <td key={j} className="px-4 py-3">
              <div className="h-4 bg-slate-200 rounded w-3/4" />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

function formatDate(iso: string | null) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function generateMonths(): string[] {
  const months: string[] = [];
  const now = new Date();
  for (let i = 0; i < 12; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    months.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`);
  }
  return months;
}

function MultiSelectDropdown({
  label,
  options,
  selected,
  onToggle,
}: {
  label: string;
  options: { key: string; label: string }[];
  selected: string[];
  onToggle: (key: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const selectedLabels = options.filter((o) => selected.includes(o.key)).map((o) => o.label);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-300 text-sm bg-white hover:border-slate-400 focus:ring-2 focus:ring-blue-500 min-w-[180px]"
      >
        <span className="flex-1 text-left truncate text-slate-700">
          {selectedLabels.length === options.length
            ? `All ${label}`
            : selectedLabels.length === 0
              ? `Select ${label}`
              : selectedLabels.join(', ')}
        </span>
        <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="absolute z-20 mt-1 w-full bg-white border border-slate-200 rounded-lg shadow-lg py-1">
          {options.map((opt) => (
            <label
              key={opt.key}
              className="flex items-center gap-2 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 cursor-pointer"
            >
              <input
                type="checkbox"
                checked={selected.includes(opt.key)}
                onChange={() => onToggle(opt.key)}
                className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
              {opt.label}
            </label>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main Dashboard ───────────────────────────────────────────────────────────

export default function AdminDashboardPage() {
  const { adminToken, logout, isLoading } = useAdminAuth();
  const router = useRouter();
  const [refreshKey, setRefreshKey] = useState(0);

  const [section, setSection] = useState<Section>(() => {
    if (typeof window !== 'undefined') {
      const hash = window.location.hash.replace('#', '') as Section;
      if (['users', 'token-usage', 'maps-usage'].includes(hash)) return hash;
    }
    return 'users';
  });

  const switchSection = (s: Section) => {
    setSection(s);
    window.location.hash = s;
  };

  useEffect(() => {
    if (!isLoading && !adminToken) {
      router.push('/admin');
    }
  }, [isLoading, adminToken, router]);

  if (isLoading || !adminToken) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-slate-50">
        <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
      </div>
    );
  }

  const navItems: { key: Section; label: string; icon: React.ReactNode }[] = [
    { key: 'users', label: 'Users', icon: <Users className="w-4 h-4" /> },
    { key: 'token-usage', label: 'AI Token Usage', icon: <Zap className="w-4 h-4" /> },
    { key: 'maps-usage', label: 'Google Maps API', icon: <Map className="w-4 h-4" /> },
  ];

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-56 bg-slate-900 flex flex-col">
        <div className="flex items-center gap-2 px-5 py-5">
          <div className="w-2.5 h-2.5 rounded-sm bg-blue-500" />
          <span className="text-sm font-semibold text-white">Roammate Admin</span>
        </div>
        <nav className="flex-1 px-3 space-y-1 mt-2">
          {navItems.map((item) => (
            <button
              key={item.key}
              onClick={() => switchSection(item.key)}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                section === item.key
                  ? 'bg-slate-800 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              {item.icon}
              {item.label}
            </button>
          ))}
        </nav>
        <div className="px-3 pb-4">
          <button
            onClick={logout}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-sm font-medium text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Logout
          </button>
        </div>
      </aside>

      {/* Content */}
      <main className="flex-1 bg-slate-50 overflow-y-auto p-6">
        <div className="flex justify-end mb-4">
          <button
            onClick={() => setRefreshKey((k) => k + 1)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 text-sm text-slate-600 hover:text-slate-900 hover:border-slate-400 bg-white transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </button>
        </div>
        {section === 'users' && <UsersSection token={adminToken} key={`users-${refreshKey}`} />}
        {section === 'token-usage' && <TokenUsageSection token={adminToken} key={`tokens-${refreshKey}`} />}
        {section === 'maps-usage' && <MapsUsageSection token={adminToken} key={`maps-${refreshKey}`} />}
      </main>
    </div>
  );
}

// ── Users Section ────────────────────────────────────────────────────────────

function UsersSection({ token }: { token: string }) {
  const [data, setData] = useState<any>(null);
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetch(`${API}/admin/users`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.json())
      .then(setData);
  }, [token]);

  const filtered = useMemo(() => {
    if (!data) return [];
    if (!search) return data.users;
    const q = search.toLowerCase();
    return data.users.filter(
      (u: any) => u.name?.toLowerCase().includes(q) || u.email?.toLowerCase().includes(q)
    );
  }, [data, search]);

  const newThisMonth = useMemo(() => {
    if (!data) return 0;
    const thirtyDaysAgo = new Date(Date.now() - 30 * 86400_000);
    return data.users.filter((u: any) => u.created_at && new Date(u.created_at) > thirtyDaysAgo).length;
  }, [data]);

  return (
    <div>
      <h2 className="text-lg font-semibold text-slate-900 mb-4">Users</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
        <KpiCard label="Total Users" value={data?.total ?? '—'} />
        <KpiCard label="New This Month" value={newThisMonth} subtitle="Last 30 days" />
      </div>
      <div className="mb-4 relative max-w-xs">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <input
          type="text"
          placeholder="Search name or email..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-9 pr-3 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="text-left px-4 py-2.5 font-medium text-slate-600">Name</th>
              <th className="text-left px-4 py-2.5 font-medium text-slate-600">Email</th>
              <th className="text-left px-4 py-2.5 font-medium text-slate-600">Joined</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {!data ? (
              <SkeletonRows cols={3} />
            ) : (
              filtered.map((u: any) => (
                <tr key={u.id} className="hover:bg-slate-50">
                  <td className="px-4 py-2.5 text-slate-900">{u.name || '—'}</td>
                  <td className="px-4 py-2.5 text-slate-600">{u.email}</td>
                  <td className="px-4 py-2.5 text-slate-500">{formatDate(u.created_at)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Token Usage Section ──────────────────────────────────────────────────────

function TokenUsageSection({ token }: { token: string }) {
  const months = useMemo(() => generateMonths(), []);
  const [providerOptions, setProviderOptions] = useState<Record<string, string[]>>({});
  const [provider, setProvider] = useState('');
  const [model, setModel] = useState('');
  const [month, setMonth] = useState('');
  const [day, setDay] = useState('');
  const [search, setSearch] = useState('');
  const [summary, setSummary] = useState<any>(null);
  const [users, setUsers] = useState<any[] | null>(null);

  useEffect(() => {
    fetch(`${API}/admin/token-usage/options`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.json())
      .then((d) => setProviderOptions(d.providers || {}));
  }, [token]);

  const availableModels = useMemo(() => {
    if (provider) return providerOptions[provider] || [];
    return Object.values(providerOptions).flat();
  }, [provider, providerOptions]);

  const buildQs = useCallback(() => {
    const p = new URLSearchParams();
    if (provider) p.set('provider', provider);
    if (model) p.set('model', model);
    if (month) p.set('month', month);
    if (day) p.set('day', day);
    return p.toString();
  }, [provider, model, month, day]);

  useEffect(() => {
    const qs = buildQs();
    const h = { Authorization: `Bearer ${token}` };
    fetch(`${API}/admin/token-usage/summary?${qs}`, { headers: h })
      .then((r) => r.json())
      .then(setSummary);
    fetch(`${API}/admin/token-usage/users?${qs}`, { headers: h })
      .then((r) => r.json())
      .then(setUsers);
  }, [token, buildQs]);

  const filtered = useMemo(() => {
    if (!users) return [];
    if (!search) return users;
    const q = search.toLowerCase();
    return users.filter(
      (u: any) => u.name?.toLowerCase().includes(q) || u.email?.toLowerCase().includes(q)
    );
  }, [users, search]);

  return (
    <div>
      <h2 className="text-lg font-semibold text-slate-900 mb-4">AI Token Usage</h2>

      {/* Filters first */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <select
          value={provider}
          onChange={(e) => { setProvider(e.target.value); setModel(''); }}
          className="px-3 py-2 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All Providers</option>
          {Object.keys(providerOptions).map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
        <select
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="px-3 py-2 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All Models</option>
          {availableModels.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
        <select
          value={month}
          onChange={(e) => { setMonth(e.target.value); setDay(''); }}
          className="px-3 py-2 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All Months</option>
          {months.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
        <input
          type="date"
          value={day}
          onChange={(e) => { setDay(e.target.value); setMonth(''); }}
          className="px-3 py-2 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-blue-500"
        />
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search user..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 pr-3 py-2 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <KpiCard label="Total Tokens" value={summary?.total_tokens?.toLocaleString() ?? '—'} />
        <KpiCard label="Total Cost (USD)" value={summary ? `$${summary.total_cost_usd}` : '—'} />
        <KpiCard label="Avg Tokens/Request" value={summary?.avg_tokens_per_request?.toLocaleString() ?? '—'} />
        <KpiCard label="Top Model" value={summary?.top_model ?? '—'} />
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg border border-slate-200 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="text-left px-4 py-2.5 font-medium text-slate-600">User</th>
              <th className="text-left px-4 py-2.5 font-medium text-slate-600">Email</th>
              <th className="text-right px-4 py-2.5 font-medium text-slate-600">Tokens In</th>
              <th className="text-right px-4 py-2.5 font-medium text-slate-600">Tokens Out</th>
              <th className="text-right px-4 py-2.5 font-medium text-slate-600">Total</th>
              <th className="text-right px-4 py-2.5 font-medium text-slate-600">Est. Cost</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {users === null ? (
              <SkeletonRows cols={6} />
            ) : (
              filtered.map((u: any) => (
                <tr key={u.user_id} className="hover:bg-slate-50">
                  <td className="px-4 py-2.5 text-slate-900">{u.name || '—'}</td>
                  <td className="px-4 py-2.5 text-slate-600">{u.email || '—'}</td>
                  <td className="px-4 py-2.5 text-right text-slate-700">{u.tokens_in.toLocaleString()}</td>
                  <td className="px-4 py-2.5 text-right text-slate-700">{u.tokens_out.toLocaleString()}</td>
                  <td className="px-4 py-2.5 text-right font-medium text-slate-900">{u.tokens_total.toLocaleString()}</td>
                  <td className="px-4 py-2.5 text-right text-slate-700">${u.cost_usd}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Maps Usage Section ───────────────────────────────────────────────────────

const API_CATEGORIES: { key: string; label: string; ops: string[] }[] = [
  { key: 'places', label: 'Places', ops: ['find_place', 'place_details'] },
  { key: 'places_new', label: 'Places New', ops: ['photo_url'] },
  { key: 'directions', label: 'Directions', ops: ['directions'] },
  { key: 'routes', label: 'Routes', ops: ['enrich_batch'] },
];

function MapsUsageSection({ token }: { token: string }) {
  const months = useMemo(() => generateMonths(), []);
  const [selectedCategories, setSelectedCategories] = useState<string[]>(
    API_CATEGORIES.map((c) => c.key)
  );
  const [month, setMonth] = useState('');
  const [day, setDay] = useState('');
  const [search, setSearch] = useState('');
  const [summary, setSummary] = useState<any>(null);
  const [users, setUsers] = useState<any[] | null>(null);

  const activeCategories = useMemo(
    () => API_CATEGORIES.filter((c) => selectedCategories.includes(c.key)),
    [selectedCategories]
  );

  const selectedOps = useMemo(
    () => activeCategories.flatMap((c) => c.ops),
    [activeCategories]
  );

  const buildQs = useCallback(() => {
    const p = new URLSearchParams();
    selectedOps.forEach((o) => p.append('ops', o));
    if (month) p.set('month', month);
    if (day) p.set('day', day);
    return p.toString();
  }, [selectedOps, month, day]);

  useEffect(() => {
    if (selectedOps.length === 0) {
      setSummary({ total_calls: 0, cache_hit_rate_pct: 0, error_rate_pct: 0, total_cost_usd: 0, by_op: {} });
      setUsers([]);
      return;
    }
    const qs = buildQs();
    const h = { Authorization: `Bearer ${token}` };
    fetch(`${API}/admin/maps-usage/summary?${qs}`, { headers: h })
      .then((r) => r.json())
      .then(setSummary);
    fetch(`${API}/admin/maps-usage/users?${qs}`, { headers: h })
      .then((r) => r.json())
      .then(setUsers);
  }, [token, buildQs, selectedOps.length]);

  const filtered = useMemo(() => {
    if (!users) return [];
    if (!search) return users;
    const q = search.toLowerCase();
    return users.filter(
      (u: any) => u.name?.toLowerCase().includes(q) || u.email?.toLowerCase().includes(q)
    );
  }, [users, search]);

  const toggleCategory = (key: string) => {
    setSelectedCategories((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  };

  const callsForCategory = (userRow: any, cat: typeof API_CATEGORIES[number]) => {
    const byOp: Record<string, number> = userRow.calls_by_op || {};
    return cat.ops.reduce((sum, op) => sum + (byOp[op] || 0), 0);
  };

  return (
    <div>
      <h2 className="text-lg font-semibold text-slate-900 mb-4">Google Maps API Usage</h2>

      {/* Category selection dropdown first */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <MultiSelectDropdown
          label="API Categories"
          options={API_CATEGORIES.map((c) => ({ key: c.key, label: c.label }))}
          selected={selectedCategories}
          onToggle={toggleCategory}
        />
        <select
          value={month}
          onChange={(e) => { setMonth(e.target.value); setDay(''); }}
          className="px-3 py-2 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All Months</option>
          {months.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
        <input
          type="date"
          value={day}
          onChange={(e) => { setDay(e.target.value); setMonth(''); }}
          className="px-3 py-2 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-blue-500"
        />
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search user..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 pr-3 py-2 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* KPI Cards — one per selected API category */}
      <div className={`grid grid-cols-2 md:grid-cols-${Math.min(activeCategories.length + 2, 6)} gap-4 mb-6`}>
        {activeCategories.map((cat) => {
          const count = cat.ops.reduce((sum, op) => sum + ((summary?.by_op || {})[op] || 0), 0);
          return <KpiCard key={cat.key} label={`${cat.label} Calls`} value={count.toLocaleString()} />;
        })}
        <KpiCard label="Cache Hit Rate" value={summary ? `${summary.cache_hit_rate_pct}%` : '—'} />
        <KpiCard label="Total Cost (USD)" value={summary ? `$${summary.total_cost_usd}` : '—'} />
      </div>

      {/* Table with dynamic columns per category */}
      <div className="bg-white rounded-lg border border-slate-200 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="text-left px-4 py-2.5 font-medium text-slate-600">User</th>
              <th className="text-left px-4 py-2.5 font-medium text-slate-600">Email</th>
              {activeCategories.map((cat) => (
                <th key={cat.key} className="text-right px-4 py-2.5 font-medium text-slate-600">{cat.label}</th>
              ))}
              <th className="text-right px-4 py-2.5 font-medium text-slate-600">Est. Cost</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {users === null ? (
              <SkeletonRows cols={3 + activeCategories.length} />
            ) : (
              filtered.map((u: any) => (
                <tr key={u.user_id} className="hover:bg-slate-50">
                  <td className="px-4 py-2.5 text-slate-900">{u.name || '—'}</td>
                  <td className="px-4 py-2.5 text-slate-600">{u.email || '—'}</td>
                  {activeCategories.map((cat) => (
                    <td key={cat.key} className="px-4 py-2.5 text-right font-medium text-slate-900">
                      {callsForCategory(u, cat).toLocaleString()}
                    </td>
                  ))}
                  <td className="px-4 py-2.5 text-right text-slate-700">${u.cost_usd}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

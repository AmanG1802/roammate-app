'use client';

import { useEffect, useRef, useState } from 'react';
import { Camera, Pencil, Check, X, Eye, EyeOff, AlertTriangle, Loader2, Info, Upload } from 'lucide-react';
import type { ProfileData } from '@/hooks/useProfile';

const CURRENCIES = ['INR', 'USD', 'EUR', 'GBP', 'AUD', 'JPY', 'CAD', 'SGD'];
const TIMEZONES = [
  'Asia/Kolkata',
  'UTC',
  'America/New_York',
  'America/Los_Angeles',
  'America/Chicago',
  'Europe/London',
  'Europe/Paris',
  'Europe/Berlin',
  'Asia/Tokyo',
  'Asia/Singapore',
  'Asia/Dubai',
  'Australia/Sydney',
];

// Fixed width shared by all three preference fields so they look uniform
const PREF_WIDTH = 'w-52';

type EditProfileProps = {
  profile: ProfileData;
  onUpdate: (updates: Record<string, any>) => Promise<boolean>;
  onDeleteAccount: () => Promise<boolean>;
};

function strengthScore(pw: string): number {
  let score = 0;
  if (pw.length >= 8) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  return score;
}

// ─── Inline text field (compact variant keeps a fixed width) ──────────────────
function InlineField({
  label,
  value,
  onSave,
  type = 'text',
  compact = false,
  placeholder,
}: {
  label: string;
  value: string;
  onSave: (v: string) => Promise<boolean>;
  type?: string;
  compact?: boolean;
  placeholder?: string;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { if (editing) inputRef.current?.focus(); }, [editing]);
  useEffect(() => { setDraft(value); }, [value]);

  const commit = async () => {
    if (draft === value) { setEditing(false); return; }
    setSaving(true);
    const ok = await onSave(draft);
    setSaving(false);
    if (ok) { setSaved(true); setTimeout(() => setSaved(false), 1500); }
    setEditing(false);
  };
  const cancel = () => { setDraft(value); setEditing(false); };

  if (editing) {
    return (
      <div className={`flex items-center gap-2 ${compact ? PREF_WIDTH : ''}`}>
        <input
          ref={inputRef}
          type={type}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') commit(); if (e.key === 'Escape') cancel(); }}
          className={`text-sm font-bold text-slate-800 border border-indigo-400 rounded-lg px-3 py-1.5 outline-none focus:ring-2 focus:ring-indigo-500 ${compact ? 'flex-1' : 'flex-1'}`}
        />
        <button onClick={commit} disabled={saving} className="text-indigo-600 hover:text-indigo-800 cursor-pointer shrink-0">
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
        </button>
        <button onClick={cancel} className="text-slate-400 hover:text-slate-600 cursor-pointer shrink-0">
          <X className="w-4 h-4" />
        </button>
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-2 group ${compact ? PREF_WIDTH : ''}`}>
      <span className={`text-sm font-bold truncate ${saved ? 'text-green-600' : 'text-slate-800'}`}>
        {saved ? '✓ Saved' : value || <span className="text-slate-400 italic">{placeholder ?? 'Not set'}</span>}
      </span>
      <button
        onClick={() => setEditing(true)}
        className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-indigo-600 transition-all cursor-pointer shrink-0"
        aria-label={`Edit ${label}`}
      >
        <Pencil className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}

// ─── Select field (fixed width) ───────────────────────────────────────────────
function SelectField({
  label,
  value,
  options,
  onSave,
}: {
  label: string;
  value: string;
  options: string[];
  onSave: (v: string) => Promise<boolean>;
}) {
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const handleChange = async (v: string) => {
    setSaving(true);
    const ok = await onSave(v);
    setSaving(false);
    if (ok) { setSaved(true); setTimeout(() => setSaved(false), 1500); }
  };

  return (
    <div className="flex items-center gap-2">
      <select
        value={value}
        onChange={(e) => handleChange(e.target.value)}
        disabled={saving}
        className={`${PREF_WIDTH} text-sm font-bold text-slate-800 border border-slate-200 rounded-lg px-3 py-1.5 bg-white focus:ring-2 focus:ring-indigo-500 outline-none cursor-pointer disabled:opacity-60`}
      >
        {options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
      {saved && <span className="text-xs text-green-600 font-bold">✓</span>}
    </div>
  );
}

// ─── Textarea with tooltip ────────────────────────────────────────────────────
function TextareaField({
  value,
  onSave,
  maxLength = 280,
}: {
  value: string;
  onSave: (v: string) => Promise<boolean>;
  maxLength?: number;
}) {
  const [draft, setDraft] = useState(value);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);

  useEffect(() => { setDraft(value); }, [value]);

  const handleBlur = async () => {
    if (draft === value) return;
    setSaving(true);
    const ok = await onSave(draft);
    setSaving(false);
    if (ok) { setSaved(true); setTimeout(() => setSaved(false), 1500); }
  };

  return (
    <div className="relative">
      <div className="flex items-center gap-1.5 mb-1">
        <label className="text-xs font-black text-slate-500 uppercase tracking-wider">Travel Style</label>
        <div className="relative">
          <button
            type="button"
            onMouseEnter={() => setShowTooltip(true)}
            onMouseLeave={() => setShowTooltip(false)}
            onFocus={() => setShowTooltip(true)}
            onBlur={() => setShowTooltip(false)}
            className="text-slate-400 hover:text-indigo-500 transition-colors cursor-help"
            aria-label="Travel style info"
          >
            <Info className="w-3.5 h-3.5" />
          </button>
          {showTooltip && (
            <div className="absolute left-5 top-0 z-10 w-56 bg-slate-800 text-white text-xs font-medium rounded-lg px-3 py-2 shadow-lg pointer-events-none">
              Integration to the AI Chat service coming soon
              <div className="absolute -left-1 top-2 w-2 h-2 bg-slate-800 rotate-45" />
            </div>
          )}
        </div>
      </div>
      <textarea
        value={draft}
        onChange={(e) => { if (e.target.value.length <= maxLength) setDraft(e.target.value); }}
        onBlur={handleBlur}
        rows={3}
        placeholder="A few words about your travel style…"
        className="w-full text-sm font-medium text-slate-800 border border-slate-200 rounded-lg px-3 py-2 resize-none focus:ring-2 focus:ring-indigo-500 outline-none"
      />
      <div className="flex items-center justify-between mt-1">
        <span className="text-xs text-slate-400">{draft.length}/{maxLength}</span>
        {saving && <span className="text-xs text-slate-400">Saving…</span>}
        {saved && <span className="text-xs text-green-600 font-bold">✓ Saved</span>}
      </div>
    </div>
  );
}

// ─── Password block ───────────────────────────────────────────────────────────
function PasswordBlock({ onSave }: { onSave: (current: string, next: string) => Promise<boolean> }) {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNext, setShowNext] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const score = strengthScore(next);
  const strengthLabels = ['', 'Weak', 'Fair', 'Good', 'Strong'];
  const strengthColors = ['', 'bg-red-400', 'bg-orange-400', 'bg-yellow-400', 'bg-green-500'];

  const handleSubmit = async () => {
    setError('');
    if (!current) { setError('Enter your current password.'); return; }
    if (next.length < 8) { setError('New password must be at least 8 characters.'); return; }
    if (next !== confirm) { setError('Passwords do not match.'); return; }
    setSaving(true);
    const ok = await onSave(current, next);
    setSaving(false);
    if (ok) {
      setSuccess(true);
      setCurrent(''); setNext(''); setConfirm('');
      setTimeout(() => setSuccess(false), 2000);
    } else {
      setError('Current password is incorrect.');
    }
  };

  return (
    <div className="space-y-3">
      <div className="relative">
        <input
          type={showCurrent ? 'text' : 'password'}
          placeholder="Current password"
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
          className="w-full text-sm font-medium border border-slate-200 rounded-lg px-3 py-2 pr-10 focus:ring-2 focus:ring-indigo-500 outline-none"
        />
        <button onClick={() => setShowCurrent(!showCurrent)} className="absolute right-3 top-2.5 text-slate-400 cursor-pointer">
          {showCurrent ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      </div>
      <div className="relative">
        <input
          type={showNext ? 'text' : 'password'}
          placeholder="New password"
          value={next}
          onChange={(e) => setNext(e.target.value)}
          className="w-full text-sm font-medium border border-slate-200 rounded-lg px-3 py-2 pr-10 focus:ring-2 focus:ring-indigo-500 outline-none"
        />
        <button onClick={() => setShowNext(!showNext)} className="absolute right-3 top-2.5 text-slate-400 cursor-pointer">
          {showNext ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      </div>
      {next && (
        <div className="flex items-center gap-2">
          <div className="flex-1 flex gap-1">
            {[1, 2, 3, 4].map((n) => (
              <div key={n} className={`h-1 flex-1 rounded-full ${score >= n ? strengthColors[score] : 'bg-slate-200'} transition-colors`} />
            ))}
          </div>
          <span className="text-xs font-bold text-slate-500">{strengthLabels[score]}</span>
        </div>
      )}
      <input
        type="password"
        placeholder="Confirm new password"
        value={confirm}
        onChange={(e) => setConfirm(e.target.value)}
        className="w-full text-sm font-medium border border-slate-200 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 outline-none"
      />
      {error && <p className="text-xs text-rose-600 font-bold">{error}</p>}
      {success && <p className="text-xs text-green-600 font-bold">✓ Password updated!</p>}
      <button
        onClick={handleSubmit}
        disabled={saving}
        className="px-4 py-2 text-sm font-bold bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 cursor-pointer"
      >
        {saving ? 'Updating…' : 'Update Password'}
      </button>
    </div>
  );
}

// ─── Delete account modal ─────────────────────────────────────────────────────
function DeleteAccountModal({ email, onConfirm, onCancel }: { email: string; onConfirm: () => Promise<void>; onCancel: () => void }) {
  const [input, setInput] = useState('');
  const [deleting, setDeleting] = useState(false);
  const handleDelete = async () => {
    if (input !== email) return;
    setDeleting(true);
    await onConfirm();
  };
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-8">
        <div className="flex items-center gap-3 mb-4">
          <AlertTriangle className="w-5 h-5 text-rose-500" />
          <h3 className="text-lg font-black text-slate-900">Delete Account</h3>
        </div>
        <p className="text-sm text-slate-600 mb-4">
          This is permanent. Type your email <span className="font-black text-slate-800">{email}</span> to confirm.
        </p>
        <input
          type="email"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={email}
          className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm mb-4 focus:ring-2 focus:ring-rose-400 outline-none"
        />
        <div className="flex gap-3 justify-end">
          <button onClick={onCancel} className="px-4 py-2 text-sm font-bold text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 cursor-pointer">Cancel</button>
          <button
            onClick={handleDelete}
            disabled={input !== email || deleting}
            className="px-4 py-2 text-sm font-bold text-white bg-rose-500 rounded-lg hover:bg-rose-600 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
          >
            {deleting ? 'Deleting…' : 'Delete my account'}
          </button>
        </div>
      </div>
    </div>
  );
}

const CROP_CONTAINER = 320;

// ─── Camera modal ─────────────────────────────────────────────────────────────
function CameraModal({ onCapture, onClose }: { onCapture: (dataUrl: string) => void; onClose: () => void }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' }, audio: false })
      .then((s) => {
        streamRef.current = s;
        if (videoRef.current) {
          videoRef.current.srcObject = s;
          videoRef.current.onloadedmetadata = () => setReady(true);
        }
      })
      .catch(() => setError('Camera access denied or unavailable. Please allow camera permissions.'));
    return () => { streamRef.current?.getTracks().forEach((t) => t.stop()); };
  }, []);

  const capture = () => {
    const v = videoRef.current;
    if (!v) return;
    const canvas = document.createElement('canvas');
    canvas.width = v.videoWidth;
    canvas.height = v.videoHeight;
    canvas.getContext('2d')!.drawImage(v, 0, 0);
    streamRef.current?.getTracks().forEach((t) => t.stop());
    onCapture(canvas.toDataURL('image/jpeg', 0.92));
  };

  const close = () => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    onClose();
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-900/80 backdrop-blur-sm">
      <div className="bg-white rounded-2xl overflow-hidden shadow-2xl flex flex-col w-[420px]">
        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-100 shrink-0">
          <span className="text-sm font-black text-slate-900">Take Photo</span>
          <button onClick={close} className="text-slate-400 hover:text-slate-600 cursor-pointer">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="relative bg-black overflow-hidden" style={{ minHeight: 240 }}>
          {error ? (
            <div className="h-48 flex items-center justify-center text-white text-sm font-medium px-6 text-center">{error}</div>
          ) : (
            <video ref={videoRef} autoPlay muted playsInline className="w-full object-cover" />
          )}
          {!ready && !error && (
            <div className="absolute inset-0 flex items-center justify-center">
              <Loader2 className="w-8 h-8 text-white animate-spin" />
            </div>
          )}
        </div>
        {!error && (
          <div className="p-5 flex justify-center bg-slate-900">
            <button
              onClick={capture}
              disabled={!ready}
              title="Capture photo"
              className="w-14 h-14 rounded-full bg-white border-4 border-slate-400 hover:border-indigo-400 disabled:opacity-40 transition-all cursor-pointer flex items-center justify-center"
            >
              <div className="w-10 h-10 rounded-full bg-indigo-600 hover:bg-indigo-700 transition-colors" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Crop modal ───────────────────────────────────────────────────────────────
type CropBox = { x: number; y: number; size: number };

function CropModal({ src, onApply, onClose }: { src: string; onApply: (dataUrl: string) => void; onClose: () => void }) {
  const imgRef = useRef<HTMLImageElement>(null);
  const [crop, setCrop] = useState<CropBox>({ x: 60, y: 60, size: 200 });
  const dragRef = useRef<{ type: 'move' | 'resize'; startX: number; startY: number; startCrop: CropBox } | null>(null);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragRef.current) return;
      const dx = e.clientX - dragRef.current.startX;
      const dy = e.clientY - dragRef.current.startY;
      const { type, startCrop } = dragRef.current;
      if (type === 'move') {
        setCrop({
          size: startCrop.size,
          x: Math.max(0, Math.min(startCrop.x + dx, CROP_CONTAINER - startCrop.size)),
          y: Math.max(0, Math.min(startCrop.y + dy, CROP_CONTAINER - startCrop.size)),
        });
      } else {
        const delta = Math.max(dx, dy);
        const newSize = Math.max(60, Math.min(startCrop.size + delta, CROP_CONTAINER - startCrop.x, CROP_CONTAINER - startCrop.y));
        setCrop({ ...startCrop, size: newSize });
      }
    };
    const onUp = () => { dragRef.current = null; };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
    return () => { document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp); };
  }, []);

  const startDrag = (e: React.MouseEvent, type: 'move' | 'resize') => {
    e.preventDefault();
    e.stopPropagation();
    dragRef.current = { type, startX: e.clientX, startY: e.clientY, startCrop: crop };
  };

  const apply = () => {
    const img = imgRef.current!;
    const nw = img.naturalWidth;
    const nh = img.naturalHeight;
    const aspect = nw / nh;
    let dw: number, dh: number, ox = 0, oy = 0;
    if (aspect >= 1) { dw = CROP_CONTAINER; dh = CROP_CONTAINER / aspect; oy = (CROP_CONTAINER - dh) / 2; }
    else { dh = CROP_CONTAINER; dw = CROP_CONTAINER * aspect; ox = (CROP_CONTAINER - dw) / 2; }
    const sx = ((crop.x - ox) / dw) * nw;
    const sy = ((crop.y - oy) / dh) * nh;
    const sw = (crop.size / dw) * nw;
    const sh = (crop.size / dh) * nh;
    const canvas = document.createElement('canvas');
    canvas.width = 400; canvas.height = 400;
    canvas.getContext('2d')!.drawImage(img, Math.max(0, sx), Math.max(0, sy), Math.min(sw, nw - Math.max(0, sx)), Math.min(sh, nh - Math.max(0, sy)), 0, 0, 400, 400);
    onApply(canvas.toDataURL('image/jpeg', 0.88));
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-900/80 backdrop-blur-sm">
      <div className="bg-white rounded-2xl overflow-hidden shadow-2xl flex flex-col" style={{ width: CROP_CONTAINER + 40 }}>
        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-100 shrink-0">
          <span className="text-sm font-black text-slate-900">Crop Photo</span>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 cursor-pointer"><X className="w-5 h-5" /></button>
        </div>
        <p className="text-xs text-slate-500 text-center py-2">Drag the box to reposition · drag the corner to resize</p>
        <div className="mx-5 mb-1 relative select-none bg-black overflow-hidden"
          style={{ width: CROP_CONTAINER, height: CROP_CONTAINER }}>
          <img ref={imgRef} src={src} alt="Crop source" className="w-full h-full object-contain pointer-events-none" draggable={false} />
          <div
            className="absolute cursor-move"
            style={{ left: crop.x, top: crop.y, width: crop.size, height: crop.size, boxShadow: '0 0 0 9999px rgba(0,0,0,0.52)', border: '2px solid white' }}
            onMouseDown={(e) => startDrag(e, 'move')}
          >
            {/* Corner resize handle */}
            <div
              className="absolute bottom-0 right-0 w-6 h-6 cursor-se-resize flex items-end justify-end p-1"
              onMouseDown={(e) => startDrag(e, 'resize')}
            >
              <div className="w-3 h-3 border-b-2 border-r-2 border-white" />
            </div>
          </div>
        </div>
        <div className="flex gap-3 justify-end p-4">
          <button onClick={onClose} className="px-4 py-2 text-sm font-bold text-slate-600 border border-slate-200 rounded-xl hover:bg-slate-50 cursor-pointer">Cancel</button>
          <button onClick={apply} className="px-5 py-2 text-sm font-bold bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 cursor-pointer">Apply Crop</button>
        </div>
      </div>
    </div>
  );
}

// ─── Avatar uploader ──────────────────────────────────────────────────────────
function AvatarUploader({
  avatarUrl,
  name,
  onUpload,
}: {
  avatarUrl: string | null;
  name: string;
  onUpload: (dataUrl: string) => Promise<boolean>;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [preview, setPreview] = useState<string | null>(avatarUrl);
  const [showMenu, setShowMenu] = useState(false);
  const [showCamera, setShowCamera] = useState(false);
  const [cropSrc, setCropSrc] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => { setPreview(avatarUrl); }, [avatarUrl]);

  useEffect(() => {
    const handle = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setShowMenu(false);
    };
    if (showMenu) document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, [showMenu]);

  const openCrop = (dataUrl: string) => {
    setShowMenu(false);
    setCropSrc(dataUrl);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = '';
    const reader = new FileReader();
    reader.onload = (ev) => openCrop(ev.target!.result as string);
    reader.readAsDataURL(file);
  };

  const handleCameraCapture = (dataUrl: string) => {
    setShowCamera(false);
    openCrop(dataUrl);
  };

  const handleCropApply = async (dataUrl: string) => {
    setCropSrc(null);
    setUploading(true);
    setPreview(dataUrl);
    await onUpload(dataUrl);
    setUploading(false);
  };

  const initials = name.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2);

  return (
    <>
      <div className="relative group" ref={menuRef}>
        <div className="w-24 h-24 rounded-full bg-indigo-600 flex items-center justify-center text-white font-black text-2xl shrink-0 overflow-hidden">
          {preview
            ? <img src={preview} alt="Avatar" className="w-full h-full object-cover" />
            : initials
          }
        </div>

        <button
          onClick={() => setShowMenu((v) => !v)}
          disabled={uploading}
          className="absolute inset-0 rounded-full bg-slate-900/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center cursor-pointer disabled:cursor-wait"
          aria-label="Change avatar"
        >
          {uploading
            ? <Loader2 className="w-5 h-5 text-white animate-spin" />
            : <Camera className="w-5 h-5 text-white" />
          }
        </button>

        {showMenu && (
          <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 bg-white rounded-xl border border-slate-100 shadow-lg py-1 z-10 w-40">
            <button
              onClick={() => { setShowMenu(false); fileRef.current!.click(); }}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50 cursor-pointer"
            >
              <Upload className="w-3.5 h-3.5 text-slate-400" />
              Upload photo
            </button>
            <button
              onClick={() => { setShowMenu(false); setShowCamera(true); }}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50 cursor-pointer"
            >
              <Camera className="w-3.5 h-3.5 text-slate-400" />
              Take photo
            </button>
          </div>
        )}

        <input ref={fileRef} type="file" accept="image/*" onChange={handleFileChange} className="hidden" />
      </div>

      {showCamera && (
        <CameraModal onCapture={handleCameraCapture} onClose={() => setShowCamera(false)} />
      )}
      {cropSrc && (
        <CropModal src={cropSrc} onApply={handleCropApply} onClose={() => setCropSrc(null)} />
      )}
    </>
  );
}

// ─── Main EditProfile ─────────────────────────────────────────────────────────
export default function EditProfile({ profile, onUpdate, onDeleteAccount }: EditProfileProps) {
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  const memberSince = profile.created_at
    ? new Date(profile.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long' })
    : null;

  const save = (field: string) => async (value: string) => onUpdate({ [field]: value });
  const handlePassword = async (current: string, next: string) =>
    onUpdate({ current_password: current, password: next });
  const handleAvatarUpload = async (dataUrl: string) =>
    onUpdate({ avatar_url: dataUrl });
  const handleDeleteConfirm = async () => {
    await onDeleteAccount();
    window.location.href = '/';
  };

  return (
    <div className="max-w-[720px] space-y-6">

      {/* Avatar + Identity */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
        <div className="flex items-center gap-5 mb-6">
          <AvatarUploader
            avatarUrl={profile.avatar_url}
            name={profile.name ?? '?'}
            onUpload={handleAvatarUpload}
          />
          <div>
            <p className="text-xl font-black text-slate-900">{profile.name}</p>
            <p className="text-sm text-slate-500">{profile.email}</p>
            {memberSince && <p className="text-xs text-slate-400 mt-0.5">Member since {memberSince}</p>}
          </div>
        </div>
        <div className="space-y-4">
          <div>
            <label className="text-xs font-black text-slate-500 uppercase tracking-wider block mb-1">Name</label>
            <InlineField label="Name" value={profile.name ?? ''} onSave={save('name')} />
          </div>
          <div>
            <label className="text-xs font-black text-slate-500 uppercase tracking-wider block mb-1">Email</label>
            <div className="flex items-center gap-3">
              <span className="text-sm font-bold text-slate-800">{profile.email}</span>
              <span className="text-xs text-slate-400 italic">Verification coming soon</span>
            </div>
          </div>
        </div>
      </div>

      {/* Preferences */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
        <h3 className="text-sm font-black text-slate-900 uppercase tracking-wider mb-4">Preferences</h3>
        <div className="space-y-4">
          <div>
            <label className="text-xs font-black text-slate-500 uppercase tracking-wider block mb-1">Timezone</label>
            <SelectField
              label="Timezone"
              value={profile.timezone ?? 'Asia/Kolkata'}
              options={TIMEZONES}
              onSave={save('timezone')}
            />
          </div>
          <div>
            <label className="text-xs font-black text-slate-500 uppercase tracking-wider block mb-1">Home City</label>
            <InlineField
              label="Home City"
              value={profile.home_city ?? ''}
              onSave={save('home_city')}
              compact
              placeholder="Bangalore"
            />
          </div>
          <div>
            <label className="text-xs font-black text-slate-500 uppercase tracking-wider block mb-1">Preferred Currency</label>
            <SelectField
              label="Currency"
              value={profile.currency ?? 'INR'}
              options={CURRENCIES}
              onSave={save('currency')}
            />
          </div>
          <div>
            {/* Travel Style with tooltip — label rendered inside TextareaField */}
            <TextareaField value={profile.travel_blurb ?? ''} onSave={save('travel_blurb')} />
          </div>
        </div>
      </div>

      {/* Security */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
        <h3 className="text-sm font-black text-slate-900 uppercase tracking-wider mb-4">Security</h3>
        <PasswordBlock onSave={handlePassword} />
      </div>

      {/* Account deletion — no "DANGER ZONE" heading */}
      <div className="bg-white rounded-2xl border border-rose-100 shadow-sm p-6">
        <p className="text-xs text-slate-500 mb-4">Permanently delete your account and all associated data. This cannot be undone.</p>
        <button
          onClick={() => setShowDeleteModal(true)}
          className="px-4 py-2 text-sm font-bold text-rose-500 border border-rose-200 rounded-lg hover:bg-rose-50 transition-colors cursor-pointer"
        >
          Delete account
        </button>
      </div>

      {showDeleteModal && (
        <DeleteAccountModal
          email={profile.email}
          onConfirm={handleDeleteConfirm}
          onCancel={() => setShowDeleteModal(false)}
        />
      )}
    </div>
  );
}

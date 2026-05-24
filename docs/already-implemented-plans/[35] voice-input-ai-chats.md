# Voice Input (Speech-to-Text) for All AI Chats — Web + iOS

## Context

Today every AI chat in Roammate is type-only. We want a microphone option so users can
**speak instead of type** into all three chat surfaces, on **both platforms**:

| Chat | Web file | iOS file |
|------|----------|----------|
| **Plan Trip** (one-shot prompt) | `frontend/components/dashboard/DashboardTripPlanner.tsx` | `ios/Roammate/Views/Chat/PlanTripDrawer.swift` |
| **Brainstorm** | `frontend/components/trip/BrainstormChat.tsx` | `ios/Roammate/Views/Trips/Brainstorm/BrainstormChatView.swift` |
| **Concierge** | `frontend/components/trip/ConciergeChatDrawer.tsx` | `ios/Roammate/Views/Chat/AIChatDrawer.swift` |

**Decisions (confirmed with user):**
- **Web** uses the browser **Web Speech API** (`SpeechRecognition` / `webkitSpeechRecognition`) — free, no backend, live interim text. The mic is hidden where the API is unsupported (e.g. Firefox).
- **iOS** uses the native **Speech framework** (`SFSpeechRecognizer` + `AVAudioEngine`) — on-device, free.
- **Behavior: fill-the-box.** Transcript is dictated **into the existing input** so the user can edit before sending. No auto-send.
- Both engines are free/on-device, so **no entitlement/quota gating** is added (keeps it out of the Plus/quota system entirely).

There is no shared chat-input component on either platform, so we build **one reusable mic
component per platform** and drop it into the three existing input bars. All styling follows
`/frontend-theme` tokens; interaction polish per `/ui-ux-pro-max`.

---

## Web implementation

### 1. New hook: `frontend/hooks/useSpeechInput.ts`
Plain client hook (mirrors `useProfile.ts` style; `'use client'`). Wraps Web Speech API.

- Detect support: `const SR = window.SpeechRecognition || window.webkitSpeechRecognition`.
- State/returns: `{ isSupported, isListening, start, stop, error }`.
- Config: `continuous = true`, `interimResults = true`, `lang = navigator.language || 'en-US'`.
- Accepts callbacks `{ onInterim(text), onFinal(text) }` so the caller controls how transcript
  merges into its own input state.
- Handle `onend`/`onerror` (reset `isListening`; surface `not-allowed` permission denial via `error`).
- Keep the `SpeechRecognition` instance in a `useRef`; clean up on unmount.

### 2. New component: `frontend/components/common/VoiceInputButton.tsx`
Reusable mic button reused by all three chats. Uses `useSpeechInput` + `lucide-react` (`Mic`).

- Props: `{ value: string; onChange: (v: string) => void; disabled?: boolean; className?: string }`.
- On start: snapshot current `value` as a base, then on each interim/final result call
  `onChange(base + transcript)` for live dictation into the box.
- **If `!isSupported`, render `null`** (mic simply absent on unsupported browsers).
- Visual states (per `/frontend-theme`): idle = `text-slate-400 hover:text-indigo-600`, matching
  the existing `rounded-xl`/`rounded-lg` ghost-button shape next to Send; recording = `bg-rose-500
  text-white` with a subtle pulsing ring (Framer Motion), gated behind `prefers-reduced-motion`.
- `aria-label` toggles "Start voice input" / "Stop voice input"; `aria-pressed={isListening}`.

### 3. Wire into the three input bars
In each, add `<VoiceInputButton value={...} onChange={set...} />` inside the existing flex row,
**immediately before the Send button**, and stop listening when the message is sent (clearing input):

- `DashboardTripPlanner.tsx` (~line 197 flex row): `value={prompt} onChange={setPrompt}`.
- `BrainstormChat.tsx` (~line 283 flex row): `value={input} onChange={setInput}`; render only in the
  non-quota-exhausted branch (alongside the Send button, not the Lock button).
- `ConciergeChatDrawer.tsx` (~line 634 flex row): `value={input} onChange={setInput}`; sits inside the
  bordered input pill, between the `<input>` and the Send button.

---

## iOS implementation

### 1. New service: `ios/Roammate/Services/SpeechRecognizer.swift`
`@Observable` (or `ObservableObject`) class, following the MVVM store pattern.

- `import Speech` + `import AVFoundation`.
- Published: `transcript: String`, `isRecording: Bool`, `isAvailable: Bool`.
- `requestAuthorization()` → `SFSpeechRecognizer.requestAuthorization` + `AVAudioSession`
  record-permission request.
- `startTranscribing()` → configure `AVAudioSession` (`.record`), install tap on `AVAudioEngine`
  input node, stream into `SFSpeechAudioBufferRecognitionRequest`, update `transcript` on each
  partial result (main actor).
- `stopTranscribing()` → stop engine, end request, deactivate session.

### 2. New view: `ios/Roammate/Views/Chat/MicButton.swift`
Reusable SwiftUI button reused by all three input bars.

- Props: `@Binding var text: String`, the `SpeechRecognizer`, optional `disabled`.
- SF Symbols `mic.fill` / `mic.slash.fill`; idle `.roammateMuted`, recording `.roammateDanger`
  with a pulsing scale animation (respect Reduce Motion).
- On start, snapshot `text` as base; mirror `recognizer.transcript` into the binding as
  `base + transcript`. Trigger `HapticManager` on toggle.
- Hidden / disabled when `!recognizer.isAvailable` or authorization denied.

### 3. Wire into the three input bars (each is an `HStack` with `TextField` + send `Button`)
Insert `MicButton(text: $input, recognizer: ...)` before the send button:

- `AIChatDrawer.swift` `inputBar` (~line 141, binding `$input`).
- `BrainstormChatView.swift` input row (~line 281, binding `$inputText`).
- `PlanTripDrawer.swift` input row (~line 310, the prompt `TextField`).

Each owns a `@State private var speech = SpeechRecognizer()` (or shared via environment).

### 4. Permissions: `ios/Roammate/App/Info.plist`
Add (currently absent):
- `NSMicrophoneUsageDescription` — e.g. "Roammate uses the mic so you can speak to the AI travel assistant."
- `NSSpeechRecognitionUsageDescription` — e.g. "Speech recognition turns your voice into chat messages."

`Speech` and `AVFoundation` are system frameworks (auto-linked on `import`); no `project.pbxproj` change expected.

---

## Cross-platform notes
- Same UX on both platforms (mic next to Send, fill-the-box, no auto-send) per the
  cross-platform rule in `/frontend-theme`.
- Reuse the danger token (`rose-500` / `.roammateDanger`) for the recording state — not the Plus
  gradient (brand-reserved).
- Respect `prefers-reduced-motion` (web) and Reduce Motion (iOS) for the pulsing animation.

## Verification
**Web** (`cd frontend && npm run dev`, open in Chrome over localhost — Web Speech needs https/localhost):
1. Dashboard → Plan-a-trip box: click mic, grant permission, speak → words fill the textarea → edit → "Plan".
2. Open a trip → Brainstorm chat: mic dictates into the textarea → Send.
3. Open Concierge drawer: mic dictates into the input pill → Send.
4. While recording, the button shows the rose pulsing state; clicking again stops.
5. Open the same pages in Firefox → mic button is absent (graceful, no errors).

**iOS** (run on a real device or simulator with host mic):
1. First mic tap shows the system mic + speech-recognition permission prompts (verifying Info.plist strings).
2. In Plan Trip, Brainstorm, and Concierge: tap mic, speak → transcript fills the field → edit → send.
3. Toggling mic off stops recording; deny-permission path hides/disables the mic gracefully.

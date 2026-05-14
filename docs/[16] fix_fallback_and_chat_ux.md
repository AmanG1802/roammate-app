---
name: Fix Fallback and Chat UX
overview: Fix the Thailand Getaway fallback being used on LLM errors (should only apply when LLM_ENABLED=false), show proper error messages on API failures, persist user prompts on error, and improve Brainstorm Chat's LLM output rendering with markdown support.
todos:
  - id: backend-remove-fallback
    content: "In RoammateServiceV1 (roammate_v1.py): change plan_trip() and extract_items() error handling from returning Thailand fallback to raising RuntimeError"
    status: completed
  - id: backend-api-error-handling
    content: "In llm.py and brainstorm.py API endpoints: add try/except around LLM calls, return HTTP 502 with user-friendly messages"
    status: completed
  - id: frontend-brainstorm-error
    content: "In BrainstormChat.tsx: add error state, move setInput('') to success path, show error banner with retry affordance"
    status: completed
  - id: frontend-markdown-rendering
    content: Install react-markdown, render assistant messages through ReactMarkdown with tailwind prose styling in BrainstormChat.tsx
    status: completed
  - id: frontend-planner-error-msg
    content: "In DashboardTripPlanner.tsx: ensure error message is clear and prompt is persisted (already mostly correct)"
    status: completed
isProject: false
---

# Fix Fallback Logic, Error UX, and Brainstorm Chat Formatting

## Problem Summary

Three issues to fix:

1. **Thailand Getaway fallback on LLM errors** -- When the LLM call fails (parse error, API error), `RoammateServiceV1.plan_trip()` and `extract_items()` silently return the Bangkok/Thailand fallback data. This fallback should **only** be used when `LLM_ENABLED=false`. On real errors, the backend should raise an HTTP error so the frontend can show an error message.

2. **User prompt not persisted on error** -- In both `DashboardTripPlanner` and `BrainstormChat`, the user's input is cleared before the API call completes. If the call fails, the prompt is lost and the user has to retype it.

3. **Brainstorm Chat renders LLM output as plain text** -- The assistant messages are rendered with `{m.content}` directly, so markdown formatting (bold, lists, line breaks) from the LLM comes out as raw text.

---

## 1. Backend: Remove fallback-on-error in `RoammateServiceV1`

**File:** [`backend/app/services/llm/services/v1/roammate_v1.py`](backend/app/services/llm/services/v1/roammate_v1.py)

### `plan_trip()` (lines 287-292)

Change the `except` block from returning `THAILAND_PLAN_FALLBACK` to raising an exception that FastAPI will surface as a 500/502:

```python
except (json.JSONDecodeError, TypeError, ValueError) as exc:
    log.warning("LLM plan_trip parse failed (%s), using fallback", exc)
    raise RuntimeError(f"Failed to parse trip plan from AI: {exc}") from exc
```

### `extract_items()` (lines 227-229)

Same pattern -- raise instead of returning fallback:

```python
except (json.JSONDecodeError, TypeError, ValueError) as exc:
    log.warning("LLM extract parse failed (%s), using fallback", exc)
    raise RuntimeError(f"Failed to parse brainstorm items from AI: {exc}") from exc
```

### `chat()` -- already raises on error (no try/except around `model.complete`), so no change needed. But `model.complete` can throw from `_retry` -- the brainstorm endpoint has no error handling either. We need to handle that at the API layer.

---

## 2. Backend: Add error handling in API endpoints

### [`backend/app/api/endpoints/llm.py`](backend/app/api/endpoints/llm.py) -- `plan_trip` endpoint

Wrap the service call in a try/except that returns a clear HTTP 502:

```python
from fastapi import HTTPException

try:
    result = await client.plan_trip(...)
    enriched_items = await get_google_maps_service().enrich_items(...)
except Exception as exc:
    log.exception("plan_trip failed")
    raise HTTPException(status_code=502, detail="AI planner is temporarily unavailable. Please try again.")
```

### [`backend/app/api/endpoints/brainstorm.py`](backend/app/api/endpoints/brainstorm.py) -- `chat` endpoint (line 112)

Similarly wrap the LLM call. On error, roll back the user message that was added to the DB (or don't persist it at all until success). Return HTTP 502 with a friendly message.

### [`backend/app/api/endpoints/brainstorm.py`](backend/app/api/endpoints/brainstorm.py) -- `extract` endpoint (line 163)

Same pattern -- catch and return HTTP 502.

---

## 3. Frontend: Persist user prompt on error

### [`frontend/components/dashboard/DashboardTripPlanner.tsx`](frontend/components/dashboard/DashboardTripPlanner.tsx) -- `plan()` function

Currently the prompt is never cleared after `plan()`, which is correct. The `prompt` state persists through errors. However, the error message could be more helpful. Current behavior is actually fine here -- the prompt stays in the textarea and the error shows below. No change needed for prompt persistence.

### [`frontend/components/trip/BrainstormChat.tsx`](frontend/components/trip/BrainstormChat.tsx) -- `send()` function

**Problem:** Line 44 does `setInput('')` before the API call. On error, the user's message is lost and there is no error UI at all -- failures are silently swallowed.

### Error UI Design

#### DashboardTripPlanner (Plan Trip)

Already has functional error handling. The `prompt` state is never cleared, so the text stays in the textarea on error. The error appears as a rose-colored line below the input (line 150). The "Plan" button remains enabled so the user just clicks it again.

Only change: improve the error message to be more descriptive, e.g. "AI planner hit a snag -- your prompt is saved, just hit Plan again."

#### BrainstormChat -- Optimistic Bubble + Inline Retry

The pattern follows how modern chat apps (iMessage, WhatsApp, Slack) handle send failures:

1. **Optimistic user bubble** -- When the user hits Send, immediately:
   - Clear the input box (feels responsive, message was "sent")
   - Append the user's message as a bubble in the chat history
   - Show the typing indicator (dots) for the AI response
   - Store the pending message text in a `failedMessage` ref

2. **On success** -- Replace the optimistic state with the real server history (`data.history`), clear `failedMessage`. Normal flow.

3. **On error** -- The typing indicator disappears and a **red error bubble** appears in the chat (where the AI response would have been):

```
 ┌─────────────────────────────────────────────┐
 │                    User's message bubble  ▐  │  (already shown optimistically)
 └─────────────────────────────────────────────┘
 ┌─────────────────────────────────────────────┐
 │  ⚠  Couldn't get a response.  [↻ Retry]    │  (error bubble, in-flow)
 └─────────────────────────────────────────────┘
```

   - Styled as a left-aligned bubble like an assistant message, but with `bg-rose-50 border-rose-200 text-rose-700`
   - Contains an `AlertTriangle` icon, short message, and a **Retry button**
   - Clicking Retry re-sends the same `failedMessage` (no need to retype anything)
   - On retry success, the error bubble is replaced with the real AI response
   - On retry failure, the error bubble stays

4. **State management:**

```typescript
const [failedMessage, setFailedMessage] = useState<string | null>(null);

const send = async (retryMsg?: string) => {
    const msg = retryMsg ?? input.trim();
    if (!msg || sending) return;
    setSending(true);
    setFailedMessage(null);
    if (!retryMsg) {
      // Optimistic: show user bubble immediately, clear input
      setMessages(prev => [...prev, { id: Date.now(), role: 'user', content: msg, created_at: new Date().toISOString() }]);
      setInput('');
    }
    try {
      const res = await fetch(...);
      if (res.ok) {
        const data = await res.json();
        setMessages(data.history);  // replaces optimistic with real
      } else {
        setFailedMessage(msg);
      }
    } catch {
      setFailedMessage(msg);
    } finally {
      setSending(false);
    }
};

// Retry handler for the error bubble button
const retry = () => failedMessage && send(failedMessage);
```

5. **Error bubble JSX** -- rendered after the last message in the chat list when `failedMessage` is set:

```tsx
{failedMessage && !sending && (
  <div className="flex items-end gap-2">
    <div className="w-6 h-6 ...">
      <AlertTriangle className="w-3 h-3 text-rose-500" />
    </div>
    <div className="bg-rose-50 border border-rose-200 rounded-2xl px-4 py-2.5 ...">
      <p className="text-sm text-rose-700 font-medium">Couldn't get a response.</p>
      <button onClick={retry} className="text-xs font-bold text-rose-600 hover:text-rose-800 mt-1 flex items-center gap-1">
        <RotateCcw className="w-3 h-3" /> Retry
      </button>
    </div>
  </div>
)}
```

---

## 4. Frontend: Render Brainstorm Chat messages with markdown

**File:** [`frontend/components/trip/BrainstormChat.tsx`](frontend/components/trip/BrainstormChat.tsx)

The LLM returns natural-language responses that often contain markdown (bold, numbered lists, bullet points). Currently line 125 renders `{m.content}` as raw text.

- Install `react-markdown` package: `npm install react-markdown`
- For assistant messages, render through `<ReactMarkdown>` with Tailwind prose styling
- User messages remain plain text (they don't contain markdown)

Replace line 125:

```tsx
{m.role === 'assistant' ? (
  <ReactMarkdown className="prose prose-sm prose-slate max-w-none [&>p]:my-1 [&>ul]:my-1 [&>ol]:my-1 [&>li]:my-0.5">
    {m.content}
  </ReactMarkdown>
) : (
  m.content
)}
```

Add `@tailwindcss/typography` plugin if not already present for prose classes, or alternatively create a lightweight custom renderer that handles bold, lists, and line breaks without extra dependencies.

---

## Files Changed

| Area | File | Change |
|------|------|--------|
| Backend | `backend/app/services/llm/services/v1/roammate_v1.py` | Raise errors instead of returning fallback data on LLM parse failures |
| Backend | `backend/app/api/endpoints/llm.py` | Add try/except with HTTP 502 for plan_trip |
| Backend | `backend/app/api/endpoints/brainstorm.py` | Add try/except with HTTP 502 for chat and extract |
| Frontend | `frontend/components/trip/BrainstormChat.tsx` | Persist input on error, add error state/display, render markdown |
| Frontend | `frontend/components/dashboard/DashboardTripPlanner.tsx` | Minor: improve error message wording |
| Frontend | `frontend/package.json` | Add `react-markdown` dependency |

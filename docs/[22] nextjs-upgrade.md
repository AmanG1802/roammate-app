# Next.js 14 → 15 → 16 Upgrade Plan (Roammate frontend)

> **Deliverable target:** Upon approval, this file will be saved to
> `docs/[22] nextjs-upgrade.md`.
> **Scope:** `frontend/` only.
> **Date:** 2026-05-14

---

## Context

The Roammate frontend is pinned to **Next.js 14.1.0** (early 2024). npm
flagged a security advisory for this version during the most recent
`docker compose build frontend`, and 14 is now two majors behind:

- **Next 15** — async request APIs (`cookies()`/`headers()`/`params`/
  `searchParams` become Promises), React 19 required, `fetch()`
  uncached by default, stable Server Actions.
- **Next 16** — Turbopack default, Cache Components (`use cache` +
  `cacheLife`/`cacheTag`/`updateTag`), `unstable_cache` deprecated.

A code survey shows our codebase is **unusually well positioned** for
the upgrade because of three pre-existing facts:

1. **Every page is `'use client'`** — no server components rely on
   `cookies()`/`headers()`/`params`/`searchParams`. The async-API
   breaking change has zero call sites here.
2. **No `unstable_cache`, `revalidateTag`, or `revalidatePath` usage** —
   the Next 16 Cache Components rework is a non-issue.
3. **No `next.config.js`, no `middleware.ts`, no `pages/` directory** —
   nothing to migrate config-wise.

What remains is mostly version bumps + a React 19 transition + light
verification. This plan covers both major hops in a single, low-risk
sequence executed on a side branch.

---

## What needs to change

### 1. Dependencies (`frontend/package.json`)

| Package | From | To | Why |
|---|---|---|---|
| `next` | `^14.1.0` | `^16` (latest patch) | core upgrade |
| `react` | `^18` | `^19` | required by Next 15+ |
| `react-dom` | `^18` | `^19` | required by Next 15+ |
| `@types/react` | `^18` | `^19` | types alignment |
| `@types/react-dom` | `^18` | `^19` | types alignment |
| `eslint-config-next` | `14.x` | `16.x` | pairs with `next` |

Run the official codemod to handle the mechanical edits:

```bash
cd frontend
npx @next/codemod@latest upgrade latest
```

The codemod will:
- Bump the packages above to compatible versions
- Apply the async-API codemod (no-op for us, but safe to run)
- Apply the `useFormState → useActionState` codemod (no-op; we have
  no `useFormState`)
- Apply any deprecation rewrites Next ships at the time of upgrade

### 2. React 19 transition — verified safe

Audit found three `forwardRef` call sites; all keep working in React 19
because `forwardRef` is still supported (just no longer required for
`ref` as a regular prop). **No edits required**, but we may opt to
simplify post-upgrade as a separate clean-up pass:

- `frontend/components/layout/NotificationBell.tsx:119`
- `frontend/components/dashboard/TodayWidget.tsx:58`
- `frontend/components/trip/BrainstormBin.tsx:34`

### 3. Third-party deps to revalidate

These have React peer-dependencies and should be re-installed after the
React 19 bump so npm picks compatible versions. None of them require
code changes:

- `framer-motion@^11.0.3`
- `@tanstack/react-query@^5.20.1`
- `react-markdown@^10.1.0`
- `zustand@^4.5.1`
- `lucide-react@^0.330.0`
- `gsap@^3.12.5` (used by the landing page)
- `@googlemaps/js-api-loader@^1.16.2`
- `@googlemaps/markerclusterer`

If `npm install` reports peer-dep warnings post-bump, address those
specific packages individually rather than a blanket bump.

### 4. `fetch()` caching defaults — no action needed

Survey confirmed every `fetch()` call in the app is client-side
(inside `'use client'` components or browser-only utilities). The
Next 15 server-side fetch-cache flip therefore has no effect on
behaviour. If we later add server components or route handlers that
fetch, we'll need to explicitly opt into `cache: 'force-cache'` where
caching is wanted — call this out in a follow-up issue but **not** in
this PR.

### 5. Turbopack (Next 16)

Next 16 makes Turbopack the default bundler for `next dev` and
`next build`. There is no `next.config.js` and no webpack-specific
config to migrate, so the switch should be transparent. The Docker
dev container uses `npm run dev`, which is just `next dev` — it will
pick up Turbopack automatically once on Next 16.

If we want to *delay* the Turbopack switch (e.g. to validate it
separately), we can keep the explicit `--turbopack=false` flag in
`package.json` scripts for one release. Default plan: leave it on.

### 6. `tsconfig.json` / `tsconfig.tsbuildinfo`

`tsconfig.json` already uses `"moduleResolution": "bundler"`, which is
Next 15+ compliant. No edits needed.

`tsconfig.tsbuildinfo` will be regenerated on first build — delete it
before the upgrade run to avoid stale-cache type-check noise.

### 7. Docker

`docker/frontend.Dockerfile` uses `node` base image + `npm install`.
Once `package-lock.json` updates, rebuild the image:

```bash
docker compose build --no-cache frontend
```

No Dockerfile changes anticipated.

---

## Critical files

```
frontend/
├── package.json                 # version bumps (codemod)
├── package-lock.json            # regenerated by npm install
├── tsconfig.tsbuildinfo         # delete before upgrade
└── (no next.config.js)          # nothing to migrate

docker/frontend.Dockerfile       # no changes; just rebuild image
```

Verified untouched:
- `frontend/app/(auth)/login/page.tsx` (uses client `useSearchParams`)
- `frontend/app/trips/page.tsx` (uses client `useSearchParams`)
- `frontend/app/trips/[id]/page.tsx` (uses client `useParams`)
- `frontend/app/layout.tsx` (already uses `next/font/google`)
- `frontend/tsconfig.json` (already `bundler` resolution)
- All server-side files (none exist — no server components, no route
  handlers, no `middleware.ts`)

---

## Execution sequence

Cut a side branch from `main` so we can validate before merging:

```bash
git checkout -b chore/nextjs-upgrade
```

Then:

1. **Codemod**: `cd frontend && npx @next/codemod@latest upgrade latest`
   - Accept the React 19 + Next 16 prompts.
2. **Clean reinstall**:
   `rm -rf node_modules .next tsconfig.tsbuildinfo && npm install`
3. **Type-check**: `npx tsc --noEmit` — must be zero errors. (Already
   zero on `main` after `4e859c0`.)
4. **Lint**: `npm run lint`
5. **Unit tests**: `npm run test` (vitest is configured).
6. **Dev server smoke**: `npm run dev` and exercise the golden path
   manually (see Verification below).
7. **Docker rebuild**: `docker compose build --no-cache frontend &&
   docker compose up -d frontend && docker compose logs --tail=80
   frontend` — confirm no compile errors.
8. **Production build**: `npm run build` to surface anything that
   slipped past `tsc` (RSC type checks, image optimisation,
   chunk-splitting issues).
9. **Commit + PR**: one squashed commit "chore: upgrade to next 16 +
   react 19" — the codemod's diff plus the lockfile.

Estimated effort: **half a day** if nothing surprises, up to a day if
peer-dep warnings need triage.

---

## Verification

End-to-end manual flow on the dev server *and* a production build:

1. Sign up new account → onboarding persona modal renders.
2. Create a trip → trip hub loads with hero animation (GSAP).
3. Open Plan mode → Timeline + Map + Idea Bin render side-by-side
   on desktop, tabbed on mobile (the Wave 2 work).
4. Add a brainstorm message → extract → drag to timeline → vote.
5. Open Concierge → "Find coffee" → confirm Esc closes the drawer
   (the Wave 3 a11y addition).
6. Resize the browser from 1440px → 320px on the trip planner →
   confirm map overlays don't overlap (the Wave 2.3 layer).
7. Reload `/dashboard` with the network throttled — confirm the
   skeleton cards (Wave 1) render instead of a blank screen.
8. Force-fail a mutation in DevTools → confirm a toast appears.
9. `Lighthouse` (mobile, incognito) on `/dashboard` and `/trips/{id}`
   — performance shouldn't regress; Turbopack may actually improve it.

Failure rollback is trivial: revert the single squashed commit and
rebuild the docker image. Lockfile pins guarantee a deterministic
return to Next 14.1.0.

---

## Out of scope (explicit non-goals)

- **Migrating any page to a Server Component.** That's a separate
  architectural decision; this upgrade keeps the all-client posture.
- **Adopting Cache Components / `use cache`.** Not used today; if we
  later add server-side data fetching we'll plan that separately.
- **Enabling Partial Prerendering (PPR).** Requires per-route opt-in
  and only makes sense once some routes are server-rendered.
- **Switching the dev container off `npm run dev`** (e.g. to a
  pre-built image). Orthogonal to this upgrade.
- **`forwardRef` simplification.** Optional cleanup, do separately.

---

## Risks & mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Peer-dep warning on framer-motion or react-query under React 19 | Low | Bump that specific package |
| Vercel deploy fails on Next 16 build | Low | Run `npm run build` locally first; we use the same Node version (Docker) |
| Subtle behavioural change in `useSearchParams`/`useParams` between Next 14 → 16 | Very low | These hooks are stable across both majors |
| Turbopack reveals a Tailwind plugin incompat | Low | Temporarily set `--no-turbopack` (see §5) |
| GSAP magnetic-button physics behaving differently under React 19 strict effects | Very low | Test landing page explicitly in verification step 1 |

---

## Suggested PR description

> **chore: upgrade to next 16 + react 19**
>
> Runs the official `@next/codemod` to move the frontend from
> Next 14.1.0 → Next 16 and React 18 → 19. Closes the security
> advisory flagged by npm on every build.
>
> The migration is mostly a version bump because the codebase is
> 100% client-rendered (no server components, no `cookies()`/
> `headers()`, no `unstable_cache`, no `middleware.ts`). All
> framer-motion / gsap / Tailwind code paths verified by hand.
>
> See `docs/[22] nextjs-upgrade.md` for the full plan and rollback.

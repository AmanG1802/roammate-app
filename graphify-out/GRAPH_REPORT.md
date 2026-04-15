# Graph Report - /Users/aman.gupta1/roammate-app  (2026-04-16)

## Corpus Check
- Corpus is ~24,733 words - fits in a single context window. You may not need a graph.

## Summary
- 372 nodes · 551 edges · 63 communities detected
- Extraction: 70% EXTRACTED · 30% INFERRED · 0% AMBIGUOUS · INFERRED: 165 edges (avg confidence: 0.59)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_SQLAlchemy Data Models|SQLAlchemy Data Models]]
- [[_COMMUNITY_Trip Integration Tests|Trip Integration Tests]]
- [[_COMMUNITY_Backend Core & Config|Backend Core & Config]]
- [[_COMMUNITY_Event & Pydantic Schemas|Event & Pydantic Schemas]]
- [[_COMMUNITY_Test Infrastructure|Test Infrastructure]]
- [[_COMMUNITY_Architecture Vision Docs|Architecture Vision Docs]]
- [[_COMMUNITY_Ingestion & Ripple API|Ingestion & Ripple API]]
- [[_COMMUNITY_Trip Social & Navigation|Trip Social & Navigation]]
- [[_COMMUNITY_Event API Tests|Event API Tests]]
- [[_COMMUNITY_Auth API Tests|Auth API Tests]]
- [[_COMMUNITY_External Services (Maps + Bin)|External Services (Maps + Bin)]]
- [[_COMMUNITY_Dashboard View|Dashboard View]]
- [[_COMMUNITY_Timeline Drag & Drop|Timeline Drag & Drop]]
- [[_COMMUNITY_NLP Pipeline|NLP Pipeline]]
- [[_COMMUNITY_Timeline Test Utilities|Timeline Test Utilities]]
- [[_COMMUNITY_Store Utility Helpers|Store Utility Helpers]]
- [[_COMMUNITY_Navbar Component|Navbar Component]]
- [[_COMMUNITY_Idea Bin Component|Idea Bin Component]]
- [[_COMMUNITY_App Configuration|App Configuration]]
- [[_COMMUNITY_API Router|API Router]]
- [[_COMMUNITY_Trip Planner Page|Trip Planner Page]]
- [[_COMMUNITY_Store Test Utilities|Store Test Utilities]]
- [[_COMMUNITY_Auth Hook|Auth Hook]]
- [[_COMMUNITY_App Entrypoint|App Entrypoint]]
- [[_COMMUNITY_Root Layout|Root Layout]]
- [[_COMMUNITY_Login Page|Login Page]]
- [[_COMMUNITY_IdeaBin Test Mock|IdeaBin Test Mock]]
- [[_COMMUNITY_TripHub Test Utilities|TripHub Test Utilities]]
- [[_COMMUNITY_Collaborators Component|Collaborators Component]]
- [[_COMMUNITY_Google Map Component|Google Map Component]]
- [[_COMMUNITY_Concierge Action Bar|Concierge Action Bar]]
- [[_COMMUNITY_VibeCheck Component|VibeCheck Component]]
- [[_COMMUNITY_DB Session|DB Session]]
- [[_COMMUNITY_Auth Dependencies|Auth Dependencies]]
- [[_COMMUNITY_API Init|API Init]]
- [[_COMMUNITY_Vitest Setup|Vitest Setup]]
- [[_COMMUNITY_Build Config|Build Config]]
- [[_COMMUNITY_Next.js Types|Next.js Types]]
- [[_COMMUNITY_Tailwind Config|Tailwind Config]]
- [[_COMMUNITY_Vitest Config|Vitest Config]]
- [[_COMMUNITY_PostCSS Config|PostCSS Config]]
- [[_COMMUNITY_Landing Page|Landing Page]]
- [[_COMMUNITY_Test Setup|Test Setup]]
- [[_COMMUNITY_Backend Init|Backend Init]]
- [[_COMMUNITY_Core Init|Core Init]]
- [[_COMMUNITY_Models Init|Models Init]]
- [[_COMMUNITY_Schemas Init|Schemas Init]]
- [[_COMMUNITY_DB Init|DB Init]]
- [[_COMMUNITY_Endpoints Init|Endpoints Init]]
- [[_COMMUNITY_Services Init|Services Init]]
- [[_COMMUNITY_updateEventTime Action|updateEventTime Action]]
- [[_COMMUNITY_reorderEvent Action|reorderEvent Action]]
- [[_COMMUNITY_GET usersme|GET /users/me]]
- [[_COMMUNITY_PATCH events|PATCH /events]]
- [[_COMMUNITY_DELETE events|DELETE /events]]
- [[_COMMUNITY_GET events|GET /events]]
- [[_COMMUNITY_GET trips|GET /trips]]
- [[_COMMUNITY_POST trips|POST /trips]]
- [[_COMMUNITY_GET trips{id}|GET /trips/{id}]]
- [[_COMMUNITY_GET trips{id}ideas|GET /trips/{id}/ideas]]
- [[_COMMUNITY_GET trips{id}members|GET /trips/{id}/members]]
- [[_COMMUNITY_Brainstorm Document|Brainstorm Document]]
- [[_COMMUNITY_README|README]]

## God Nodes (most connected - your core abstractions)
1. `create_trip()` - 23 edges
2. `User` - 19 edges
3. `TripMember` - 16 edges
4. `Base` - 15 edges
5. `IngestRequest` - 13 edges
6. `Event` - 12 edges
7. `Event` - 11 edges
8. `Get all trips where the current user is a member.` - 11 edges
9. `Create a new trip and add the current user as the owner.` - 11 edges
10. `Return all members of a trip (with user details). Caller must be a member.` - 11 edges

## Surprising Connections (you probably didn't know these)
- `localStorage Token-Based Auth Pattern` --semantically_similar_to--> `API Dependencies (get_current_user)`  [INFERRED] [semantically similar]
  frontend/hooks/useAuth.tsx → backend/app/api/deps.py
- `RippleEngine.shift_itinerary` --implements--> `Ripple Engine (Architecture Concept)`  [INFERRED]
  backend/app/services/ripple_engine.py → architecture.md
- `Event Interface (Frontend)` --semantically_similar_to--> `Event SQLAlchemy Model`  [INFERRED] [semantically similar]
  frontend/lib/store.ts → backend/app/models/all_models.py
- `Idea Interface (Frontend)` --semantically_similar_to--> `IdeaBinItem SQLAlchemy Model`  [INFERRED] [semantically similar]
  frontend/lib/store.ts → backend/app/models/all_models.py
- `Idea Bin Ingestion Concept` --rationale_for--> `IdeaBinService`  [INFERRED]
  roammate-brainstorm.md → backend/app/services/idea_bin.py

## Hyperedges (group relationships)
- **3-Pane Trip Planner (Timeline + Map + IdeaBin)** — component_timeline, component_googlemap, component_ideabin, store_usetripstore [EXTRACTED 1.00]
- **Drag + Time Hint → Auto-Scheduling Flow** — component_ideabin, concept_timehint, component_timeline, store_usetripstore [EXTRACTED 0.95]
- **Authentication Guard Flow (Login → Token → ProtectedRoute)** — page_login, concept_localstoragauth, hook_useauth, concept_protectedroute [INFERRED 0.88]
- **Backend JWT Authentication Flow** — backend_security, api_deps, backend_config [EXTRACTED 0.95]
- **Optimistic Idea-to-Event Store Flow** — store_moveideato_timeline, store_moveeventtoidea, pattern_optimistic_update [EXTRACTED 0.92]
- **In-Memory SQLite Test Isolation via Fixtures** — tests_conftest, pattern_sqlite_test_isolation, db_session [EXTRACTED 0.90]
- **NLP Quick Add Pipeline: NLPService + GoogleMaps + QuickAddService -> Event** — nlp_parse_quick_add, googlemaps_find_place, quickadd_process_text, events_quickadd [EXTRACTED 0.95]
- **Idea Bin Ingestion Flow: Endpoint + IdeaBinService + GoogleMaps** — trips_ingest, ideabin_ingest_from_text, googlemaps_find_place [EXTRACTED 0.95]
- **Test Infrastructure: conftest + SQLite + auth_headers** — conftest_setup_db, sqlite_inmemory_test, conftest_auth_headers [EXTRACTED 0.90]

## Communities

### Community 0 - "SQLAlchemy Data Models"
Cohesion: 0.16
Nodes (29): IdeaBinItem, Trip, TripMember, User, Base, BaseModel, IdeaBinItem, IdeaBinItemBase (+21 more)

### Community 1 - "Trip Integration Tests"
Cohesion: 0.11
Nodes (26): create_trip(), Integration tests for trip endpoints including member management. Uses SQLite in, User A's trips must not appear in User B's list., test_create_trip_unauthenticated(), test_get_ideas_empty(), test_get_ideas_forbidden_for_non_member(), test_get_members_forbidden_non_member(), test_get_members_includes_creator() (+18 more)

### Community 2 - "Backend Core & Config"
Cohesion: 0.1
Nodes (32): API Dependencies (get_current_user), Settings / Config (config.py), FastAPI App Entry Point (main.py), Security Utilities (JWT + bcrypt), SQLAlchemy Declarative Base, Async DB Session & Engine, Event SQLAlchemy Model, IdeaBinItem SQLAlchemy Model (+24 more)

### Community 3 - "Event & Pydantic Schemas"
Cohesion: 0.15
Nodes (24): Event, Event, EventBase, EventCreate, EventUpdate, RippleRequest, create_event(), delete_event() (+16 more)

### Community 4 - "Test Infrastructure"
Cohesion: 0.11
Nodes (24): Base, auth_headers(), client(), Test Conftest Fixtures, override_get_db(), Shared fixtures for backend/tests/ integration tests. Uses an in-memory SQLite d, Create all tables before each test and drop after., Create all tables before each test, drop them after. (+16 more)

### Community 5 - "Architecture Vision Docs"
Cohesion: 0.09
Nodes (26): LLM Intent Extraction Pipeline (Architecture Concept), Offline-First Sync Layer (Architecture Concept), Ripple Engine (Architecture Concept), Timeline Map Split View (Architecture Concept), System Architecture Document, Concierge Phase Concept, Natural Language Quick Add Concept, Conflict Resolution and Ripple Engine Concept (+18 more)

### Community 6 - "Ingestion & Ripple API"
Cohesion: 0.19
Nodes (21): Events Ripple API (/events/ripple), Trip Ingest API (/trips/{id}/ingest), Idea Bin Ingestion Concept, Collaborators, ConciergeActionBar, GoogleMap, IdeaBin, Timeline (+13 more)

### Community 7 - "Trip Social & Navigation"
Cohesion: 0.18
Nodes (14): Trip Invite API (/trips/{id}/invite), Trips API Endpoint, Navbar, GSAP Animation Layer, localStorage Token Auth Pattern, ProtectedRoute Guard, TripGrid Component, View Transition API Navigation (+6 more)

### Community 8 - "Event API Tests"
Cohesion: 0.26
Nodes (9): create_trip(), Tests for /api/events/* endpoints:   GET  /events/?trip_id=   POST /events/rippl, Ripple on an empty trip returns an empty list., test_get_events_empty(), test_get_events_forbidden_for_non_member(), test_get_events_unauthenticated(), test_ripple_empty_itinerary(), test_ripple_forbidden_for_non_member() (+1 more)

### Community 9 - "Auth API Tests"
Cohesion: 0.18
Nodes (1): Tests for /api/users/* endpoints:   POST /register   POST /login   GET  /me

### Community 10 - "External Services (Maps + Bin)"
Cohesion: 0.2
Nodes (5): GoogleMapsService, IdeaBinService, test_ingest_from_text_empty(), test_ingest_from_text_success(), ingest_to_idea_bin()

### Community 11 - "Dashboard View"
Cohesion: 0.22
Nodes (3): fetchTrips(), getInitials(), handleCreateTrip()

### Community 12 - "Timeline Drag & Drop"
Cohesion: 0.27
Nodes (4): handleConfirm(), handleDropFromBin(), handleEventDrop(), parseTimeString()

### Community 13 - "NLP Pipeline"
Cohesion: 0.4
Nodes (2): NLPService, Parses a natural language string into a structured event object.         Example

### Community 14 - "Timeline Test Utilities"
Cohesion: 0.4
Nodes (0): 

### Community 15 - "Store Utility Helpers"
Cohesion: 0.4
Nodes (0): 

### Community 16 - "Navbar Component"
Cohesion: 0.5
Nodes (0): 

### Community 17 - "Idea Bin Component"
Cohesion: 0.5
Nodes (0): 

### Community 18 - "App Configuration"
Cohesion: 0.5
Nodes (2): BaseSettings, Settings

### Community 19 - "API Router"
Cohesion: 0.5
Nodes (4): Events Endpoint Router, API Main Router, Trips Endpoint Router, Users Endpoint Router

### Community 20 - "Trip Planner Page"
Cohesion: 0.67
Nodes (0): 

### Community 21 - "Store Test Utilities"
Cohesion: 0.67
Nodes (0): 

### Community 22 - "Auth Hook"
Cohesion: 1.0
Nodes (2): ProtectedRoute(), useAuth()

### Community 23 - "App Entrypoint"
Cohesion: 0.67
Nodes (0): 

### Community 24 - "Root Layout"
Cohesion: 1.0
Nodes (0): 

### Community 25 - "Login Page"
Cohesion: 1.0
Nodes (0): 

### Community 26 - "IdeaBin Test Mock"
Cohesion: 1.0
Nodes (0): 

### Community 27 - "TripHub Test Utilities"
Cohesion: 1.0
Nodes (0): 

### Community 28 - "Collaborators Component"
Cohesion: 1.0
Nodes (0): 

### Community 29 - "Google Map Component"
Cohesion: 1.0
Nodes (0): 

### Community 30 - "Concierge Action Bar"
Cohesion: 1.0
Nodes (0): 

### Community 31 - "VibeCheck Component"
Cohesion: 1.0
Nodes (0): 

### Community 32 - "DB Session"
Cohesion: 1.0
Nodes (0): 

### Community 33 - "Auth Dependencies"
Cohesion: 1.0
Nodes (0): 

### Community 34 - "API Init"
Cohesion: 1.0
Nodes (0): 

### Community 35 - "Vitest Setup"
Cohesion: 1.0
Nodes (2): Vitest Config, Test Setup

### Community 36 - "Build Config"
Cohesion: 1.0
Nodes (2): PostCSS Config, Tailwind Config

### Community 37 - "Next.js Types"
Cohesion: 1.0
Nodes (0): 

### Community 38 - "Tailwind Config"
Cohesion: 1.0
Nodes (0): 

### Community 39 - "Vitest Config"
Cohesion: 1.0
Nodes (0): 

### Community 40 - "PostCSS Config"
Cohesion: 1.0
Nodes (0): 

### Community 41 - "Landing Page"
Cohesion: 1.0
Nodes (0): 

### Community 42 - "Test Setup"
Cohesion: 1.0
Nodes (0): 

### Community 43 - "Backend Init"
Cohesion: 1.0
Nodes (0): 

### Community 44 - "Core Init"
Cohesion: 1.0
Nodes (0): 

### Community 45 - "Models Init"
Cohesion: 1.0
Nodes (0): 

### Community 46 - "Schemas Init"
Cohesion: 1.0
Nodes (0): 

### Community 47 - "DB Init"
Cohesion: 1.0
Nodes (0): 

### Community 48 - "Endpoints Init"
Cohesion: 1.0
Nodes (0): 

### Community 49 - "Services Init"
Cohesion: 1.0
Nodes (0): 

### Community 50 - "updateEventTime Action"
Cohesion: 1.0
Nodes (1): updateEventTime Action

### Community 51 - "reorderEvent Action"
Cohesion: 1.0
Nodes (1): reorderEvent Action

### Community 52 - "GET /users/me"
Cohesion: 1.0
Nodes (1): GET /users/me

### Community 53 - "PATCH /events"
Cohesion: 1.0
Nodes (1): PATCH /events/{event_id}

### Community 54 - "DELETE /events"
Cohesion: 1.0
Nodes (1): DELETE /events/{event_id}

### Community 55 - "GET /events"
Cohesion: 1.0
Nodes (1): GET /events/

### Community 56 - "GET /trips"
Cohesion: 1.0
Nodes (1): GET /trips/

### Community 57 - "POST /trips"
Cohesion: 1.0
Nodes (1): POST /trips/

### Community 58 - "GET /trips/{id}"
Cohesion: 1.0
Nodes (1): GET /trips/{trip_id}

### Community 59 - "GET /trips/{id}/ideas"
Cohesion: 1.0
Nodes (1): GET /trips/{trip_id}/ideas

### Community 60 - "GET /trips/{id}/members"
Cohesion: 1.0
Nodes (1): GET /trips/{trip_id}/members

### Community 61 - "Brainstorm Document"
Cohesion: 1.0
Nodes (1): Product Brainstorm Document

### Community 62 - "README"
Cohesion: 1.0
Nodes (1): README: Local Dev Setup

## Ambiguous Edges - Review These
- `Settings / Config (config.py)` → `LLM Itinerary Adaptation Intent (VibeCheck)`  [AMBIGUOUS]
  frontend/components/trip/VibeCheck.tsx · relation: references

## Knowledge Gaps
- **51 isolated node(s):** `Tests for /api/users/* endpoints:   POST /register   POST /login   GET  /me`, `User A's trips must not appear in User B's list.`, `Tests for /api/events/* endpoints:   GET  /events/?trip_id=   POST /events/rippl`, `Ripple on an empty trip returns an empty list.`, `Parses a natural language string into a structured event object.         Example` (+46 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Root Layout`** (2 nodes): `RootLayout()`, `layout.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Login Page`** (2 nodes): `handleSubmit()`, `page.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `IdeaBin Test Mock`** (2 nodes): `mockStore()`, `IdeaBin.test.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `TripHub Test Utilities`** (2 nodes): `makeFetch()`, `TripHub.test.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Collaborators Component`** (2 nodes): `Collaborators()`, `Collaborators.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Google Map Component`** (2 nodes): `GoogleMap()`, `GoogleMap.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Concierge Action Bar`** (2 nodes): `handleRunningLate()`, `ConciergeActionBar.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `VibeCheck Component`** (2 nodes): `VibeCheck.tsx`, `handleVibeSelect()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `DB Session`** (2 nodes): `get_db()`, `session.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Auth Dependencies`** (2 nodes): `get_current_user()`, `deps.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `API Init`** (2 nodes): `__init__.py`, `router.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Vitest Setup`** (2 nodes): `Vitest Config`, `Test Setup`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Build Config`** (2 nodes): `PostCSS Config`, `Tailwind Config`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Next.js Types`** (1 nodes): `next-env.d.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Tailwind Config`** (1 nodes): `tailwind.config.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Vitest Config`** (1 nodes): `vitest.config.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `PostCSS Config`** (1 nodes): `postcss.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Landing Page`** (1 nodes): `page.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Test Setup`** (1 nodes): `setup.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Backend Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Core Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Models Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Schemas Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `DB Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Endpoints Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Services Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `updateEventTime Action`** (1 nodes): `updateEventTime Action`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `reorderEvent Action`** (1 nodes): `reorderEvent Action`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `GET /users/me`** (1 nodes): `GET /users/me`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `PATCH /events`** (1 nodes): `PATCH /events/{event_id}`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `DELETE /events`** (1 nodes): `DELETE /events/{event_id}`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `GET /events`** (1 nodes): `GET /events/`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `GET /trips`** (1 nodes): `GET /trips/`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `POST /trips`** (1 nodes): `POST /trips/`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `GET /trips/{id}`** (1 nodes): `GET /trips/{trip_id}`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `GET /trips/{id}/ideas`** (1 nodes): `GET /trips/{trip_id}/ideas`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `GET /trips/{id}/members`** (1 nodes): `GET /trips/{trip_id}/members`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Brainstorm Document`** (1 nodes): `Product Brainstorm Document`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `README`** (1 nodes): `README: Local Dev Setup`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Settings / Config (config.py)` and `LLM Itinerary Adaptation Intent (VibeCheck)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `Base` connect `Test Infrastructure` to `SQLAlchemy Data Models`, `Event & Pydantic Schemas`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Why does `User` connect `SQLAlchemy Data Models` to `Event & Pydantic Schemas`, `Test Infrastructure`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Why does `IdeaBin Tests` connect `Ingestion & Ripple API` to `Architecture Vision Docs`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **Are the 17 inferred relationships involving `User` (e.g. with `Base` and `UserCreate`) actually correct?**
  _`User` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `TripMember` (e.g. with `Base` and `Create a single event (e.g. from idea bin drag-to-timeline).`) actually correct?**
  _`TripMember` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `Base` (e.g. with `Shared fixtures for backend/tests/ integration tests. Uses an in-memory SQLite d` and `Create all tables before each test and drop after.`) actually correct?**
  _`Base` has 13 INFERRED edges - model-reasoned connections that need verification._
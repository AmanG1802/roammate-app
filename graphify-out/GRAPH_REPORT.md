# Graph Report - .  (2026-04-17)

## Corpus Check
- Corpus is ~36,197 words - fits in a single context window. You may not need a graph.

## Summary
- 229 nodes · 638 edges · 39 communities detected
- Extraction: 34% EXTRACTED · 66% INFERRED · 0% AMBIGUOUS · INFERRED: 422 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Trip & Idea Schemas|Trip & Idea Schemas]]
- [[_COMMUNITY_Core Data Models|Core Data Models]]
- [[_COMMUNITY_Idea Bin Service|Idea Bin Service]]
- [[_COMMUNITY_Architecture Concepts|Architecture Concepts]]
- [[_COMMUNITY_Dashboard & Landing Pages|Dashboard & Landing Pages]]
- [[_COMMUNITY_Auth & DB Infrastructure|Auth & DB Infrastructure]]
- [[_COMMUNITY_Timeline Component|Timeline Component]]
- [[_COMMUNITY_IdeaBin Component|IdeaBin Component]]
- [[_COMMUNITY_Zustand Store|Zustand Store]]
- [[_COMMUNITY_DevOps & Docker Setup|DevOps & Docker Setup]]
- [[_COMMUNITY_Landing & Login Pages|Landing & Login Pages]]
- [[_COMMUNITY_Trip Planner Page|Trip Planner Page]]
- [[_COMMUNITY_Test Infrastructure|Test Infrastructure]]
- [[_COMMUNITY_Auth Hook|Auth Hook]]
- [[_COMMUNITY_Ripple Engine|Ripple Engine]]
- [[_COMMUNITY_FastAPI App Entry|FastAPI App Entry]]
- [[_COMMUNITY_CSS Config|CSS Config]]
- [[_COMMUNITY_Test Config|Test Config]]
- [[_COMMUNITY_Next.js Types|Next.js Types]]
- [[_COMMUNITY_Root Layout|Root Layout]]
- [[_COMMUNITY_Store Tests|Store Tests]]
- [[_COMMUNITY_Timeline Tests|Timeline Tests]]
- [[_COMMUNITY_TripHub Tests|TripHub Tests]]
- [[_COMMUNITY_Collaborators Component|Collaborators Component]]
- [[_COMMUNITY_Google Map Component|Google Map Component]]
- [[_COMMUNITY_Backend Init|Backend Init]]
- [[_COMMUNITY_Core Init|Core Init]]
- [[_COMMUNITY_Models Init|Models Init]]
- [[_COMMUNITY_Schemas Init|Schemas Init]]
- [[_COMMUNITY_DB Init|DB Init]]
- [[_COMMUNITY_API Init|API Init]]
- [[_COMMUNITY_Endpoints Init|Endpoints Init]]
- [[_COMMUNITY_Services Init|Services Init]]
- [[_COMMUNITY_Brainstorm Doc|Brainstorm Doc]]
- [[_COMMUNITY_Idea Bin Concept|Idea Bin Concept]]
- [[_COMMUNITY_README|README]]
- [[_COMMUNITY_Claude Config|Claude Config]]
- [[_COMMUNITY_Python Dependencies|Python Dependencies]]
- [[_COMMUNITY_Graph Report|Graph Report]]

## God Nodes (most connected - your core abstractions)
1. `Event` - 30 edges
2. `User` - 29 edges
3. `IdeaBinItem` - 28 edges
4. `TripMember` - 27 edges
5. `IdeaBinItem` - 26 edges
6. `IngestRequest` - 25 edges
7. `Get all trips where the current user is an accepted member,     including the us` - 21 edges
8. `Create a new trip and add the current user as the owner.     Auto-creates Day 1` - 21 edges
9. `Return all pending trip invitations for the current user.` - 21 edges
10. `Accept a pending trip invitation.` - 21 edges

## Surprising Connections (you probably didn't know these)
- `RippleEngine.shift_itinerary` --implements--> `Ripple Engine (Architecture Concept)`  [INFERRED]
  backend/app/services/ripple_engine.py → architecture.md
- `NLPService.parse_quick_add` --implements--> `LLM Intent Extraction Pipeline (Architecture Concept)`  [INFERRED]
  backend/app/services/nlp_service.py → architecture.md
- `Natural Language Quick Add Concept` --rationale_for--> `QuickAddService`  [INFERRED]
  roammate-brainstorm.md → backend/app/services/quick_add.py
- `RippleEngine` --conceptually_related_to--> `Concierge Phase Concept`  [INFERRED]
  backend/app/services/ripple_engine.py → roammate-brainstorm.md
- `LLM Itinerary Adaptation Intent (VibeCheck)` --references--> `Settings / Config (config.py)`  [AMBIGUOUS]
  frontend/components/trip/VibeCheck.tsx → backend/app/core/config.py

## Hyperedges (group relationships)
- **Authentication Guard Flow (Login → Token → ProtectedRoute)** — page_login, concept_localstoragauth, hook_useauth, concept_protectedroute [INFERRED 0.88]
- **In-Memory SQLite Test Isolation via Fixtures** — tests_conftest, pattern_sqlite_test_isolation, db_session [EXTRACTED 0.90]
- **Backend JWT Authentication Flow** — backend_security, api_deps, backend_config [EXTRACTED 0.95]
- **NLP Quick Add Pipeline: NLPService + GoogleMaps + QuickAddService -> Event** — nlp_parse_quick_add, googlemaps_find_place, quickadd_process_text, events_quickadd [EXTRACTED 0.95]
- **Test Infrastructure: conftest + SQLite + auth_headers** — conftest_setup_db, sqlite_inmemory_test, conftest_auth_headers [EXTRACTED 0.90]

## Communities

### Community 0 - "Trip & Idea Schemas"
Cohesion: 0.36
Nodes (40): Trip, TripDay, BaseModel, IdeaBinItem, IdeaBinItemBase, IdeaBinItemCreate, IngestRequest, InvitationOut (+32 more)

### Community 1 - "Core Data Models"
Cohesion: 0.15
Nodes (33): Event, IdeaBinItem, TripMember, User, Base, auth_headers Fixture, Event, EventBase (+25 more)

### Community 2 - "Idea Bin Service"
Cohesion: 0.08
Nodes (21): _extract_time_hint(), IdeaBinService, Pull a time fragment like '2pm' or '14:00' from free-form text., Remove the time portion so the title stays clean., _strip_time_hint(), accept_invitation(), add_trip_day(), create_trip() (+13 more)

### Community 3 - "Architecture Concepts"
Cohesion: 0.11
Nodes (20): LLM Intent Extraction Pipeline (Architecture Concept), Offline-First Sync Layer (Architecture Concept), Ripple Engine (Architecture Concept), Timeline Map Split View (Architecture Concept), System Architecture Document, Concierge Phase Concept, Natural Language Quick Add Concept, Conflict Resolution and Ripple Engine Concept (+12 more)

### Community 4 - "Dashboard & Landing Pages"
Cohesion: 0.16
Nodes (4): fetchTrips(), getInitials(), handleAcceptInvite(), handleCreateTrip()

### Community 5 - "Auth & DB Infrastructure"
Cohesion: 0.2
Nodes (12): API Dependencies (get_current_user), Settings / Config (config.py), Security Utilities (JWT + bcrypt), SQLAlchemy Declarative Base, Async DB Session & Engine, SQLite In-Memory Test Isolation Pattern, API Test Fixtures (conftest.py), Auth API Tests (+4 more)

### Community 6 - "Timeline Component"
Cohesion: 0.27
Nodes (4): handleConfirm(), handleDropFromBin(), handleEventDrop(), parseTimeString()

### Community 7 - "IdeaBin Component"
Cohesion: 0.29
Nodes (2): handleSaveTime(), timeValueToHint()

### Community 8 - "Zustand Store"
Cohesion: 0.33
Nodes (0): 

### Community 9 - "DevOps & Docker Setup"
Cohesion: 0.33
Nodes (6): App Running Guide, Docker Development Workflow, Colima Container Runtime, Docker Setup Guide, PostgreSQL Service Config, Redis Service Config

### Community 10 - "Landing & Login Pages"
Cohesion: 0.4
Nodes (5): Navbar, GSAP Animation Layer, localStorage Token Auth Pattern, Home Landing Page, LoginPage

### Community 11 - "Trip Planner Page"
Cohesion: 0.4
Nodes (0): 

### Community 12 - "Test Infrastructure"
Cohesion: 0.4
Nodes (5): Test Conftest Fixtures, setup_db Fixture (In-Memory SQLite), SQLite In-Memory Test Database, Test: Trips Integration, Test Suite README

### Community 13 - "Auth Hook"
Cohesion: 0.67
Nodes (2): ProtectedRoute(), useAuth()

### Community 14 - "Ripple Engine"
Cohesion: 0.67
Nodes (3): Events Ripple API (/events/ripple), ConciergeActionBar, Ripple Engine (Running Late)

### Community 15 - "FastAPI App Entry"
Cohesion: 0.67
Nodes (0): 

### Community 16 - "CSS Config"
Cohesion: 1.0
Nodes (2): PostCSS Config, Tailwind Config

### Community 17 - "Test Config"
Cohesion: 1.0
Nodes (2): Vitest Config, Test Setup

### Community 18 - "Next.js Types"
Cohesion: 1.0
Nodes (0): 

### Community 19 - "Root Layout"
Cohesion: 1.0
Nodes (1): RootLayout

### Community 20 - "Store Tests"
Cohesion: 1.0
Nodes (1): Store Tests

### Community 21 - "Timeline Tests"
Cohesion: 1.0
Nodes (1): Timeline Tests

### Community 22 - "TripHub Tests"
Cohesion: 1.0
Nodes (1): TripHub Tests

### Community 23 - "Collaborators Component"
Cohesion: 1.0
Nodes (1): Collaborators

### Community 24 - "Google Map Component"
Cohesion: 1.0
Nodes (1): GoogleMap

### Community 25 - "Backend Init"
Cohesion: 1.0
Nodes (0): 

### Community 26 - "Core Init"
Cohesion: 1.0
Nodes (0): 

### Community 27 - "Models Init"
Cohesion: 1.0
Nodes (0): 

### Community 28 - "Schemas Init"
Cohesion: 1.0
Nodes (0): 

### Community 29 - "DB Init"
Cohesion: 1.0
Nodes (0): 

### Community 30 - "API Init"
Cohesion: 1.0
Nodes (0): 

### Community 31 - "Endpoints Init"
Cohesion: 1.0
Nodes (0): 

### Community 32 - "Services Init"
Cohesion: 1.0
Nodes (0): 

### Community 33 - "Brainstorm Doc"
Cohesion: 1.0
Nodes (1): Product Brainstorm Document

### Community 34 - "Idea Bin Concept"
Cohesion: 1.0
Nodes (1): Idea Bin Ingestion Concept

### Community 35 - "README"
Cohesion: 1.0
Nodes (1): README: Local Dev Setup

### Community 36 - "Claude Config"
Cohesion: 1.0
Nodes (1): Claude AI Config

### Community 37 - "Python Dependencies"
Cohesion: 1.0
Nodes (1): Python Dependencies

### Community 38 - "Graph Report"
Cohesion: 1.0
Nodes (1): Graph Report

## Ambiguous Edges - Review These
- `LLM Itinerary Adaptation Intent (VibeCheck)` → `Settings / Config (config.py)`  [AMBIGUOUS]
  frontend/components/trip/VibeCheck.tsx · relation: references

## Knowledge Gaps
- **44 isolated node(s):** `Tailwind Config`, `Vitest Config`, `PostCSS Config`, `RootLayout`, `GSAP Animation Layer` (+39 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `CSS Config`** (2 nodes): `PostCSS Config`, `Tailwind Config`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Test Config`** (2 nodes): `Vitest Config`, `Test Setup`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Next.js Types`** (1 nodes): `next-env.d.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Root Layout`** (1 nodes): `RootLayout`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Store Tests`** (1 nodes): `Store Tests`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Timeline Tests`** (1 nodes): `Timeline Tests`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `TripHub Tests`** (1 nodes): `TripHub Tests`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Collaborators Component`** (1 nodes): `Collaborators`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Google Map Component`** (1 nodes): `GoogleMap`
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
- **Thin community `API Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Endpoints Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Services Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Brainstorm Doc`** (1 nodes): `Product Brainstorm Document`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Idea Bin Concept`** (1 nodes): `Idea Bin Ingestion Concept`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `README`** (1 nodes): `README: Local Dev Setup`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Claude Config`** (1 nodes): `Claude AI Config`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Python Dependencies`** (1 nodes): `Python Dependencies`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Graph Report`** (1 nodes): `Graph Report`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `LLM Itinerary Adaptation Intent (VibeCheck)` and `Settings / Config (config.py)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `Event` connect `Core Data Models` to `Trip & Idea Schemas`, `Architecture Concepts`?**
  _High betweenness centrality (0.089) - this node is a cross-community bridge._
- **Why does `User` connect `Core Data Models` to `Trip & Idea Schemas`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **Why does `QuickAddService.process_text` connect `Architecture Concepts` to `Core Data Models`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **Are the 28 inferred relationships involving `Event` (e.g. with `Create a single event (e.g. from idea bin drag-to-timeline).` and `Update event time or sort_order.`) actually correct?**
  _`Event` has 28 INFERRED edges - model-reasoned connections that need verification._
- **Are the 27 inferred relationships involving `User` (e.g. with `Users Endpoint Router` and `POST /users/register`) actually correct?**
  _`User` has 27 INFERRED edges - model-reasoned connections that need verification._
- **Are the 26 inferred relationships involving `IdeaBinItem` (e.g. with `Create a single event (e.g. from idea bin drag-to-timeline).` and `Update event time or sort_order.`) actually correct?**
  _`IdeaBinItem` has 26 INFERRED edges - model-reasoned connections that need verification._
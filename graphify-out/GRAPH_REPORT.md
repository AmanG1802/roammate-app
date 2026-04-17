# Graph Report - .  (2026-04-17)

## Corpus Check
- 71 files · ~45,863 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 375 nodes · 1371 edges · 53 communities detected
- Extraction: 29% EXTRACTED · 71% INFERRED · 0% AMBIGUOUS · INFERRED: 979 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]

## God Nodes (most connected - your core abstractions)
1. `User` - 58 edges
2. `TripMember` - 57 edges
3. `Event` - 55 edges
4. `IdeaBinItem` - 54 edges
5. `IdeaBinItem` - 52 edges
6. `IngestRequest` - 48 edges
7. `Trip` - 39 edges
8. `TripDay` - 36 edges
9. `InvitationOut` - 36 edges
10. `TripWithRole` - 36 edges

## Surprising Connections (you probably didn't know these)
- `RippleEngine` --conceptually_related_to--> `Concierge Phase Concept`  [INFERRED]
  backend/app/services/ripple_engine.py → roammate-brainstorm.md
- `NLPService.parse_quick_add` --implements--> `LLM Intent Extraction Pipeline (Architecture Concept)`  [INFERRED]
  backend/app/services/nlp_service.py → architecture.md
- `QuickAddService` --rationale_for--> `Natural Language Quick Add Concept`  [INFERRED]
  backend/app/services/quick_add.py → roammate-brainstorm.md
- `RippleEngine.shift_itinerary` --implements--> `Ripple Engine (Architecture Concept)`  [INFERRED]
  backend/app/services/ripple_engine.py → architecture.md
- `LLM Itinerary Adaptation Intent (VibeCheck)` --references--> `Settings / Config (config.py)`  [AMBIGUOUS]
  frontend/components/trip/VibeCheck.tsx → backend/app/core/config.py

## Hyperedges (group relationships)
- **Authentication Guard Flow (Login → Token → ProtectedRoute)** — page_login, concept_localstoragauth, hook_useauth, concept_protectedroute [INFERRED 0.88]
- **In-Memory SQLite Test Isolation via Fixtures** — tests_conftest, pattern_sqlite_test_isolation, db_session [EXTRACTED 0.90]
- **Backend JWT Authentication Flow** — backend_security, api_deps, backend_config [EXTRACTED 0.95]
- **NLP Quick Add Pipeline: NLPService + GoogleMaps + QuickAddService -> Event** — nlp_parse_quick_add, googlemaps_find_place, quickadd_process_text, events_quickadd [EXTRACTED 0.95]
- **Test Infrastructure: conftest + SQLite + auth_headers** — conftest_setup_db, sqlite_inmemory_test, conftest_auth_headers [EXTRACTED 0.90]

## Communities

### Community 0 - "Community 0"
Cohesion: 0.38
Nodes (54): Notification, Trip, TripDay, NotificationType, IdeaBinItem, IngestRequest, InvitationOut, InviteRequest (+46 more)

### Community 1 - "Community 1"
Cohesion: 0.13
Nodes (40): Group, GroupMember, BaseModel, GroupBase, GroupCreate, GroupDetailOut, GroupInvitationOut, GroupInviteRequest (+32 more)

### Community 2 - "Community 2"
Cohesion: 0.22
Nodes (34): Event, IdeaBinItem, TripMember, User, Base, auth_headers Fixture, Event, EventBase (+26 more)

### Community 3 - "Community 3"
Cohesion: 0.11
Nodes (26): create_event(), delete_event(), get_events(), move_event_to_bin(), quick_add_event(), trigger_ripple_engine(), update_event(), emit() (+18 more)

### Community 4 - "Community 4"
Cohesion: 0.12
Nodes (17): LLM Intent Extraction Pipeline (Architecture Concept), Offline-First Sync Layer (Architecture Concept), Ripple Engine (Architecture Concept), Timeline Map Split View (Architecture Concept), System Architecture Document, Concierge Phase Concept, Natural Language Quick Add Concept, Conflict Resolution and Ripple Engine Concept (+9 more)

### Community 5 - "Community 5"
Cohesion: 0.22
Nodes (16): create_group(), create_trip(), Integration tests for groups: create, invite, accept/decline, attach trip., Bob accepts membership as a 'member', then tries to invite — should 403., Bob is group admin (his own group), but the trip belongs to Alice — attach must, test_accept_group_invitation(), test_attach_trip_as_admin_succeeds(), test_attach_trip_requires_trip_admin() (+8 more)

### Community 6 - "Community 6"
Cohesion: 0.16
Nodes (4): fetchTrips(), getInitials(), handleAcceptInvite(), handleCreateTrip()

### Community 7 - "Community 7"
Cohesion: 0.2
Nodes (12): API Dependencies (get_current_user), Settings / Config (config.py), Security Utilities (JWT + bcrypt), SQLAlchemy Declarative Base, Async DB Session & Engine, SQLite In-Memory Test Isolation Pattern, API Test Fixtures (conftest.py), Auth API Tests (+4 more)

### Community 8 - "Community 8"
Cohesion: 0.38
Nodes (9): accept(), attach(), auth(), authJson(), decline(), handleDelete(), handleDetachTrip(), handleRemoveMember() (+1 more)

### Community 9 - "Community 9"
Cohesion: 0.27
Nodes (4): handleConfirm(), handleDropFromBin(), handleEventDrop(), parseTimeString()

### Community 10 - "Community 10"
Cohesion: 0.29
Nodes (6): ActorSummary, NotificationOut, UnreadCountOut, list_notifications(), Most recent notifications for the current user., unread_count()

### Community 11 - "Community 11"
Cohesion: 0.42
Nodes (8): get_today_widget(), _pick_trip(), Pick the most relevant trip for the Today Widget.      Priority: in_trip (active, Return a contextual snapshot for the dashboard hero based on trip state., _to_date(), TodayEvent, TodayTrip, TodayWidgetOut

### Community 12 - "Community 12"
Cohesion: 0.31
Nodes (8): create_trip(), Integration tests for notification fan-out, listing, and read-state., Bob should not see Alice's self-only trip_created notification., test_invite_creates_notification_for_invitee(), test_mark_all_read_zeros_unread(), test_mark_read_decrements_unread(), test_notifications_isolated_between_users(), test_trip_create_emits_self_notification()

### Community 13 - "Community 13"
Cohesion: 0.36
Nodes (7): make_trip(), Integration tests for the /dashboard/today endpoint., test_today_in_trip_when_today_within_range(), test_today_isolated_per_user(), test_today_post_trip_within_30d(), test_today_pre_trip_with_future_start(), test_today_prefers_active_over_upcoming()

### Community 14 - "Community 14"
Cohesion: 0.29
Nodes (2): handleSaveTime(), timeValueToHint()

### Community 15 - "Community 15"
Cohesion: 0.32
Nodes (6): _extract_time_hint(), IdeaBinService, Pull a time fragment like '2pm' or '14:00' from free-form text., Remove the time portion so the title stays clean., _strip_time_hint(), ingest_to_idea_bin()

### Community 16 - "Community 16"
Cohesion: 0.29
Nodes (0): 

### Community 17 - "Community 17"
Cohesion: 0.33
Nodes (0): 

### Community 18 - "Community 18"
Cohesion: 0.33
Nodes (6): App Running Guide, Docker Development Workflow, Colima Container Runtime, Docker Setup Guide, PostgreSQL Service Config, Redis Service Config

### Community 19 - "Community 19"
Cohesion: 0.4
Nodes (5): Navbar, GSAP Animation Layer, localStorage Token Auth Pattern, Home Landing Page, LoginPage

### Community 20 - "Community 20"
Cohesion: 0.4
Nodes (0): 

### Community 21 - "Community 21"
Cohesion: 0.5
Nodes (0): 

### Community 22 - "Community 22"
Cohesion: 0.67
Nodes (2): ProtectedRoute(), useAuth()

### Community 23 - "Community 23"
Cohesion: 0.67
Nodes (3): Events Ripple API (/events/ripple), ConciergeActionBar, Ripple Engine (Running Late)

### Community 24 - "Community 24"
Cohesion: 0.67
Nodes (0): 

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (2): PostCSS Config, Tailwind Config

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (2): Vitest Config, Test Setup

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (2): setup_db Fixture (In-Memory SQLite), SQLite In-Memory Test Database

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (2): Test Conftest Fixtures, Test: Trips Integration

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (0): 

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): RootLayout

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Store Tests

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): Timeline Tests

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): TripHub Tests

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (1): Collaborators

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (1): GoogleMap

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (0): 

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (0): 

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (0): 

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (0): 

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (0): 

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (0): 

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (0): 

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (0): 

### Community 44 - "Community 44"
Cohesion: 1.0
Nodes (0): 

### Community 45 - "Community 45"
Cohesion: 1.0
Nodes (1): NLPService

### Community 46 - "Community 46"
Cohesion: 1.0
Nodes (1): Product Brainstorm Document

### Community 47 - "Community 47"
Cohesion: 1.0
Nodes (1): Idea Bin Ingestion Concept

### Community 48 - "Community 48"
Cohesion: 1.0
Nodes (1): README: Local Dev Setup

### Community 49 - "Community 49"
Cohesion: 1.0
Nodes (1): Test Suite README

### Community 50 - "Community 50"
Cohesion: 1.0
Nodes (1): Claude AI Config

### Community 51 - "Community 51"
Cohesion: 1.0
Nodes (1): Python Dependencies

### Community 52 - "Community 52"
Cohesion: 1.0
Nodes (1): Graph Report

## Ambiguous Edges - Review These
- `LLM Itinerary Adaptation Intent (VibeCheck)` → `Settings / Config (config.py)`  [AMBIGUOUS]
  frontend/components/trip/VibeCheck.tsx · relation: references

## Knowledge Gaps
- **54 isolated node(s):** `Tailwind Config`, `Vitest Config`, `PostCSS Config`, `RootLayout`, `GSAP Animation Layer` (+49 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 25`** (2 nodes): `PostCSS Config`, `Tailwind Config`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (2 nodes): `Vitest Config`, `Test Setup`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (2 nodes): `setup_db Fixture (In-Memory SQLite)`, `SQLite In-Memory Test Database`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (2 nodes): `Test Conftest Fixtures`, `Test: Trips Integration`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `next-env.d.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `RootLayout`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `Store Tests`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `Timeline Tests`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `TripHub Tests`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `Collaborators`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `GoogleMap`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `router.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (1 nodes): `NLPService`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (1 nodes): `Product Brainstorm Document`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (1 nodes): `Idea Bin Ingestion Concept`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (1 nodes): `README: Local Dev Setup`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (1 nodes): `Test Suite README`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (1 nodes): `Claude AI Config`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (1 nodes): `Python Dependencies`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (1 nodes): `Graph Report`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `LLM Itinerary Adaptation Intent (VibeCheck)` and `Settings / Config (config.py)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `Event` connect `Community 2` to `Community 0`, `Community 11`, `Community 4`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Why does `User` connect `Community 2` to `Community 0`, `Community 1`, `Community 10`, `Community 11`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Why does `TripMember` connect `Community 2` to `Community 0`, `Community 1`, `Community 11`, `Community 3`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Are the 56 inferred relationships involving `User` (e.g. with `Users Endpoint Router` and `POST /users/register`) actually correct?**
  _`User` has 56 INFERRED edges - model-reasoned connections that need verification._
- **Are the 55 inferred relationships involving `TripMember` (e.g. with `Create a single event (e.g. from idea bin drag-to-timeline).` and `Update event time or sort_order.`) actually correct?**
  _`TripMember` has 55 INFERRED edges - model-reasoned connections that need verification._
- **Are the 53 inferred relationships involving `Event` (e.g. with `Create a single event (e.g. from idea bin drag-to-timeline).` and `Update event time or sort_order.`) actually correct?**
  _`Event` has 53 INFERRED edges - model-reasoned connections that need verification._
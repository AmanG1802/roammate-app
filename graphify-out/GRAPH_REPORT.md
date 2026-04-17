# Graph Report - .  (2026-04-18)

## Corpus Check
- 81 files · ~52,153 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 517 nodes · 2053 edges · 58 communities detected
- Extraction: 29% EXTRACTED · 71% INFERRED · 0% AMBIGUOUS · INFERRED: 1463 edges (avg confidence: 0.52)
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
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]

## God Nodes (most connected - your core abstractions)
1. `User` - 86 edges
2. `TripMember` - 86 edges
3. `IdeaBinItem` - 77 edges
4. `Event` - 76 edges
5. `IdeaBinItem` - 75 edges
6. `IngestRequest` - 63 edges
7. `Trip` - 57 edges
8. `NotificationType` - 50 edges
9. `TripDay` - 45 edges
10. `InvitationOut` - 45 edges

## Surprising Connections (you probably didn't know these)
- `NLPService.parse_quick_add` --implements--> `LLM Intent Extraction Pipeline (Architecture Concept)`  [INFERRED]
  backend/app/services/nlp_service.py → architecture.md
- `QuickAddService` --rationale_for--> `Natural Language Quick Add Concept`  [INFERRED]
  backend/app/services/quick_add.py → roammate-brainstorm.md
- `RippleEngine` --conceptually_related_to--> `Concierge Phase Concept`  [INFERRED]
  backend/app/services/ripple_engine.py → roammate-brainstorm.md
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
Cohesion: 0.35
Nodes (65): Event, Notification, Trip, TripDay, IdeaBinItem, IdeaBinItemBase, IdeaBinItemCreate, IngestRequest (+57 more)

### Community 1 - "Community 1"
Cohesion: 0.16
Nodes (46): Group, GroupMember, BaseModel, GroupBase, GroupCreate, GroupDetailOut, GroupInvitationOut, GroupInviteRequest (+38 more)

### Community 2 - "Community 2"
Cohesion: 0.18
Nodes (46): EventVote, IdeaBinItem, IdeaVote, TripMember, User, Base, Event, EventBase (+38 more)

### Community 3 - "Community 3"
Cohesion: 0.09
Nodes (31): create_event(), delete_event(), get_events(), move_event_to_bin(), quick_add_event(), trigger_ripple_engine(), update_event(), _extract_time_hint() (+23 more)

### Community 4 - "Community 4"
Cohesion: 0.12
Nodes (22): IdeaTag, copy_idea_to_trip(), list_idea_tags(), Idea-scoped endpoints: tags + cross-trip copy (provenance)., Replace the tag list for this idea. Requires admin or view_with_vote., Copy an idea into another trip, preserving provenance via origin_idea_id.     Ca, set_idea_tags(), CopyIdeaRequest (+14 more)

### Community 5 - "Community 5"
Cohesion: 0.11
Nodes (19): LLM Intent Extraction Pipeline (Architecture Concept), Offline-First Sync Layer (Architecture Concept), Ripple Engine (Architecture Concept), Timeline Map Split View (Architecture Concept), System Architecture Document, Concierge Phase Concept, Natural Language Quick Add Concept, Conflict Resolution and Ripple Engine Concept (+11 more)

### Community 6 - "Community 6"
Cohesion: 0.27
Nodes (18): create_event(), create_idea(), create_trip(), invite(), invite_and_accept(), Votes on ideas + events: role gating, tally, vote transfer on move-to-bin / bin-, Invite invitee and have them accept — returns the TripMember dict., test_admin_can_vote_on_event() (+10 more)

### Community 7 - "Community 7"
Cohesion: 0.31
Nodes (16): _classify(), get_today_widget(), _pick_default(), Pick the most relevant trip for the Today Widget.      Priority: in_trip (active, Bucket and cap trips: up to 1 active, MAX_PAST past, MAX_UPCOMING upcoming., One page of the widget carousel — a single trip in context., Return the index into the merged pages list that should display first.      Prio, Return the default page index. Page order: past … | active | upcoming …      Pri (+8 more)

### Community 8 - "Community 8"
Cohesion: 0.22
Nodes (16): create_group(), create_trip(), Integration tests for groups: create, invite, accept/decline, attach trip., Bob accepts membership as a 'member', then tries to invite — should 403., Bob is group admin (his own group), but the trip belongs to Alice — attach must, test_accept_group_invitation(), test_attach_trip_as_admin_succeeds(), test_attach_trip_requires_trip_admin() (+8 more)

### Community 9 - "Community 9"
Cohesion: 0.36
Nodes (15): attach_trip(), create_group(), create_idea(), create_trip(), Group library: search, tag filter, provenance (origin_idea_id), cross-trip copy., Bob tries to copy Alice's idea into his own trip — must 403 because Bob isn't on, test_copy_idea_sets_origin_and_carries_tags(), test_copy_requires_membership_on_target() (+7 more)

### Community 10 - "Community 10"
Cohesion: 0.23
Nodes (14): _default_page(), make_trip(), Integration tests for the /dashboard/today endpoint., Max 2 past, max 3 upcoming shown., When no active trip, default to past if it's closer than upcoming., Pages must be ordered: past → active → upcoming., test_today_caps_past_at_2_upcoming_at_3(), test_today_default_index_closer_past() (+6 more)

### Community 11 - "Community 11"
Cohesion: 0.13
Nodes (1): getInitials()

### Community 12 - "Community 12"
Cohesion: 0.17
Nodes (12): _get_existing_columns(), _get_existing_constraints(), _get_existing_indexes(), _pg_col_type(), Automatic schema sync: diffs SQLAlchemy metadata against the live PostgreSQL cat, Render a PostgreSQL column type + inline constraints from a SA Column., Return {(table_name, column_name)} for all columns in the public schema., Return {index_name} for all indexes in the public schema. (+4 more)

### Community 13 - "Community 13"
Cohesion: 0.2
Nodes (12): API Dependencies (get_current_user), Settings / Config (config.py), Security Utilities (JWT + bcrypt), SQLAlchemy Declarative Base, Async DB Session & Engine, SQLite In-Memory Test Isolation Pattern, API Test Fixtures (conftest.py), Auth API Tests (+4 more)

### Community 14 - "Community 14"
Cohesion: 0.25
Nodes (7): ActorSummary, is_enabled(), NotificationOut, UnreadCountOut, list_notifications(), Most recent notifications for the current user., unread_count()

### Community 15 - "Community 15"
Cohesion: 0.38
Nodes (9): accept(), attach(), auth(), authJson(), decline(), handleDelete(), handleDetachTrip(), handleRemoveMember() (+1 more)

### Community 16 - "Community 16"
Cohesion: 0.27
Nodes (4): handleConfirm(), handleDropFromBin(), handleEventDrop(), parseTimeString()

### Community 17 - "Community 17"
Cohesion: 0.2
Nodes (7): auth_headers(), Shared fixtures for backend/tests/ integration tests. Uses an in-memory SQLite d, Create all tables before each test, drop them after., Register + login the primary test user, return Bearer headers., Register + login a second user (for permission tests)., second_auth_headers(), setup_db()

### Community 18 - "Community 18"
Cohesion: 0.31
Nodes (8): create_trip(), Integration tests for notification fan-out, listing, and read-state., Bob should not see Alice's self-only trip_created notification., test_invite_creates_notification_for_invitee(), test_mark_all_read_zeros_unread(), test_mark_read_decrements_unread(), test_notifications_isolated_between_users(), test_trip_create_emits_self_notification()

### Community 19 - "Community 19"
Cohesion: 0.29
Nodes (2): handleSaveTime(), timeValueToHint()

### Community 20 - "Community 20"
Cohesion: 0.46
Nodes (7): create_trip(), invite_and_accept(), Ripple Engine access gating — only trip admins may fire it., test_admin_can_fire_ripple(), test_non_member_cannot_fire_ripple(), test_view_only_cannot_fire_ripple(), test_view_with_vote_cannot_fire_ripple()

### Community 21 - "Community 21"
Cohesion: 0.29
Nodes (0): 

### Community 22 - "Community 22"
Cohesion: 0.33
Nodes (0): 

### Community 23 - "Community 23"
Cohesion: 0.33
Nodes (6): App Running Guide, Docker Development Workflow, Colima Container Runtime, Docker Setup Guide, PostgreSQL Service Config, Redis Service Config

### Community 24 - "Community 24"
Cohesion: 0.4
Nodes (5): Navbar, GSAP Animation Layer, localStorage Token Auth Pattern, Home Landing Page, LoginPage

### Community 25 - "Community 25"
Cohesion: 0.4
Nodes (0): 

### Community 26 - "Community 26"
Cohesion: 0.5
Nodes (0): 

### Community 27 - "Community 27"
Cohesion: 0.67
Nodes (2): ProtectedRoute(), useAuth()

### Community 28 - "Community 28"
Cohesion: 0.67
Nodes (0): 

### Community 29 - "Community 29"
Cohesion: 0.67
Nodes (3): Events Ripple API (/events/ripple), ConciergeActionBar, Ripple Engine (Running Late)

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (2): PostCSS Config, Tailwind Config

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (2): Vitest Config, Test Setup

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (0): 

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): RootLayout

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (1): Store Tests

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (1): Timeline Tests

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (1): TripHub Tests

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (1): Collaborators

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (1): GoogleMap

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
Nodes (0): 

### Community 46 - "Community 46"
Cohesion: 1.0
Nodes (0): 

### Community 47 - "Community 47"
Cohesion: 1.0
Nodes (0): 

### Community 48 - "Community 48"
Cohesion: 1.0
Nodes (1): NLPService

### Community 49 - "Community 49"
Cohesion: 1.0
Nodes (1): Test: Trips Integration

### Community 50 - "Community 50"
Cohesion: 1.0
Nodes (1): Return the default page from the paginated widget response.

### Community 51 - "Community 51"
Cohesion: 1.0
Nodes (1): Product Brainstorm Document

### Community 52 - "Community 52"
Cohesion: 1.0
Nodes (1): Idea Bin Ingestion Concept

### Community 53 - "Community 53"
Cohesion: 1.0
Nodes (1): README: Local Dev Setup

### Community 54 - "Community 54"
Cohesion: 1.0
Nodes (1): Test Suite README

### Community 55 - "Community 55"
Cohesion: 1.0
Nodes (1): Claude AI Config

### Community 56 - "Community 56"
Cohesion: 1.0
Nodes (1): Python Dependencies

### Community 57 - "Community 57"
Cohesion: 1.0
Nodes (1): Graph Report

## Ambiguous Edges - Review These
- `LLM Itinerary Adaptation Intent (VibeCheck)` → `Settings / Config (config.py)`  [AMBIGUOUS]
  frontend/components/trip/VibeCheck.tsx · relation: references

## Knowledge Gaps
- **71 isolated node(s):** `Tailwind Config`, `Vitest Config`, `PostCSS Config`, `RootLayout`, `GSAP Animation Layer` (+66 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 30`** (2 nodes): `PostCSS Config`, `Tailwind Config`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (2 nodes): `Vitest Config`, `Test Setup`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `next-env.d.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `RootLayout`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `Store Tests`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `Timeline Tests`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (1 nodes): `TripHub Tests`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (1 nodes): `Collaborators`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (1 nodes): `GoogleMap`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (1 nodes): `router.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (1 nodes): `NLPService`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (1 nodes): `Test: Trips Integration`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (1 nodes): `Return the default page from the paginated widget response.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (1 nodes): `Product Brainstorm Document`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (1 nodes): `Idea Bin Ingestion Concept`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (1 nodes): `README: Local Dev Setup`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 54`** (1 nodes): `Test Suite README`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 55`** (1 nodes): `Claude AI Config`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 56`** (1 nodes): `Python Dependencies`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 57`** (1 nodes): `Graph Report`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `LLM Itinerary Adaptation Intent (VibeCheck)` and `Settings / Config (config.py)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `Event` connect `Community 0` to `Community 2`, `Community 5`, `Community 7`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Why does `User` connect `Community 2` to `Community 0`, `Community 1`, `Community 4`, `Community 7`, `Community 14`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Why does `TripMember` connect `Community 2` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 7`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Are the 84 inferred relationships involving `User` (e.g. with `Users Endpoint Router` and `POST /users/register`) actually correct?**
  _`User` has 84 INFERRED edges - model-reasoned connections that need verification._
- **Are the 84 inferred relationships involving `TripMember` (e.g. with `Create a single event (e.g. from idea bin drag-to-timeline).` and `Update event time or sort_order.`) actually correct?**
  _`TripMember` has 84 INFERRED edges - model-reasoned connections that need verification._
- **Are the 75 inferred relationships involving `IdeaBinItem` (e.g. with `Create a single event (e.g. from idea bin drag-to-timeline).` and `Update event time or sort_order.`) actually correct?**
  _`IdeaBinItem` has 75 INFERRED edges - model-reasoned connections that need verification._
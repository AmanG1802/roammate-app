# Roammate System Architecture & Design

## 1. Executive Summary

**Product:** Roammate - Itinerary Planner and Visualiser
**Core Architecture:** Next.js (React) Frontend + Python (FastAPI) Backend + PostgreSQL (with PostGIS).

This document outlines the detailed system architecture and design to build Roammate, an adaptive itinerary planner with an intelligent "Concierge" phase.

---

## 2. Technology Stack

### 2.1 Frontend: Next.js (React)
- **Framework:** Next.js with App Router for SSR/SSG and Client Components for highly interactive sections.
- **Styling:** Tailwind CSS with Shadcn UI/Radix UI.
- **State Management & Data Fetching:** React Query for API state and optimistic UI updates.
- **Offline & Sync:** Standard caching + optimistic UI. IndexedDB (via Dexie.js) for local caching. A sync queue handles offline mutations.
- **Mapping Provider:** Google Maps (Maps JavaScript API, Places API).

### 2.2 Backend: Python (FastAPI)
- **Framework:** FastAPI for asynchronous REST APIs.
- **AI/NLP Pipeline:** LangChain or direct OpenAI/Anthropic SDKs for the LLM Intent Extraction Pipeline.
- **Core Engines:**
  - **Ripple Engine:** Python-based conflict resolution and time-shifting logic.
  - **Graph Routing:** Algorithms for geographic activity clustering and optimization.
- **Task Queue:** Celery with Redis for background jobs (scraping, weather, alerts).

### 2.3 Database
- **Primary Database:** PostgreSQL with PostGIS for geospatial queries.
- **Caching & Rate Limiting:** Redis.
- **ORM:** SQLAlchemy (Async) or SQLModel.

---

## 3. High-Level System Architecture

### 3.1 Architecture Diagram (Conceptual)

```mermaid
graph TD
    Client[Next.js Web App / PWA] -->|REST / Sync Queue| API_Gateway[FastAPI Server]
    Client -->|Google Maps SDK| Google_Maps_API[Google Maps API]
    
    subgraph Backend Services
        API_Gateway --> LLM_Pipeline[NLP Intent Engine]
        API_Gateway --> Ripple_Engine[Conflict & Ripple Engine]
        API_Gateway --> Scraper[Blog/URL Scraper]
        API_Gateway --> Background_Worker[Celery Worker]
    end
    
    LLM_Pipeline --> External_LLM[(OpenAI / Anthropic)]
    Ripple_Engine --> Google_Distance_Matrix[Google Routes/Distance Matrix]
    Background_Worker --> Weather_API[Weather APIs]
    
    Backend Services --> Primary_DB[(PostgreSQL + PostGIS)]
    Backend Services --> Cache[(Redis Cache)]
```

### 3.2 Core Components & Engines

#### 3.2.1 Offline-First Sync Layer
The frontend maintains a local replica of the active `Trip`. 
- **Reads:** Fetched from API and stored in IndexedDB.
- **Writes:** Mutate local IndexedDB instantly (Optimistic UI). Operations are added to a `Sync_Queue`.
- **Sync:** When online, the queue pushes operations to the backend for merging.

#### 3.2.2 LLM Intent Extraction Pipeline ("Quick Add" & "Chat Now")
- **Input:** Natural language string.
- **Process:** LLM parses text + current state into structured JSON patches.
- **Execution:** The Ripple Engine validates and applies the changes.

#### 3.2.3 The Ripple Engine
- Triggered by "Running Late" or LLM commands.
- Recursively shifts subsequent events while checking for hard constraints (e.g., closing times) and recalculating transit times.

#### 3.2.4 Timeline Map Split View
- Two independent React components communicating via shared state.
- **Scroll Sync:** Intersection Observer on the timeline triggers map panning/zooming to the active event's location.

---

## 4. Data Model (PostgreSQL Schema Draft)

- **Users:** `id`, `email`, `name`, `preferences`
- **Trips:** `id`, `name`, `start_date`, `end_date`, `created_by`
- **Trip_Members:** `trip_id`, `user_id`, `role`
- **Idea_Bin_Items:** `id`, `trip_id`, `title`, `place_id`, `lat`, `lng`, `url_source`
- **Events (Timeline):** 
  - `id`, `trip_id`, `title`, `place_id`, `lat`, `lng`, `start_time`, `end_time`, `is_locked`, `event_type`

---

## 5. Development Phases

### Phase 1: Core Foundation & Planning UI
1. **Scaffolding:** Initialize Next.js, Tailwind, FastAPI, and PostgreSQL.
2. **Auth & Setup:** User authentication and basic Trip CRUD.
3. **Idea Bin & Scraping:** Implement ingestion from text/URLs.
4. **Drag & Drop Timeline:** Build the split-pane UI and manual scheduling.
5. **Map Sync:** Integrate Google Maps and synchronize with the timeline.

### Phase 2: Intelligence & Adaptation
1. **Quick Add (NLP):** Build the LLM pipeline for sentence-to-event parsing.
2. **Ripple Engine:** Implement automatic timeboxing and conflict resolution.
3. **Offline Sync Queue:** Implement IndexedDB caching and optimistic updates.
4. **Chat Now:** Complex itinerary mutations via conversational AI.

### Phase 3: External Integrations
1. **Affiliate Links:** Handoffs to booking partners.
2. **Email Forwarding:** Background worker to parse confirmation emails.
3. **Proactive Alerts:** Weather-based and contextual "Vibe Check" prompts.

---

## 6. Recommendations & Next Steps
- **UI Prototyping:** Draft Figma flows for the Split-Pane view and Action Bar.
- **Proof of Concept:** Build a POC for the **Ripple Engine** logic in Python to validate transit-aware time-shifting.

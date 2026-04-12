# Roammate: Product Discovery & Brainstorm

## 1. Opportunity & Concept
**Product:** Roammate - Itinerary Planner and Visualiser
**Target Audience:** The meticulous planner, the spontaneous traveler, and group/family travelers.
**Core Value:** A living, breathing itinerary that transitions seamlessly from a "Travel Agent" planning phase to a real-time "Concierge" phase that adapts to changes on the go.

---

## 2. Phase 1 Scope (Core Experience)

**Focus:** Building a robust, adaptive itinerary system with manual and AI-assisted planning, interactive visualization, and real-time "Concierge" adaptation.

### Ideation from Three Perspectives

#### Product Manager Perspective (Focus: Market fit, value creation)
1.  **AI Itinerary Generation with Anchor Constraints:** Users input fixed "anchors" (e.g., flight arrival) and loose preferences ("want to see museums"). The AI builds the itinerary around these anchors.
2.  **Rapid "Idea Bin" Ingestion:** Users can paste a list of places (or URLs from travel blogs), and the app parses them into an unscheduled "Idea Bin" to be scheduled later.
3.  **Smart Timeboxing & Buffer Zones:** The app automatically calculates realistic travel times and buffer times between locations, warning if a day is physically impossible.
4.  **Collaborative "Multiplayer" Planning:** For families/groups, allow shared trips where members can propose changes and upvote/downvote activities.
5.  **Proactive Contextual Adaptation:** The app monitors external APIs (weather). If an outdoor activity is scheduled during rain, the app proactively pushes an alert offering indoor alternatives.

#### Product Designer Perspective (Focus: UX, onboarding, engagement)
1.  **Natural Language "Quick Add":** A single input field where a user types "Dinner at Gusto at 8pm tomorrow." The app parses the intent and creates the block instantly.
2.  **Split-Pane "Drag-from-Bin" UI:** A desktop/tablet view where the left pane is the daily timeline, and the right pane is the "Idea Bin". Users drag and drop places to build their day.
3.  **"Timeline Map" Split View:** Scrolling the vertical timeline of the day on one side automatically pans and zooms the map on the other side, highlighting the route.
4.  **One-Tap Concierge Action Bar:** A sticky action bar on the daily view featuring quick-actions: "Running Late", "Skip Next", "Find Coffee", and the "Chat Now" button.
5.  **"Vibe Check" Morning Prompt:** A micro-interaction asking "How energetic are we feeling today?" If "Low Energy," the app suggests replacing a strenuous hike with a cafe visit.

#### Software Engineer Perspective (Focus: Technical innovation, API integrations)
1.  **Google Places/Mapbox API Integration:** Robust autocomplete fetching photos, opening hours, and exact coordinates instantly to ensure accurate routing.
2.  **Conflict Resolution & Ripple Engine:** Automatically calculates time deltas and safely "ripples" (shifts) subsequent events when overlaps occur or a user is "Running late".
3.  **LLM Intent Extraction Pipeline:** A robust NLP pipeline to reliably parse "Chat Now" free-text inputs into structured JSON commands that mutate the database.
4.  **Graph-Based Routing Engine:** An algorithm that optimizes the order of a day's activities based on geographic clustering.
5.  **Offline-First Architecture:** A robust local-first database (IndexedDB/SQLite) ensuring the itinerary and map tiles are available offline, syncing Concierge changes when reconnected.

### Feature Breakdown by App Section

#### 1. Planning Section (The "Travel Agent" Phase)
*   **Fully AI-Assisted Generation:** Generates a structured day-by-day itinerary based on conversational prompts and fixed "anchors" (like flight times).
*   **Natural Language "Quick Add" (NLP):** Text-box input (e.g., "Colosseum tour tomorrow from 9 to 11") that instantly creates an event on the timeline.
*   **"Idea Bin" / Web Scraping:** Paste a comma-separated list or a travel blog URL. The app extracts locations, validates them via Places API, and adds them to an unscheduled sidebar for drag-and-drop scheduling.
*   **Traditional Manual Entry Form:** A structured modal (Title, Location autocomplete, Start/End Time, Notes) for highly specific or custom events.
*   **Collaborative Planning:** Real-time multi-user editing, upvoting, and shared idea bins.
*   **Smart Timeboxing:** Background calculation of transit times warning users of impossible schedules.

#### 2. Itinerary Visualisation Section
*   **"Timeline Map" Split View:** Dynamic UI syncing the chronological list with the spatial map route.
*   **Drag-and-Drop Timeline Blocks:** Visual blocks that can be easily rearranged, showing visual warnings (e.g., turning red) if dragged into an overlapping slot.

#### 3. Itinerary Interaction Section (The "Concierge" Phase)
*   **One-Tap Action Bar:** Quick UI buttons for common needs: "Running Late" (triggers the Ripple Engine), "Skip this", "Find nearby [coffee/food]".
*   **Conversational AI Chat ("Chat Now"):** Chat interface for complex changes (e.g., "Push everything back 2 hours", "Find a vegan place near the next stop").
*   **Proactive Alerts:** "Vibe Check" morning prompts and weather-based alternative suggestions.

### Top Prioritized Ideas for Phase 1 Validation
1.  **Real-Time Contextual Adaptation & "Ripple" Shifting:** The core differentiator for the Concierge phase.
2.  **Multi-Modal Data Entry (AI, NLP Quick Add, Idea Bin):** Lowers friction; crucial for user adoption.
3.  **Smart Timeboxing & Routing Warnings:** Solves the core problem for meticulous planners.
4.  **"Timeline Map" Split View:** Drives engagement and spatial understanding.
5.  **LLM Intent Extraction Pipeline:** Enables the powerful "Chat Now" functionality.

---

## 3. Phase 2 Scope (Booking & Advanced Integration)

**Focus:** Closing the loop from planning to purchasing, introducing direct or affiliate bookings, and deeper integration with user travel accounts.

### Ideation from Three Perspectives

#### Product Manager Perspective (Focus: Monetization, ecosystem)
1.  **Affiliate Handoff & Deep Linking:** Introduce "Check Availability" buttons for hotels, flights, and tours that link out to partners (Skyscanner, Booking.com, GetYourGuide) with affiliate tags.
2.  **Email Forwarding Integration:** Allow users to forward booking confirmation emails (like TripIt) to automatically populate the itinerary timeline with PNRs and exact times.
3.  **Dynamic Pricing Alerts:** Monitor saved but unbooked items in the "Idea Bin" and notify the user if ticket prices drop for their specific travel dates.

#### Product Designer Perspective (Focus: Trust, consolidated views)
1.  **Unified Booking Dashboard:** A secure "Wallet" view holding all ticket PDFs, QR codes, and booking reference numbers linked to specific timeline events.
2.  **AI "Booking Concierge" Chat:** Expand the chat UI to handle queries like "Find me a flight under $300 arriving before noon," presenting rich, bookable option cards.
3.  **Expense Tracking UI:** Visual breakdown of costs based on booked items vs. estimated costs for planned items.

#### Software Engineer Perspective (Focus: Security, external APIs)
1.  **Email Parsing Engine:** Securely parsing incoming, unstructured confirmation emails from hundreds of different airlines and hotels into structured timeline events.
2.  **Live Inventory API Integrations:** Connecting to GDS (Global Distribution Systems) or aggregator APIs (Amadeus, Skyscanner) to show real-time flight and hotel pricing.
3.  **End-to-End Encryption for Documents:** Ensuring user travel documents (passport copies, ticket PDFs) stored in the "Wallet" are securely encrypted.

### Feature Breakdown by App Section

#### 1. Planning Section
*   **AI Travel Querying:** Use AI to search and present live options for flights, cars, and accommodation directly within the planning flow.
*   **Email Forwarding:** Auto-populate the itinerary by forwarding confirmation emails.
*   **Dynamic Price Tracking:** Alerts for price drops on planned items.

#### 2. Itinerary Visualisation Section
*   **Booking "Wallet" Overlay:** Quick access to tickets/QR codes directly from the timeline event.
*   **Expense Dashboard:** Visual charts of trip spending.

#### 3. Itinerary Interaction Section (The "Concierge" Phase)
*   **In-Trip Booking:** Using the Concierge chat to book a last-minute activity or restaurant reservation (via OpenTable/Fork APIs).
*   **Disruption Management:** If the app detects a flight delay via external APIs, the Concierge automatically offers to adjust rental car pickup times and the first day's itinerary.

### Top Prioritized Ideas for Phase 2 Validation
1.  **Affiliate Handoff & Deep Linking:** The primary monetization engine.
2.  **Email Forwarding Integration:** Crucial for users who already have partially booked trips.
3.  **Unified Booking Dashboard (Wallet):** Keeps users in the app when they actually travel, rather than digging through their email inbox.
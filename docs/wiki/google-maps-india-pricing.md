# Google Maps Platform — India Pricing Reference

> **Source:** https://developers.google.com/maps/billing-and-pricing/india
> **Last updated on source:** 2026-05-08 UTC
> **Effective date:** March 1, 2025
> **Eligibility:** Customers with billing and a large majority of usage in India. Applied automatically.
> **Currency:** All prices in USD (CPM = Cost Per Thousand billable events). INR billing available.

---

## 1. Essentials / Pro / Enterprise — SKU Tier Classification (New APIs)

These are the **current (v2) APIs** organized by tier. You can mix and match across tiers. Bold names indicate SKU names updated on March 1, 2025.

### Maps

| Essentials | Pro | Enterprise |
|---|---|---|
| Dynamic Maps (India) | Dynamic Street View (India) | Map Tiles API: Photorealistic 3D Tiles (India) |
| **Embed** *(merged from Embed + Embed Advanced)* | Elevation (India) | |
| Map Tiles API: 2D Map Tiles (India) | **Aerial View (India)** *(was: End user views of Aerial View videos)* | |
| Map Tiles API: Street View Tiles (India) | | |
| **Maps SDK (India)** *(merged from Mobile Native Dynamic + Static Maps)* | | |
| Static Maps (India) | | |
| Static Street View (India) | | |
| Street View Metadata | | |

### Places

| Essentials | Pro | Enterprise |
|---|---|---|
| Autocomplete - Per Request (India) | **Address Validation Pro (India)** | **Address Validation Enterprise (India)** |
| Autocomplete (included with Places Details) - Per Session | Autocomplete without Places Details - Per Session (India) | Atmosphere Data (India) |
| Autocomplete Requests (India) | Find Current Place (India) | Contact Data (India) |
| Autocomplete Session Usage (India) | Find Place (India) | **Places API Nearby Search Enterprise (India)** |
| Basic Data (India) | Places - Nearby Search (India) | **Places API Nearby Search Enterprise + Atmosphere (India)** |
| Find Place - ID only (India) | Places - Text Search (India) | **Places API Place Details Enterprise (India)** |
| Geocoding (India) | **Places API Nearby Search Pro (India)** | **Places API Place Details Enterprise + Atmosphere (India)** |
| Geolocation (India) | **Places API Place Details Pro (India)** | **Places API Place Details Photos (India)** |
| **Places API Place Details Essentials (IDs Only) (India)** | **Places API Text Search Pro (India)** | **Places API Text Search Enterprise (India)** |
| **Places API Place Details Essentials (India)** | Places Details (India) | **Places API Text Search Enterprise + Atmosphere (India)** |
| **Places API Text Search Essentials (IDs Only) (India)** | | Places Photo (India) |
| Places Details - ID Refresh (India) | | |
| Query Autocomplete - Per Request (India) | | |
| Time Zone (India) | | |
| Maps Grounding Lite (India) | | |

### Routes

| Essentials | Pro | Enterprise |
|---|---|---|
| Directions (India) | Directions Advanced (India) | Navigation Request (India) |
| Distance Matrix (India) | Distance Matrix Advanced (India) | RouteOptimization - FleetRouting (India) |
| **Routes: Compute Route Matrix Essentials (India)** | Roads - Nearest Road (India) | **Routes: Compute Route Matrix Enterprise (India)** |
| **Routes: Compute Routes Essentials (India)** | Roads - Route Traveled (India) | **Routes: Compute Routes Enterprise (India)** |
| | RouteOptimization - SingleVehicleRouting (India) | |
| | **Routes: Compute Route Matrix Pro (India)** | |
| | **Routes: Compute Routes Pro (India)** | |

### Environment

| Essentials | Pro | Enterprise |
|---|---|---|
| Air Quality Usage (India) | Pollen Usage (India) | Solar API Data Layers (India) |
| Solar API Building Insights (India) | | |

---

## 2. Free Monthly Billable Events

The USD $200 monthly recurring credit was replaced with free monthly usage thresholds per SKU, effective March 1, 2025.

| Tier | Free Monthly Billable Events |
|---|---|
| **Essentials** | **70,000** |
| **Pro** | **35,000** |
| **Enterprise** | **7,000** |

**Exception:** Map Tiles API: 2D Map Tiles (India) and Map Tiles API: Street View Tiles (India) have **700,000** free monthly billable events.

---

## 3. India Pricing Sheet — New SKUs (Effective March 1, 2025)

All prices are **Cost Per Thousand (CPM) billable events in USD**.

### Maps

| SKU Name (effective March 1, 2025) | Category | Free Threshold | Next → 5,000,000 | 5,000,000+ |
|---|---|---|---|---|
| Dynamic Maps (India) | Essentials | 70,000 | $2.10 | $0.53 |
| Embed | Essentials | — | $0.00 | $0.00 |
| Maps SDK (India) | Essentials | — | $0.00 | $0.00 |
| Static Maps (India) | Essentials | 70,000 | $0.60 | $0.15 |
| Static Street View (India) | Essentials | 70,000 | $2.10 | $0.53 |
| Street View Metadata | Essentials | — | $0.00 | $0.00 |
| Dynamic Street View (India) | Pro | 35,000 | $4.20 | $1.05 |
| Elevation (India) | Pro | 35,000 | $1.50 | $0.38 |
| Aerial View (India) | Pro | 35,000 | $4.80 | $1.20 |

### Maps — Tiles

> **Note:** 2D and Street View Tiles have a higher free threshold (700,000) and a higher volume discount tier (50,000,000+).

| SKU Name (effective March 1, 2025) | Category | Free Threshold | Next → Volume Cap | Volume Cap+ |
|---|---|---|---|---|
| Map Tiles API: 2D Map Tiles (India) | Essentials | 700,000 | $0.18 *(700,001 → 50M)* | $0.045 *(50M+)* |
| Map Tiles API: Street View Tiles (India) | Essentials | 700,000 | $0.60 *(700,001 → 50M)* | $0.20 *(50M+)* |
| Map Tiles API: Photorealistic 3D Tiles (India) | Enterprise | 7,000 | $3.30 *(7,001 → 5M)* | $2.40 *(5M+)* |

### Places

| SKU Name (effective March 1, 2025) | Category | Free Threshold | Next → 5,000,000 | 5,000,000+ |
|---|---|---|---|---|
| Autocomplete Requests (India) | Essentials | 70,000 | $0.85 | $0.21 |
| Autocomplete Session Usage (India) | Essentials | — | $0.00 | $0.00 |
| Geocoding (India) | Essentials | 70,000 | $1.50 | $0.38 |
| Geolocation (India) | Essentials | 70,000 | $1.50 | $0.38 |
| Time Zone (India) | Essentials | 70,000 | $1.50 | $0.38 |
| Maps Grounding Lite (India) | Essentials | 70,000 | $3.85 ¹ | $2.80 |
| Places API Place Details Essentials (IDs Only) (India) | Essentials | — | $0.00 | $0.00 |
| Places API Place Details Essentials (India) | Essentials | 70,000 | $1.50 | $0.38 |
| Places API Text Search Essentials (IDs Only) (India) | Essentials | — | $0.00 | $0.00 |
| Address Validation Pro (India) | Pro | 35,000 | $5.10 | $1.28 |
| **Places API Nearby Search Pro (India)** | **Pro** | **35,000** | **$9.60** | **$2.40** |
| Places API Place Details Pro (India) | Pro | 35,000 | $5.10 | $1.28 |
| **Places API Text Search Pro (India)** | **Pro** | **35,000** | **$9.60** | **$2.40** |
| Address Validation Enterprise (India) | Enterprise | 7,000 | $7.50 | $2.28 |
| **Places API Nearby Search Enterprise (India)** | **Enterprise** | **7,000** | **$10.50** | **$2.63** |
| **Places API Nearby Search Enterprise + Atmosphere (India)** | **Enterprise** | **7,000** | **$12.00** | **$3.40** |
| Places API Place Details Enterprise (India) | Enterprise | 7,000 | $6.00 | $1.51 |
| **Places API Place Details Enterprise + Atmosphere (India)** | **Enterprise** | **7,000** | **$7.50** | **$2.28** |
| Places API Place Details Photos (India) | Enterprise | 7,000 | $2.10 | $0.53 |
| **Places API Text Search Enterprise (India)** | **Enterprise** | **7,000** | **$10.50** | **$2.63** |
| **Places API Text Search Enterprise + Atmosphere (India)** | **Enterprise** | **7,000** | **$12.00** | **$3.40** |

> ¹ Maps Grounding Lite: Contact sales for volume pricing.

### Environment

| SKU Name (effective March 1, 2025) | Category | Free Threshold | Next → 5,000,000 | 5,000,000+ |
|---|---|---|---|---|
| Air Quality Usage (India) | Essentials | 70,000 | $0.50 | $0.25 |
| Solar API Building Insights (India) | Essentials | 70,000 | $4.00 | $3.50 |
| Pollen Usage (India) | Pro | 35,000 | $1.00 | $0.50 |
| Solar API Data Layers (India) | Enterprise | 7,000 | $30.00 | $26.25 |

### Routes

| SKU Name (effective March 1, 2025) | Category | Free Threshold | Next → 5,000,000 | 5,000,000+ |
|---|---|---|---|---|
| Routes: Compute Route Matrix Essentials (India) | Essentials | 70,000 | $1.50 | $0.38 |
| Routes: Compute Routes Essentials (India) | Essentials | 70,000 | $1.50 | $0.38 |
| Roads - Nearest Road (India) | Pro | 35,000 | $3.00 | $0.76 |
| Roads - Route Traveled (India) | Pro | 35,000 | $3.00 | $0.76 |
| RouteOptimization - SingleVehicleRouting (India) | Pro | 35,000 | $0.80 | $0.70 |
| Routes: Compute Route Matrix Pro (India) | Pro | 35,000 | $3.00 | $0.75 |
| Routes: Compute Routes Pro (India) | Pro | 35,000 | $3.00 | $0.75 |
| RouteOptimization - FleetRouting (India) | Enterprise | 7,000 | $2.40 | $2.10 |
| Routes: Compute Route Matrix Enterprise (India) | Enterprise | 7,000 | $4.50 | $1.14 |
| Routes: Compute Routes Enterprise (India) | Enterprise | 7,000 | $4.50 | $1.14 |
| Navigation Request (India) | Enterprise | 7,000 | $28.00 *(7,001+, flat)* | — |

---

## 4. India Pricing Sheet — Legacy SKUs (Effective March 1, 2025)

> **Note:** As of March 1, 2025, Legacy services (Places API, Directions API, Distance Matrix API) can no longer be newly enabled. Existing users may continue using them. Migration to Places API (New) and Routes API is encouraged.

### Places (Legacy)

| SKU Name (effective March 1, 2025) | Category | Free Threshold | Next → 5,000,000 | 5,000,000+ |
|---|---|---|---|---|
| Autocomplete - Per Request (India) | Essentials | 70,000 | $0.85 | $0.21 |
| Autocomplete (included with Places Details) - Per Session ¹ | Essentials | — | $0.00 | $0.00 |
| Basic Data (India) | Essentials | — | $0.00 | $0.00 |
| Find Place - ID only (India) | Essentials | — | $0.00 | $0.00 |
| Places Details - ID Refresh (India) | Essentials | — | $0.00 | $0.00 |
| Query Autocomplete - Per Request (India) | Essentials | 70,000 | $0.85 | $0.21 |
| Autocomplete without Places Details - Per Session (India) | Pro | 35,000 | $5.10 | $1.28 |
| Find Current Place (India) | Pro | 35,000 | $9.00 | $2.25 |
| Find Place (India) | Pro | 35,000 | $5.10 | $1.28 |
| **Places - Nearby Search (India)** | **Pro** | **35,000** | **$9.60** | **$2.40** |
| **Places - Text Search (India)** | **Pro** | **35,000** | **$9.60** | **$2.40** |
| Places Details (India) | Pro | 35,000 | $5.10 | $1.28 |
| Atmosphere Data (India) | Enterprise | 7,000 | $1.50 | $0.77 |
| Contact Data (India) | Enterprise | 7,000 | $0.90 | $0.23 |
| Places Photo (India) | Enterprise | 7,000 | $2.10 | $0.53 |

> ¹ Autocomplete request is free; subsequent Places Details calls are charged at regular Places Details (India) pricing.

### Routes (Legacy)

| SKU Name (effective March 1, 2025) | Category | Free Threshold | Next → 5,000,000 | 5,000,000+ |
|---|---|---|---|---|
| Directions (India) | Essentials | 70,000 | $1.50 | $0.38 |
| Distance Matrix (India) | Essentials | 70,000 | $1.50 | $0.38 |
| Directions Advanced (India) | Pro | 35,000 | $3.00 | $0.75 |
| Distance Matrix Advanced (India) | Pro | 35,000 | $3.00 | $0.75 |

---

## Quick Reference — Roammate App Usage

The APIs Roammate currently uses and their tier/cost implications:

| What we use | SKU triggered | Tier | Free/month | CPM (paid) |
|---|---|---|---|---|
| Directions API (legacy v1) | Directions (India) | Essentials | 70,000 | $1.50 |
| Routes: Compute Routes (v2) | Routes: Compute Routes Essentials (India) | Essentials | 70,000 | $1.50 |
| Places Text Search (v2, Pro fields) | Places API Text Search Pro (India) | Pro | 35,000 | $9.60 |
| Places Text Search (v2, Enterprise fields like `editorialSummary`) | Places API Text Search Enterprise + Atmosphere (India) | Enterprise | 7,000 | $12.00 |
| Places Nearby Search (v2, Pro fields) | Places API Nearby Search Pro (India) | Pro | 35,000 | $9.60 |
| Places Nearby Search (v2, Enterprise fields like `editorialSummary`) | Places API Nearby Search Enterprise + Atmosphere (India) | Enterprise | 7,000 | $12.00 |
| Places Place Details (v2, Pro fields) | Places API Place Details Pro (India) | Pro | 35,000 | $5.10 |
| Places Place Details (v2, Enterprise fields) | Places API Place Details Enterprise + Atmosphere (India) | Enterprise | 7,000 | $7.50 |
| Places Photos (v2) | Places API Place Details Photos (India) | Enterprise | 7,000 | $2.10 |
| Geocoding | Geocoding (India) | Essentials | 70,000 | $1.50 |
| Nearby Search (legacy v1) | Places - Nearby Search (India) | Pro | 35,000 | $9.60 |
| Text Search (legacy v1) | Places - Text Search (India) | Pro | 35,000 | $9.60 |

> **Key insight for `editorialSummary`:** Requesting `places.editorialSummary` in v2 field masks escalates the SKU from **Pro ($9.60 CPM)** to **Enterprise + Atmosphere ($12.00 CPM)** — a 25% cost increase and the free threshold drops from 35,000 to 7,000. Consider gating behind a config flag.

---

## 6. Roammate API Calls — Field-Level Tier Breakdown

This section documents exactly which APIs and fields Roammate calls, what tier each field belongs to, and what ultimately determines the billed SKU for each call. The billing rule is: **you are billed at the highest-tier field in your request**.

> **Source:** [SKU Details](https://developers.google.com/maps/billing-and-pricing/sku-details)

### 6.1 Places API (New / v2) — Field-to-Tier Mapping

For Place Details, Text Search, and Nearby Search (all New/v2), the tier is determined by the `X-Goog-FieldMask` header. The tables below show only the **Web service** field names (prefixed with `places.` for search endpoints).

#### Essentials Fields (Place Details only — $1.50 CPM India, 70K free)

> Essentials fields don't apply to Text Search or Nearby Search. Using *any* Text/Nearby Search field automatically starts at Pro.

| Field | Description | We use? |
|---|---|---|
| `addressComponents` | Structured address components | No |
| `addressDescriptor` | Address descriptors (GA in India) | No |
| `adrFormatAddress` | Address in adr microformat | No |
| `formattedAddress` | Full human-readable address | **Yes** |
| `location` | Lat/lng coordinates | **Yes** |
| `plusCode` | Plus Code | No |
| `postalAddress` | Structured postal address | No |
| `shortFormattedAddress` | Short address | No |
| `types` | Place type tags | **Yes** |
| `viewport` | Recommended viewport | No |

#### Pro Fields ($5.10–$9.60 CPM India, 35K free)

These fields trigger Pro billing for Place Details ($5.10 CPM), Text Search ($9.60 CPM), and Nearby Search ($9.60 CPM).

| Field | Description | We use? |
|---|---|---|
| `accessibilityOptions` | Wheelchair accessible entrance | No |
| `addressComponents` | *(Text/Nearby only — Essentials for Details)* | No |
| `adrFormatAddress` | *(Text/Nearby only — Essentials for Details)* | No |
| `attributions` | *(Nearby only)* | No |
| `businessStatus` | OPERATIONAL, CLOSED, etc. | No |
| `containingPlaces` | Parent places | No |
| `displayName` | Human-readable place name | **Yes** |
| `formattedAddress` | *(Text/Nearby only — Essentials for Details)* | **Yes** |
| `googleMapsLinks` | Links to Google Maps | No |
| `googleMapsUri` | Google Maps URL | No |
| `iconBackgroundColor` | Icon background color hex | No |
| `iconMaskBaseUri` | Icon mask URI | No |
| `id` | Place ID *(always returned; Pro trigger for Text/Nearby only — no tier impact for Details)* | **Yes** |
| `location` | *(Text/Nearby only — Essentials for Details)* | **Yes** |
| `movedPlace` / `movedPlaceId` | *(Nearby only)* | No |
| `name` | Resource name (`places/PLACE_ID`) | No |
| `openingDate` | Date place opened | No |
| `photos` | Photo metadata (fetching the actual photo triggers Enterprise: Place Details Photos) | **Yes** (if `FETCH_PHOTOS=True`) |
| `plusCode` | *(Text/Nearby only — Essentials for Details)* | No |
| `postalAddress` | *(Text/Nearby only — Essentials for Details)* | No |
| `primaryType` | Primary place type | No |
| `primaryTypeDisplayName` | Display name of primary type | No |
| `pureServiceAreaBusiness` | Service area flag | No |
| `searchUri` | *(Text Search only)* | No |
| `shortFormattedAddress` | *(Text/Nearby only — Essentials for Details)* | No |
| `subDestinations` | Sub-destinations within place | No |
| `timeZone` | *(Nearby only as Pro; Details is Pro)* | No |
| `types` | *(Text/Nearby only — Essentials for Details)* | **Yes** |
| `utcOffsetMinutes` | UTC offset | No |
| `viewport` | *(Text/Nearby only — Essentials for Details)* | No |

#### Enterprise Fields ($6.00–$10.50 CPM India, 7K free)

These fields trigger Enterprise billing.

| Field | Description | We use? |
|---|---|---|
| `currentOpeningHours` | Opening hours for the next 7 days | No |
| `currentSecondaryOpeningHours` | Secondary opening hours | No |
| `internationalPhoneNumber` | Phone number (international) | No |
| `nationalPhoneNumber` | Phone number (national) | No |
| `priceLevel` | Price level enum (FREE → VERY_EXPENSIVE) | **Yes** (if `FETCH_RATING=True`) |
| `priceRange` | Price range | No |
| `rating` | Aggregate rating (1.0–5.0) | **Yes** (if `FETCH_RATING=True`) |
| `regularOpeningHours` | Standard weekly opening hours | No |
| `regularSecondaryOpeningHours` | Secondary standard hours | No |
| `userRatingCount` | Total number of ratings | No |
| `websiteUri` | Website URL | No |

#### Enterprise + Atmosphere Fields ($7.50–$12.00 CPM India, 7K free)

These fields trigger the highest-cost SKU. **Any single field from this list escalates the entire request.**

| Field | Description | We use? |
|---|---|---|
| `allowsDogs` | Dogs allowed | No |
| `curbsidePickup` | Curbside pickup available | No |
| `delivery` | Delivery available | No |
| `dineIn` | Dine-in available | No |
| **`editorialSummary`** | **Google's editorial description** | No |
| `evChargeAmenitySummary` | EV charging summary | No |
| `evChargeOptions` | EV charge options | No |
| `fuelOptions` | Fuel options | No |
| `generativeSummary` | AI-generated summary | No |
| `goodForChildren` | Good for children | No |
| `goodForGroups` | Good for groups | No |
| `goodForWatchingSports` | Sports viewing | No |
| `liveMusic` | Live music available | No |
| `menuForChildren` | Children's menu | No |
| `neighborhoodSummary` | Neighborhood description | No |
| `outdoorSeating` | Outdoor seating | No |
| `parkingOptions` | Parking details | No |
| `paymentOptions` | Payment methods | No |
| `reservable` | Reservations available | No |
| `restroom` | Restroom available | No |
| `reviews` | User reviews | No |
| `reviewSummary` | Review summary | No |
| `routingSummaries` | *(Text/Nearby only)* Routing summaries | No |
| `servesBeer/Breakfast/Brunch/...` | Various food/drink service flags | No |
| `takeout` | Takeout available | No |

#### Place Photos (separate Enterprise SKU — $2.10 CPM India, 7K free)

Fetching the actual photo binary via `GET /v1/{photo_name}/media` triggers `Places API Place Details Photos` — a separate Enterprise SKU, regardless of which field-mask tier your search/details call used.

---

### 6.2 Routes API (v2) — Feature-to-Tier Mapping

Unlike Places, Routes tier is determined by **features/parameters used in the request**, not by field masks.

| Tier | Trigger Conditions | India CPM |
|---|---|---|
| **Essentials** | Basic request: origin → destination, ≤10 intermediate waypoints, no traffic routing, no toll/polyline traffic | $1.50 |
| **Pro** | Any of: 11–25 intermediate waypoints, `optimizeWaypointOrder: true`, `routingPreference: TRAFFIC_AWARE` or `TRAFFIC_AWARE_OPTIMAL`, location modifiers (side of road, heading, vehicle stopover) | $3.00 |
| **Enterprise** | Any of: Two-wheeled vehicle routing, toll calculation, traffic info on polylines | $4.50 |

---

### 6.3 What Roammate V1 (Legacy) Calls — Tier Analysis

**Config:** `GOOGLE_MAPS_API_VERSION = "v1"` (legacy APIs)

#### Legacy Find Place API

| What we request | Legacy fields param | Tier triggered |
|---|---|---|
| `find_place()` | `place_id,name,geometry,formatted_address` | **Pro** — Find Place (India) |

> **Why Pro?** The legacy Find Place API itself is a **Pro SKU** ($5.10 CPM, 35K free). Unlike the new API, the legacy Find Place doesn't have Essentials/Pro/Enterprise field-level tiers — **any call to Find Place triggers the Pro SKU**, plus any additional data SKUs based on fields returned.

#### Legacy Place Details API

| What we request | Legacy fields param | Data SKU triggered | Base SKU |
|---|---|---|---|
| Always | `place_id,name,geometry,formatted_address,types` | Basic Data (Essentials, $0.00) | Places Details (Pro, $5.10 CPM) |
| If `FETCH_RATING=True` | `+ rating,price_level` | Basic Data ($0.00) — rating/price_level are Basic Data fields in legacy | Places Details (Pro, $5.10 CPM) |
| If `FETCH_PHOTOS=True` | `+ photos` | Basic Data ($0.00) — photo metadata is Basic Data in legacy; but **fetching the actual photo** triggers Enterprise: Places Photo ($2.10 CPM) | Places Details (Pro, $5.10 CPM) |

> **Legacy Place Details billing model:** Every call triggers the base `Places Details (India)` SKU (Pro, $5.10 CPM). On top of that, data-type SKUs are billed at $0 for Basic Data fields. `rating` and `price_level` are **Basic Data** in legacy (unlike v2 where they are Enterprise). Photos metadata is also Basic Data, but the photo fetch itself is a separate Enterprise SKU.

#### Legacy Directions API

**What Roammate sends (request params):**

```
origin:       place_id:{place_id} or lat,lng
destination:  place_id:{place_id} or lat,lng
waypoints:    pipe-delimited list of intermediates (only when >2 points)
mode:         driving
key:          API_KEY
```

**No advanced features used** — no `departure_time`, no `waypoints=optimize:true`, no `side_of_road`, no `heading`.

**What Roammate reads from the response:**

| Response field read | Object path | Description |
|---|---|---|
| `overview_polyline.points` | `routes[0].overview_polyline.points` | Encoded polyline for map rendering |
| `legs[].distance.value` | `routes[0].legs[i].distance.value` | Distance in meters per leg |
| `legs[].duration.value` | `routes[0].legs[i].duration.value` | Duration in seconds per leg (no traffic) |

**All available response fields in legacy Directions API:**

| Field | Level | Description | We use? |
|---|---|---|---|
| `routes[].bounds` | Route | Viewport bounding box | No |
| `routes[].copyrights` | Route | Copyright text | No |
| `routes[].legs` | Route | Array of legs (one per waypoint pair) | **Yes** |
| `routes[].overview_polyline` | Route | Encoded polyline for the full route | **Yes** |
| `routes[].summary` | Route | Short text description of route | No |
| `routes[].warnings` | Route | Warning messages | No |
| `routes[].waypoint_order` | Route | Optimized waypoint order (only with `optimize:true`) | No |
| `routes[].fare` | Route | Transit fare (transit only) | No |
| `legs[].end_address` | Leg | Reverse-geocoded end address | No |
| `legs[].end_location` | Leg | End lat/lng | No |
| `legs[].start_address` | Leg | Reverse-geocoded start address | No |
| `legs[].start_location` | Leg | Start lat/lng | No |
| `legs[].steps` | Leg | Turn-by-turn navigation steps | No |
| `legs[].distance` | Leg | Total leg distance (`text` + `value`) | **Yes** (`.value` only) |
| `legs[].duration` | Leg | Total leg duration (`text` + `value`) | **Yes** (`.value` only) |
| `legs[].duration_in_traffic` | Leg | Traffic-aware duration (requires `departure_time`) | No |
| `legs[].arrival_time` | Leg | Transit arrival time | No |
| `legs[].departure_time` | Leg | Transit departure time | No |
| `legs[].traffic_speed_entry` | Leg | Traffic speed entries | No |
| `legs[].via_waypoint` | Leg | Via waypoint info | No |

**Tier determination — what triggers Pro (Advanced):**

| Feature | Triggers Pro? | Roammate uses? |
|---|---|---|
| `duration_in_traffic` (requires `departure_time`) | **Yes** | No |
| 11–25 waypoints | **Yes** | No (we call per-pair in Smart Ripple, 2 points per call) |
| `waypoints=optimize:true` | **Yes** | No |
| Location modifier: `side_of_road` | **Yes** | No |
| Location modifier: `heading` | **Yes** | No |

**Billed SKU:** `Directions (India)` — **Essentials, $1.50 CPM, 70K free**

> We use none of the Pro triggers. Basic driving directions with ≤10 waypoints and no traffic-aware duration = Essentials tier.

#### Legacy Nearby Search / Text Search

| What we request | SKU triggered | Tier | CPM |
|---|---|---|---|
| `nearby_search()` with `USE_NEARBY_API=True` | Places - Nearby Search (India) | Pro | $9.60 |
| `nearby_search()` with `USE_NEARBY_API=False` (default, Text Search) | Places - Text Search (India) | Pro | $9.60 |

> Both legacy search APIs are flat **Pro** SKUs. No field-level tiering — any call is Pro.

#### Legacy Photo Fetch

| What we request | SKU triggered | Tier | CPM |
|---|---|---|---|
| `photo_url()` (fetches photo binary) | Places Photo (India) | Enterprise | $2.10 |

---

### 6.4 What Roammate V2 (New API) Calls — Tier Analysis

**Config:** `GOOGLE_MAPS_API_VERSION = "v2"` (new APIs)

#### V2 Text Search (used as `find_place()`)

**Current field mask:**
```
places.id, places.displayName, places.formattedAddress, places.location, places.types
```

| Field | Tier |
|---|---|
| `places.id` | Pro |
| `places.displayName` | Pro |
| `places.formattedAddress` | Pro |
| `places.location` | Pro |
| `places.types` | Pro |

**Billed SKU:** `Places API Text Search Pro (India)` — **Pro, $9.60 CPM, 35K free**

#### V2 Place Details

**Current field mask (base):**
```
id, displayName, formattedAddress, location, types
```

**With `FETCH_RATING=True`:**
```
+ rating, priceLevel
```

**With `FETCH_PHOTOS=True`:**
```
+ photos
```

| Field | Tier |
|---|---|
| `id` | n/a (always returned) |
| `displayName` | Pro |
| `formattedAddress` | Essentials |
| `location` | Essentials |
| `types` | Essentials |
| **`rating`** | **Enterprise** |
| **`priceLevel`** | **Enterprise** |
| `photos` | Pro (metadata only; fetching photo binary = separate Enterprise SKU) |

**Billed SKU (with rating/priceLevel):** `Places API Place Details Enterprise (India)` — **Enterprise, $6.00 CPM, 7K free**

> **Key difference from V1:** In legacy, `rating` and `price_level` are Basic Data ($0.00 add-on). In v2, `rating` and `priceLevel` are **Enterprise fields** ($6.00 CPM). This is a significant cost escalation when using v2 with `FETCH_RATING=True`.

#### V2 Nearby Search

**Current field mask (base):**
```
places.id, places.displayName, places.formattedAddress, places.location, places.types
```

**With `FETCH_RATING=True`:**
```
+ places.rating, places.priceLevel
```

**With `FETCH_PHOTOS=True`:**
```
+ places.photos
```

| Field | Tier in Nearby Search |
|---|---|
| `places.id` | Pro |
| `places.displayName` | Pro |
| `places.formattedAddress` | Pro |
| `places.location` | Pro |
| `places.types` | Pro |
| **`places.rating`** | **Enterprise** |
| **`places.priceLevel`** | **Enterprise** |
| `places.photos` | Pro (metadata); fetching photo = Enterprise Photos SKU |

**Billed SKU (with rating/priceLevel):** `Places API Nearby Search Enterprise (India)` — **Enterprise, $10.50 CPM, 7K free**

**Billed SKU (without rating/priceLevel):** `Places API Nearby Search Pro (India)` — **Pro, $9.60 CPM, 35K free**

#### V2 Compute Routes

**What Roammate sends (request body):**

```json
{
  "origin":      { "placeId": "..." } or { "location": { "latLng": { "latitude": ..., "longitude": ... } } },
  "destination": { "placeId": "..." } or { "location": { "latLng": { ... } } },
  "intermediates": [ ... ],       // only when >2 waypoints
  "travelMode": "DRIVE",
  "polylineEncoding": "ENCODED_POLYLINE"
}
```

**No advanced features used** — no `routingPreference`, no `optimizeWaypointOrder`, no location modifiers, no toll calculation, no `TWO_WHEELER` travel mode.

**Current field mask (X-Goog-FieldMask):**

```
routes.duration, routes.distanceMeters, routes.polyline.encodedPolyline,
routes.legs.duration, routes.legs.distanceMeters
```

**What Roammate reads from the response:**

| Response field read | Object path | Description |
|---|---|---|
| `polyline.encodedPolyline` | `routes[0].polyline.encodedPolyline` | Encoded polyline for map rendering |
| `legs[].distanceMeters` | `routes[0].legs[i].distanceMeters` | Distance in meters per leg |
| `legs[].duration` | `routes[0].legs[i].duration` | Duration string (e.g. `"165s"`) per leg |
| `distanceMeters` | `routes[0].distanceMeters` | Total route distance (fallback if no legs) |
| `duration` | `routes[0].duration` | Total route duration (fallback if no legs) |

**All available response fields (field mask options):**

| Field mask path | Level | Description | Tier | We use? |
|---|---|---|---|---|
| `routes.routeLabels` | Route | Labels (DEFAULT_ROUTE, FUEL_EFFICIENT) | Essentials | No |
| `routes.legs` | Route | Array of legs | Essentials | **Yes** |
| `routes.distanceMeters` | Route | Total distance in meters | Essentials | **Yes** |
| `routes.duration` | Route | Total duration string | Essentials | **Yes** |
| `routes.staticDuration` | Route | Duration without traffic | Essentials | No |
| `routes.polyline` | Route | Route polyline | Essentials | **Yes** |
| `routes.description` | Route | Text description of route | Essentials | No |
| `routes.warnings` | Route | Warning messages | Essentials | No |
| `routes.viewport` | Route | Viewport bounding box | Essentials | No |
| `routes.localizedValues` | Route | Localized distance/duration text | Essentials | No |
| `routes.optimizedIntermediateWaypointIndex` | Route | Optimized order (needs `optimizeWaypointOrder`) | **Pro** | No |
| `routes.routeToken` | Route | Opaque token for Navigation SDK | Essentials | No |
| `routes.legs.distanceMeters` | Leg | Leg distance in meters | Essentials | **Yes** |
| `routes.legs.duration` | Leg | Leg duration string | Essentials | **Yes** |
| `routes.legs.staticDuration` | Leg | Leg duration without traffic | Essentials | No |
| `routes.legs.polyline` | Leg | Leg polyline | Essentials | No |
| `routes.legs.startLocation` | Leg | Leg start lat/lng | Essentials | No |
| `routes.legs.endLocation` | Leg | Leg end lat/lng | Essentials | No |
| `routes.legs.steps` | Leg | Turn-by-turn steps | Essentials | No |
| `routes.legs.localizedValues` | Leg | Localized text | Essentials | No |
| `routes.legs.stepsOverview` | Leg | Multi-modal step overview | Essentials | No |
| `routes.legs.travelAdvisory` | Leg | Speed-reading segments, toll info | Essentials* | No |
| `routes.travelAdvisory` | Route | Route-level travel advisory | Essentials* | No |
| `routes.travelAdvisory.tollInfo` | Route | Toll information | **Enterprise** | No |
| `routes.polylineDetails` | Route | Flyover/narrow road details on polyline | Essentials | No |
| `geocodingResults` | Top | Geocoding info for waypoints | Essentials | No |

> *`travelAdvisory` itself is Essentials, but requesting `tollInfo` within it triggers Enterprise.

**Tier determination — what triggers Pro:**

| Feature / Request Parameter | Triggers Pro? | Roammate uses? |
|---|---|---|
| 11–25 intermediate waypoints | **Yes** | No (we call per-pair, 2 points per call) |
| `optimizeWaypointOrder: true` | **Yes** | No |
| `routingPreference: TRAFFIC_AWARE` | **Yes** | No |
| `routingPreference: TRAFFIC_AWARE_OPTIMAL` | **Yes** | No |
| Location modifier: `sideOfRoad` | **Yes** | No |
| Location modifier: `heading` | **Yes** | No |
| Location modifier: `vehicleStopover` | **Yes** | No |

**Tier determination — what triggers Enterprise:**

| Feature / Request Parameter | Triggers Enterprise? | Roammate uses? |
|---|---|---|
| `travelMode: TWO_WHEELER` | **Yes** | No |
| Toll calculation (`extraComputations: TOLLS`) | **Yes** | No |
| Traffic info on polylines (`extraComputations: TRAFFIC_ON_POLYLINE`) | **Yes** | No |

**Billed SKU:** `Routes: Compute Routes Essentials (India)` — **Essentials, $1.50 CPM, 70K free**

> We use none of the Pro or Enterprise triggers. Basic origin/destination DRIVE routing with an encoded polyline and per-leg distance/duration = Essentials tier.

#### V2 Photo Fetch

| What we request | SKU triggered | Tier | CPM |
|---|---|---|---|
| `GET /v1/{photo_name}/media` | Places API Place Details Photos (India) | Enterprise | $2.10 |

---

### 6.5 Cost Comparison Summary — V1 vs V2

| API Call | V1 (Legacy) SKU | V1 CPM | V2 (New) SKU | V2 CPM | Winner |
|---|---|---|---|---|---|
| Find Place / Text Search | Find Place (Pro) | $5.10 | Text Search Pro | $9.60 | **V1** (47% cheaper) |
| Place Details (base) | Places Details (Pro) | $5.10 | Place Details Pro | $5.10 | Tie |
| Place Details (with rating) | Places Details (Pro) + Basic Data ($0) | $5.10 | Place Details Enterprise | $6.00 | **V1** (15% cheaper) |
| Nearby/Text Search | Nearby/Text Search (Pro) | $9.60 | Nearby/Text Search Pro | $9.60 | Tie |
| Nearby Search (with rating) | Nearby Search (Pro) | $9.60 | Nearby Search Enterprise | $10.50 | **V1** (9% cheaper) |
| Directions | Directions (Essentials) | $1.50 | Compute Routes Essentials | $1.50 | Tie |
| Photo fetch | Places Photo (Enterprise) | $2.10 | Place Details Photos (Enterprise) | $2.10 | Tie |

> **Bottom line:** V1 (legacy) is cheaper for Roammate's current usage profile because `rating` and `priceLevel` are free add-on data in legacy but Enterprise-tier fields in v2. The only reason to prefer v2 is future-proofing — Google will eventually deprecate legacy APIs.

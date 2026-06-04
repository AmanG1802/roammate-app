# [39] OpenAPI 3.0 Spec-First Backend

## Context

Roammate's FastAPI backend has 17 endpoint modules (~80+ routes) with no committed API spec. The goal is **Spec → Code** development going forward. Since no spec exists yet, the immediate work is to write the OpenAPI 3.0 YAML manually based on today's existing APIs, then set up tooling so future development starts from the spec — not the other way around.

---

## Phase 1: Write the OpenAPI 3.0 YAML Spec (Immediate deliverable)

Manually author `docs/api/openapi.yaml` that fully describes all existing endpoints.

### Spec top-level structure

```yaml
openapi: 3.0.3
info:
  title: Roammate API
  version: "1.0.0"
  description: |
    Travel itinerary planner API.
    
    ## Authentication
    All protected endpoints accept credentials via two transports:
    - **Web**: HttpOnly cookie `rm_access` set on login/verify/refresh.
    - **iOS**: `Authorization: Bearer <jwt>` header. Login response body includes `access_token` for Keychain.

servers:
  - url: http://localhost:8000
    description: Local development
  - url: https://api.roammate.xyz
    description: Production

components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
    cookieAuth:
      type: apiKey
      in: cookie
      name: rm_access

  schemas:
    ErrorDetail:
      type: object
      required: [detail]
      properties:
        detail:
          type: string
          example: "Trip not found"
    # ... all schemas (see below)
```

### Schemas to define in `components/schemas`

**Auth**: `TokenPair`, `UserOut`, `SignupIn`, `LoginIn`, `OAuthIn`, `ForgotIn`, `ResetIn`, `VerifyIn`, `IdentityOut`

**Places (shared mixin)**: `PlaceFields` (title, place_id, lat, lng, address, photo_url, rating, price_level, types, time_category, added_by) — used by Event, IdeaBinItem, BrainstormBinItem

**Trips**: `TripCreate`, `TripUpdate`, `TripOut`, `TripMemberOut`, `TripDayOut`, `InviteRequest`, `InvitationOut`, `IdeaBinItem`, `IdeaBinItemUpdate`, `IngestRequest`

**Events**: `EventCreate`, `EventUpdate`, `EventOut`, `RippleRequest`

**Groups**: `GroupCreate`, `GroupUpdate`, `GroupOut`, `GroupDetailOut`, `GroupMemberOut`, `GroupInviteRequest`, `GroupInvitationOut`, `GroupTripSummary`, `LibraryIdeaOut`, `TagSummary`

**Votes**: `VoteRequest` (value enum: [-1, 0, 1]), `VoteTally`, `VoterList`

**Dashboard**: `TodayWidgetOut`, `TodayWidgetPage` (state: pre_trip|in_trip|post_trip), `TodayEvent`

### Paths to document

Cover all 80+ routes across: auth (13), trips (14), events (6), groups (16), votes (6), dashboard (1), users (5), notifications (4), ideas (3), brainstorm (8), concierge (6), maps (4), llm (1), billing (8), admin (5), tutorial (4).

For each path document:
- `summary` and `description`
- `parameters` (path, query with descriptions)
- `requestBody` with `$ref` to component schema
- `responses` for all status codes (200/201/204/400/401/403/404/409/422)
- `security` (bearerAuth + cookieAuth, or empty `[]` for public endpoints)
- `tags`

**Key behaviors to call out in descriptions:**
- Auth: dual token transport — cookies for web, body for iOS
- Events: start_time/end_time are trip-local naive time, HH:MM:SS format
- Ripple Engine: `POST /events/ripple/{trip_id}` returns 422 `cross_midnight_shift` as structured error
- Votes: only `admin`/`view_with_vote` roles can cast; `view_only` can read
- `GET /api/events/?trip_id=` — trip is a query param, not path param (non-standard, document explicitly)

---

## Phase 2: Spec Validation Middleware (runtime enforcement)

Add `openapi-core` to validate requests/responses against the spec at runtime (dev/staging only, controlled by `VALIDATE_SPEC=true` env var).

```python
# backend/app/middleware/spec_validation.py
from openapi_core import OpenAPI
from openapi_core.contrib.starlette import StarletteOpenAPIRequest

openapi = OpenAPI.from_file_path("docs/api/openapi.yaml")

class SpecValidationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if not settings.VALIDATE_SPEC:
            return await call_next(request)
        openapi.validate_request(StarletteOpenAPIRequest(request))
        return await call_next(request)
```

This makes the spec the contract enforcer — violating the spec raises an error in development.

---

## Phase 3: Spec Conformance Tests (CI)

### `backend/tests/test_openapi_spec.py`

```python
import schemathesis

schema = schemathesis.from_file("docs/api/openapi.yaml", app=app)

@schema.parametrize()
def test_api_conforms_to_spec(case):
    response = case.call_asgi()
    case.validate_response(response)

def test_spec_coverage():
    with open("docs/api/openapi.yaml") as f:
        spec = yaml.safe_load(f)
    assert len(spec["paths"]) >= 80
    assert "bearerAuth" in spec["components"]["securitySchemes"]
```

Public endpoints are fully tested. Protected endpoints that return 401/403 (documented responses) pass automatically.

---

## Phase 4: Future Spec-First Development Workflow

### Code generation from spec

```bash
# Generate Pydantic v2 models from spec
datamodel-codegen --input docs/api/openapi.yaml --output backend/app/schemas/generated.py
```

### Developer workflow going forward

```
1. Update docs/api/openapi.yaml  ← start here
2. Run datamodel-codegen → updates backend/app/schemas/generated.py
3. Implement / update business logic in endpoints
4. Run tests — spec middleware + schemathesis catch conformance issues
5. PR merged only if spec is updated AND tests pass
```

Document in `docs/api/README.md`. Any PR that adds or changes an endpoint **must** include a diff to `docs/api/openapi.yaml`.

---

## Deliverables

| Deliverable | Description |
|-------------|-------------|
| `docs/api/openapi.yaml` | Hand-authored OpenAPI 3.0 spec covering all ~80 existing routes |
| `docs/api/README.md` | Spec-first workflow guide for developers |
| `backend/app/schemas/errors.py` | Shared `ErrorDetail` and `HTTP_4xx` dicts |
| `backend/app/middleware/spec_validation.py` | Runtime request validation against spec (dev/staging) |
| `backend/tests/test_openapi_spec.py` | Schemathesis conformance + metadata tests |
| `backend/requirements.txt` | Add `pyyaml`, `schemathesis`, `openapi-core`, `datamodel-code-generator` |

## What We Are NOT Doing

- **Not enriching FastAPI decorators to generate the spec** — the YAML is hand-authored, not derived from code
- **Not replacing FastAPI with `connexion`** — too invasive; FastAPI stays, spec enforced via middleware + tests

## Verification

1. `openapi-spec-validator docs/api/openapi.yaml` — spec is valid OpenAPI 3.0
2. `VALIDATE_SPEC=true` in dev → any request/response violating the spec raises immediately
3. `pytest tests/test_openapi_spec.py -v` → all tests pass
4. Change an endpoint to accept an undocumented field → spec validation catches it

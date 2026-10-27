# Expedia Lite design

## Responsibility boundaries

Expedia Lite uses an MVC-style separation with an explicit provider boundary:

| Responsibility | Project location | Current role |
| --- | --- | --- |
| Model and provider access | `backend/app/config.py`, `location_controller.py`, `hotel_discovery.py` | Load backend-only configuration, resolve an exact U.S. postcode, call Geoapify Places, validate provider data, and return typed provider-independent records. |
| Local API-hotel model | `backend/app/database.py`, `saved_hotel_data.py` | Apply additive SQLite tables; save exact provider IDs and ZIP associations; create non-overwriting demo nights; retrieve ZIP-scoped saved subsets; and remove one saved hotel transactionally. |
| Chatbot provider and orchestration | `backend/app/gemini_client.py`, `rag_service.py` | Use the fixed backend-only Gemini REST configuration and schema-constrained JSON for the two-request proposal/retrieval/grounding flow, then map only safe provider outcomes. |
| Read-only chatbot retrieval | `backend/app/chatbot_retrieval.py` | Validate hostile SQL and parameters, enforce the table/column/function allowlist and bounds, and execute with defense-in-depth SQLite read-only controls. |
| HTTP controller | `backend/app/main.py` | Validate five ASCII digits, invoke the discovery controller, and map known outcomes to safe HTTP responses under `/api`. |
| Browser request service | `frontend/src/services/travelApi.js` | Check local saved hotels first, call the provider route only after a successful empty local result, and own save/remove requests through Vite’s `/api` proxy. |
| Chatbot browser service | `frontend/src/services/chatbotApi.js` | Send only `{ question }`, parse stable success and non-2xx outcomes, preserve safe rejected-query traces, and replace invalid transport payloads with safe client errors. |
| View and interaction state | `frontend/src/App.vue` | Own the hotel workflows plus bounded chatbot input, distinct outcome feedback, safe trace rendering, and one shared `selectedPlaceId` for list/map selection. |
| Focused map view | `frontend/src/components/HotelDiscoveryMap.vue` | Render the accepted center, 5 km circle, normalized hotel markers, popups, synchronized selection, and attribution; clean up Leaflet layers on replacement or destruction. |

The browser never calls Geoapify and never receives the API key. The original Assignment 1 SQLite search and booking layers remain separate and operational.

## Local-first data flow

```text
Five-digit ZIP string
        ↓
GET /api/hotels/saved?postcode=...
        ↓
Saved matches? ── yes ─→ saved subset + stored center + demo nights
        │
        no (successful empty result only)
        ↓
GET /api/hotels/nearby?postcode=...
        ↓
Preserved Part 1 Geoapify workflow
```

A local-storage error ends the sequence with useful feedback; it never triggers the provider request. Both result sources use the same normalized provider ID and coordinate fields, so the existing shared list/map selection remains unchanged.

`saved_hotels` owns one exact provider ID. `saved_search_contexts` owns one verified U.S. ZIP center. `saved_hotel_zip_associations` connects them without duplication. `demo_hotel_nights` owns the October 10–14, 2026 classroom rows. The 10,000-cent rate and 20-room count are visibly labeled simulated classroom data and are never described as provider-supplied inventory.

Saving uses one transaction and conflict-safe inserts. Repeating a save may fill a missing association or missing demo date but never overwrites an existing rate or room count. Removing uses one transaction to delete the selected hotel’s demo rows, associations, and hotel row, followed by cleanup of only ZIP contexts no longer referenced by any hotel.

## Assignment 2 Part 1 data flow

```text
Five-digit ZIP string
        ↓
Vue validation and /api proxy
        ↓
GET /api/hotels/nearby?postcode=...
        ↓
Exact U.S. postcode geocoding
        ↓
Verified postcode center (latitude/longitude)
        ↓
Geoapify Places: accommodation.hotel
filter=circle:{longitude},{latitude},5000
bias=proximity:{longitude},{latitude}
limit=20
        ↓
Typed normalization and safe error mapping
        ↓
Sanitized FastAPI response
        ↓
One Vue hotel collection → table + Leaflet markers
        ↓
One shared provider place ID ↔ synchronized selection
```

The postcode remains a string from input through the controller, preserving leading zeros. A geocoding result is accepted only when it identifies the exact requested U.S. postcode and supplies finite, in-range coordinates. The verified longitude and latitude—not an unverified user-entered point—become the center of the strict 5,000-meter Places circle. A proximity bias orders results but does not replace the circle boundary.

## Provider-independent contract

The nearby-hotel response contains:

- `search_center`: postcode, normalized country code, optional locality, latitude, and longitude;
- `hotels`: provider place identifier, optional name, optional formatted address, latitude, longitude, and optional valid distance;
- `search_radius_meters`: `5000`;
- `result_limit`: `20`;
- the usable count and any omitted-provider-record count.

Every map hotel must have a nonblank provider place identifier and valid coordinates. Missing names are displayed as `Name unavailable`; missing addresses are displayed as `Address not provided`. Invalid or ambiguous records are omitted rather than repaired with invented data. No provider result is presented as proof of price, rating, rooms, availability, or bookability. One result page of up to 20 records is a bounded demonstration, not an exhaustive inventory.

## Response states

- **Invalid input:** Vue and FastAPI require exactly five ASCII digits; no provider search is treated as successful.
- **Unresolved ZIP:** no exact U.S. postcode was accepted, so no substitute hotel search occurs.
- **Missing configuration:** the backend reports configuration is unavailable without revealing the key.
- **No nearby hotels:** a valid provider response with zero usable hotels is HTTP 200 and keeps the accepted center visible.
- **Provider failure or timeout:** a safe service error is returned without a raw exception or credential-bearing URL.
- **Rate or quota failure:** HTTP 429 receives distinct retry-later feedback.
- **Malformed response:** invalid provider structure is not misreported as a legitimate empty result.
- **Success:** the center and one normalized collection are returned to both list and map.
- **Saved local success:** the stored center, ZIP-associated subset, five dated demo values, and incomplete-inventory notice are returned without a provider request.
- **Local database failure:** safe local feedback is shown and provider fallback is prohibited.
- **Save/remove failure:** the interface changes saved state only after backend success; a failed transactional removal leaves all related rows intact.

## List and map synchronization

`App.vue` owns the only hotel-selection state: `selectedPlaceId`. A successful search replaces stale results and selects the first usable hotel when present. A list control updates that ID; the map component highlights and opens the matching marker. A marker activation emits the same provider ID; the matching row becomes selected and is scrolled into view. Keyboard-operable list controls and Leaflet markers use the same path.

The search-center marker and translucent 5 km circle explain query origin and radius but are not hotel results. A new search or empty result clears old rows, markers, and selection. At narrow widths the list and map stack while the table keeps its own horizontal scrolling area.

OpenStreetMap Standard tiles are used only for this low-volume classroom demonstration. Leaflet’s attribution control stays enabled and visibly includes `© OpenStreetMap contributors`; a separate `Powered by Geoapify` link identifies the geocoding and Places source.

## Preserved Assignment 1 model

SQLite stores the instructor-supplied hotel, trip, user, and booking records with their text IDs. `app_metadata` records the one-time seed marker and monotonically increasing booking counter. Assignment 1 hotel search and booking CRUD continue to use SQLite after the first seed. Cancellation retains a row with `cancelled` status; deletion removes the selected booking without allowing its ID to be reused.

The local database is ignored runtime state. Instructor CSV files remain unchanged. Authentication, payment processing, taxes, fees, and live room inventory remain outside the application.

## Assignment 2 Part 2 RAG flow — implemented and bounded live flow verified

The reviewed local hotel storage remains the only retrieval source. The selected provider is Google Gemini API and the exact model is `gemini-3.5-flash-lite`. The provider-independent retrieval layer, two-request backend service, FastAPI route, browser request service, and Vue interface are implemented. Repeatable automated checks use fixed Gemini fixtures, temporary databases, fake credentials, and mocked HTTP only. One explicitly authorized live flow completed Request 1, validated and executed the bounded read-only SQL over the saved-hotel tables, and completed Request 2 with a grounded answer over the two retrieved classroom hotels. Fixed mocked no-match and mutation-rejection scenarios prove that Request 2 is skipped and the temporary database remains unchanged. The retired OpenRouter/Nemotron approach produced three controlled malformed Request 1 outcomes and remains documented as failed/revised evidence.

```text
Labeled natural-language question
        ↓
Vue validation and local /api request only
        ↓
Thin FastAPI chatbot route
        ↓
Backend-only Gemini GenerateContent client (REQUEST 1)
question + fixed allowed schema + query rules
        ↓
Untrusted schema-constrained JSON: SQL + positional parameters
        ↓
SQL policy validation
        ↓
SQLite mode=ro + query_only + default-deny authorizer
approved tables/functions + bound parameters + time/row/payload limits
        ↓
0 rows → deterministic no-match/insufficient-data response
        ↓ bounded rows
Backend normalization and deterministic date/total/coverage calculations
        ↓
Backend-only Gemini GenerateContent client (REQUEST 2)
fixed grounding rules + original question + limited records only
        ↓
Grounded answer with record references
        ↓
Vue: proposed SQL + retrieved records + answer + explicit state label
```

### Current responsibilities

- **Configuration/provider model:** backend configuration reads the Gemini key from the ignored project-root `.env`; health exposes configured/not-configured status only. Model and endpoint are fixed backend constants and cannot be supplied by Vue.
- **Model client:** sends finite-timeout REST requests to the exact model with the key only in `x-goog-api-key`, bounds request/response bytes and token output, requests one schema-constrained JSON candidate, maps safe error categories, and never logs headers, raw provider payloads, or exception text. Automatic retries and provider/model fallbacks are absent.
- **Query proposal service:** supplies the fixed local-hotel schema, rules, exact JSON keys, and one minimal `?`-binding/final-`LIMIT` example. It requires `sql` and `parameters`; optional or blank `intent` becomes a neutral internal description. Unknown fields, aliases, unsafe types, malformed or duplicate-key JSON, and oversized data are rejected. Every accepted proposal still passes through the unchanged retrieval security layer; the model has no database connection or SQL-execution tool.
- **SQL policy/controller:** allows one bounded read-only query over `saved_hotels`, `saved_hotel_zip_associations`, `saved_search_contexts`, and `demo_hotel_nights`; validates placeholders and parameters; default-denies every other SQLite authorization action.
- **Retrieval model:** opens a separate `file:` URI connection in `mode=ro`, enables `PRAGMA query_only`, installs an authorizer and progress deadline, executes with bound parameters, and returns no more than 20 normalized rows or 32 KiB.
- **Grounding service:** computes coverage and totals from integer cents/dated rows, then gives the second request only the question and limited records. Schema-constrained JSON requires an answer, referenced row numbers, and an explanation; limitation is optional. Independent row-reference and grounding checks still apply. Zero rows and incomplete requested nights produce deterministic no-match/insufficient-data feedback without Request 2.
- **FastAPI controller:** validates question length, orchestrates the two-request flow, and maps missing configuration, rejected query, insufficient data, authentication, quota/rate, timeout, malformed response, and provider failure to safe distinct responses.
- **Vue request/view:** `chatbotApi.js` submits only the bounded question through `/api`; `App.vue` clears stale output, prevents repeat submission while loading, and renders labeled SQL, semantic parameter/record tables, a grounded answer, row references, limitations, and distinct error/empty states without displacing the existing search/map/local-storage workflows.

### Planned safety invariants

- A model response can never authorize itself. Static backend policy and SQLite enforce the boundary.
- `Connection.execute` is used for one statement; `executescript` is prohibited.
- User values travel as bound parameters, not interpolated SQL literals.
- Assignment 1 tables, users, and bookings are outside the chatbot allowlist.
- Checkout is excluded from multi-night stays. Missing nights are not treated as available.
- Prices and room counts remain labeled simulated classroom data, never live inventory.
- No chatbot response can save/remove a hotel or create/cancel/delete a booking.
- Automated tests use labeled fixtures/mocks; a minimal live call requires explicit separate approval.
- Non-sensitive internal diagnostic codes distinguish schema-invalid proposal/answer fields for tests and evidence. The public chatbot response never returns raw provider content.

Research rationale and rejected approaches are recorded in [`assignment-2-part-2-research.md`](assignment-2-part-2-research.md). The early interface proposal is [`assignment-2-part-2-rag-mockup.svg`](assignment-2-part-2-rag-mockup.svg).

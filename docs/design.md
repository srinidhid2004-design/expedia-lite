# Expedia Lite design

## Responsibility boundaries

Expedia Lite uses an MVC-style separation with an explicit provider boundary:

| Responsibility | Project location | Assignment 2 Part 1 role |
| --- | --- | --- |
| Model and provider access | `backend/app/config.py`, `location_controller.py`, `hotel_discovery.py` | Load backend-only configuration, resolve an exact U.S. postcode, call Geoapify Places, validate provider data, and return typed provider-independent records. |
| HTTP controller | `backend/app/main.py` | Validate five ASCII digits, invoke the discovery controller, and map known outcomes to safe HTTP responses under `/api`. |
| Browser request service | `frontend/src/services/travelApi.js` | Send the entered postcode only to the local FastAPI route through Vite’s `/api` proxy. |
| View and interaction state | `frontend/src/App.vue` | Own the form, feedback states, sanitized search-center table, hotel table, and one shared `selectedPlaceId`. |
| Focused map view | `frontend/src/components/HotelDiscoveryMap.vue` | Render the accepted center, 5 km circle, normalized hotel markers, popups, synchronized selection, and attribution; clean up Leaflet layers on replacement or destruction. |

The browser never calls Geoapify and never receives the API key. The original Assignment 1 SQLite search and booking layers remain separate and operational.

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

## List and map synchronization

`App.vue` owns the only hotel-selection state: `selectedPlaceId`. A successful search replaces stale results and selects the first usable hotel when present. A list control updates that ID; the map component highlights and opens the matching marker. A marker activation emits the same provider ID; the matching row becomes selected and is scrolled into view. Keyboard-operable list controls and Leaflet markers use the same path.

The search-center marker and translucent 5 km circle explain query origin and radius but are not hotel results. A new search or empty result clears old rows, markers, and selection. At narrow widths the list and map stack while the table keeps its own horizontal scrolling area.

OpenStreetMap Standard tiles are used only for this low-volume classroom demonstration. Leaflet’s attribution control stays enabled and visibly includes `© OpenStreetMap contributors`; a separate `Powered by Geoapify` link identifies the geocoding and Places source.

## Preserved Assignment 1 model

SQLite stores the instructor-supplied hotel, trip, user, and booking records with their text IDs. `app_metadata` records the one-time seed marker and monotonically increasing booking counter. Assignment 1 hotel search and booking CRUD continue to use SQLite after the first seed. Cancellation retains a row with `cancelled` status; deletion removes the selected booking without allowing its ID to be reused.

The local database is ignored runtime state. Instructor CSV files remain unchanged. Authentication, payment processing, taxes, fees, live room inventory, shortlist persistence, and chatbot/RAG behavior are outside Assignment 2 Part 1.

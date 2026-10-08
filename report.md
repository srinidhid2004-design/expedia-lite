# Expedia Lite — Assignment 2, Part 1

## Repository and submission status

Public repository: [https://github.com/srinidhid2004-design/expedia-lite](https://github.com/srinidhid2004-design/expedia-lite)

Assessed Assignment 2 Part 1 commit: **Pending final review.** No assessed commit was created during this documentation checkpoint.

Live demo video: **Pending.** The video has not yet been recorded or published.

Project records: [README.md](https://github.com/srinidhid2004-design/expedia-lite/blob/main/README.md), [AGENTS.md](https://github.com/srinidhid2004-design/expedia-lite/blob/main/AGENTS.md), [design](https://github.com/srinidhid2004-design/expedia-lite/blob/main/docs/design.md), [research](https://github.com/srinidhid2004-design/expedia-lite/blob/main/docs/assignment-2-part-1-research.md), [early mockup](https://github.com/srinidhid2004-design/expedia-lite/blob/main/docs/assignment-2-part-1-mockup.svg), [verification procedure](https://github.com/srinidhid2004-design/expedia-lite/blob/main/docs/verification.md), [evidence log](https://github.com/srinidhid2004-design/expedia-lite/blob/main/docs/evidence.md), [prompt index](https://github.com/srinidhid2004-design/expedia-lite/blob/main/prompts/README.md), and [current handoff](https://github.com/srinidhid2004-design/expedia-lite/blob/main/handoffs/current.md).

The Assignment 2 files and evidence are still on the local feature branch. Their `main` links above and below are publication targets that become publicly accessible after final review, commit, merge, and push. This report does not claim that unpublished paths are already live.

## Startup and safe configuration

Create the Python virtual environment, install the declared backend requirements, and install the locked frontend dependencies:

```powershell
python -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt
cd frontend
npm install
cd ..
```

Create a project-root `.env` file beside `backend/` and `frontend/` with this setting:

```dotenv
GEOAPIFY_API_KEY=your-key-here
```

The `.env` file is ignored. The key must not be placed in Vue, a `VITE_` variable, documentation, screenshots, fixtures, logs, or Git. `backend/app/config.py` reads it through an explicit backend path, and `/api/health` reports only whether a nonblank value is configured. FastAPI must be restarted after `.env` changes.

Start FastAPI on `127.0.0.1:8000` and Vue on `127.0.0.1:5173` using the commands in the public [README](https://github.com/srinidhid2004-design/expedia-lite/blob/main/README.md). The application page is `http://127.0.0.1:5173/`; FastAPI’s root `/` intentionally has no page, while `/api/health` is the backend health endpoint.

## Research, observations, and adopted decisions

Primary sources were accessed October 7, 2026. Full notes are in the [research document](https://github.com/srinidhid2004-design/expedia-lite/blob/main/docs/assignment-2-part-1-research.md).

| Source | Observation or weakness | Expedia Lite decision |
| --- | --- | --- |
| [Geoapify Geocoding API](https://apidocs.geoapify.com/docs/geocoding/) | Postcodes need a country context and a geocoder may otherwise return a nearby or differently formatted result. | Send a structured postcode with `type=postcode`, `filter=countrycode:us`, and `format=json`; accept only an exact requested U.S. postcode with valid coordinates. |
| [Geoapify Places API](https://apidocs.geoapify.com/docs/places/) | Proximity bias affects order but is not a geographic boundary; provider fields can be optional. | Request `accommodation.hotel` with a strict `circle:longitude,latitude,5000` filter, matching proximity bias, `lang=en`, and `limit=20`; normalize only supported fields. |
| [Geoapify pricing and attribution](https://www.geoapify.com/pricing/) | Requests consume quota and attribution is required; returned coverage is not a complete inventory guarantee. | Search only on explicit submit, block duplicate submission while loading, show `Powered by Geoapify`, and call the result one bounded provider page rather than “all hotels.” |
| [Leaflet Quick Start](https://leafletjs.com/examples/quick-start/) and [Leaflet API reference](https://leafletjs.com/reference.html) | Maps need an explicit height, managed layers, event handling, and cleanup. Independent list/map state can drift. | Use a focused Vue map component and one `selectedPlaceId` owned by the parent; update or clear layers with each search and remove the map on destruction. |
| [OpenStreetMap Standard tile policy](https://operations.osmfoundation.org/policies/tiles/) and [copyright guidance](https://www.openstreetmap.org/copyright) | Standard tiles are best-effort, prohibit bulk/offline use, and require visible attribution. | Use Standard tiles only for this low-volume classroom demo, do not prefetch, preserve browser caching behavior, and visibly show `© OpenStreetMap contributors`. |
| [Airbnb search-results explanation](https://www.airbnb.com/help/article/39) and [map-search help](https://www.airbnb.com/help/article/252) | A list/map layout helps spatial comparison, but commercial products may personalize, broaden, sponsor, or show map results that differ from the list. | Adopt the side-by-side comparison and selectable markers, but keep one identical bounded collection in both views and never silently broaden the 5 km search. |

Weaknesses deliberately avoided include substituting a nearby postcode, treating a proximity bias as a radius, labeling provider failure as “no hotels,” silently dropping list/map synchronization, inventing missing fields, hiding attribution, and implying prices, ratings, availability, or exhaustive coverage.

## Early mockup and revised approach

The approved [early annotated mockup](https://github.com/srinidhid2004-design/expedia-lite/blob/main/docs/assignment-2-part-1-mockup.svg) established the five-digit ZIP input, loading and error states, accepted search center, responsive list/map layout, selected row and marker, and visible attribution. The final implementation preserved the cream, navy, and burnt-orange Expedia Lite visual language. During implementation, provider place IDs were shown with the rows for traceability, the result cap and omitted-record message were made explicit, and the separate center marker plus 5 km circle clarified why a hotel appeared.

One revised approach began with the in-class fixed `Look up ZIP 16802` button. Its screenshot proved the first public API call but was insufficient for the final Part 1 rubric because it did not demonstrate user-entered input or the complete hotel list/map workflow. The panel was revised to use a labeled text ZIP input that preserves leading zeros, semantic tables, distinct feedback states, nearby-hotel discovery, and synchronized Leaflet selection.

A second correction concerned startup expectations: opening `http://127.0.0.1:8000/` produced the expected FastAPI `404 Not Found` response because the backend has no root page. Verification was corrected to use port 8000 at `/api/health` and to open the actual Vue application on port 5173.

## Implementation responsibilities and data flow

The browser keeps the ZIP as text, validates exactly five digits, and calls only the local FastAPI route through Vite’s `/api` proxy. `backend/app/location_controller.py` resolves the exact requested U.S. postcode. `backend/app/hotel_discovery.py` uses that verified coordinate as the center of a 5,000-meter Geoapify Places circle and returns up to 20 normalized hotels. `backend/app/main.py` provides the thin route and safe status mapping. It never returns the key, full provider URL, or raw exception.

The provider-independent hotel result contains a provider place identifier, optional name, optional formatted address, valid latitude and longitude, and an optional valid distance. Missing names appear as `Name unavailable`; missing addresses appear as `Address not provided`. Records without a stable identifier or valid coordinates are omitted because they cannot participate honestly in synchronized list/map behavior.

`frontend/src/services/travelApi.js` owns the local request. `frontend/src/App.vue` owns form, loading/error/result state, the sanitized center, the hotel table, and the single shared `selectedPlaceId`. `frontend/src/components/HotelDiscoveryMap.vue` owns Leaflet initialization, OpenStreetMap tiles, the distinct center marker, radius circle, hotel markers, popups, attribution, layer replacement, and destruction cleanup.

Data flow:

```text
ZIP text → Vue validation → /api/hotels/nearby
→ exact Geoapify postcode → verified point
→ Geoapify Places accommodation.hotel within 5 km, limit 20
→ typed normalization → sanitized FastAPI response
→ one Vue collection rendered as list and map
→ one provider place ID synchronizes selection both ways
```

Assignment 1’s SQLite hotel search and simulated booking behavior remains present and separate.

## Verification

Observation date: **October 7, 2026**. Tested ZIP: **16802**.

| Action | Expected result | Observed result |
| --- | --- | --- |
| Run the complete backend suite through `backend/.venv` | All Assignment 1, postcode, discovery, and route tests pass | 57 tests passed; two known upstream FastAPI/Starlette test-client deprecation warnings were non-failing |
| Run the focused mocked discovery suite | Success fixture, missing optional fields, zero results, malformed data, timeout/provider failure, rate limit, missing configuration, and unresolved ZIP pass without live quota | 9 focused tests passed |
| Run Oxlint, ESLint, production build, and `git diff --check` | No lint, build, or whitespace failure | All four checks passed; Vite 8.3.0 transformed 16 modules and built successfully |
| Submit one live `16802` search | Exact U.S. postcode center and one bounded 5 km hotel page; no fixed result-count assumption | Center was State College, `US`, latitude `40.803167822`, longitude `-77.861384958`; the provider returned 20 usable records on that request |
| Compare sanitized API, list, and map | Center matches; every normalized hotel appears once in the list and once as a hotel marker | 20 unique provider IDs in the list matched 20 hotel markers; the distinct center marker and 5 km circle were also visible |
| Select a list result and then a different marker | Matching marker/popup and matching row identify the same shared provider place ID | Both directions passed; keyboard list activation and keyboard-operable markers also passed |
| Check invalid, unresolved, zero-hotel, provider-failure, malformed, rate/quota, and missing-configuration states | Each state is safe and distinct; no extra live quota is consumed | Local validation, mocks, and the credential-free fixture produced the expected distinct outcomes |
| Inspect attribution, narrow layout, and console | Required attribution is visible, the interface is usable at 390 × 844, and no application error appears | All checks passed; `Leaflet | © OpenStreetMap contributors` remained visible and the console had zero application errors or warnings |
| Search `Harbor` in the preserved Assignment 1 form | Existing matching stays T001 and T009 remain operational | The visible interface returned both trip IDs |

Detailed commands, live-versus-mocked labels, expected-versus-observed notes, corrections, and limitations are in the [evidence log](https://github.com/srinidhid2004-design/expedia-lite/blob/main/docs/evidence.md).

## Screenshots

These repository publication-target links will become public after the reviewed Assignment 2 Part 1 files are committed, merged, and pushed:

- [Successful ZIP results with list, map, center, and attribution](https://github.com/srinidhid2004-design/expedia-lite/blob/main/screenshots/assignment-2-part-1-live-list-map.png)
- [Synchronized selected hotel in the list and map](https://github.com/srinidhid2004-design/expedia-lite/blob/main/screenshots/assignment-2-part-1-synchronized-selection.png)
- [Representative invalid-input feedback](https://github.com/srinidhid2004-design/expedia-lite/blob/main/screenshots/assignment-2-part-1-invalid-zip.png)

The browser’s tall-element screenshot stitching can repeat content below the primary viewport when capturing the long table. The primary center, list, selected marker or popup, and attribution evidence remains visible; result counts were also verified independently.

## Limitations and next work

- Geoapify coverage and optional fields vary. The app presents one page of up to 20 usable hotel records and does not claim an exhaustive inventory.
- The Places result does not prove price, rating, room inventory, availability, or bookability.
- Only exact five-digit U.S. ZIP input is supported; broader address/city search is outside Part 1.
- OpenStreetMap Standard tiles are appropriate for this local, low-volume classroom demonstration, not guaranteed production service.
- The application has no authentication, payments, taxes, fees, or real reservations.
- Assignment 2 Part 2 shortlist persistence and chatbot/RAG behavior are not implemented.
- The assessed commit and live demo-video link remain pending final review.

## AI assistance disclosure

The AI tool and model used were **OpenAI Codex — GPT-5**. The Codex interface did not expose a more specific internal snapshot identifier, so no version or model suffix is claimed. OpenAI Codex (GPT-5) assisted with research summarization, the early mockup, implementation planning, code generation, tests, debugging, verification, and documentation. Human review and approval were performed at each milestone. No additional generative AI tool or model is claimed for this work.

## Prompt traceability

Selected prompt records connect requirements to decisions, code, and verification:

- Research decision: “use a 5 km circle” and study attribution, list/map patterns, omissions, and misleading behavior — [Prompt 11: research and mockup](https://github.com/srinidhid2004-design/expedia-lite/blob/main/prompts/11-assignment-2-research-and-mockup.md).
- Dependency decision: inspect, explain, obtain approval, and install only Leaflet locally — [Prompt 12: dependency checkpoint](https://github.com/srinidhid2004-design/expedia-lite/blob/main/prompts/12-leaflet-dependency-checkpoint.md).
- Backend code decision: keep the key backend-only, cap results, and normalize only supported fields — [Prompt 13: hotel-discovery backend](https://github.com/srinidhid2004-design/expedia-lite/blob/main/prompts/13-hotel-discovery-backend.md).
- Route and list decision: preserve leading zeros and treat zero hotels as a successful empty result — [Prompt 14: route and list](https://github.com/srinidhid2004-design/expedia-lite/blob/main/prompts/14-hotel-discovery-route-and-list.md).
- Map decision: use one shared selection state for rows and markers — [Prompt 15: list/map synchronization](https://github.com/srinidhid2004-design/expedia-lite/blob/main/prompts/15-leaflet-list-map-synchronization.md).
- Verification decision: one live search, mocked failures, regression check, credential scan, and screenshots — [Prompt 16: AutoLoop verification](https://github.com/srinidhid2004-design/expedia-lite/blob/main/prompts/16-assignment-2-part-1-verification.md).
- Disclosure and report decision: document the model transparently and keep assessed commit/video pending — [Prompt 17: documentation checkpoint](https://github.com/srinidhid2004-design/expedia-lite/blob/main/prompts/17-assignment-2-part-1-documentation.md).

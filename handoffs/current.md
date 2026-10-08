# Current handoff

Updated: 2026-10-07

## Orientation

Expedia Lite is a FastAPI, Vue 3, SQLite, Geoapify, and Leaflet course application. Assignment 1 remains published on `main`. Assignment 2 Part 1 is implemented and manually reviewed in the working interface on `feature/assignment-2-part-1`; its final assessed commit, merge/publication, and demo-video URL are still pending.

Read [`../README.md`](../README.md), follow [`../AGENTS.md`](../AGENTS.md), use [`../docs/verification.md`](../docs/verification.md) for repeatable checks, and consult [`../docs/evidence.md`](../docs/evidence.md) before continuing.

## What exists

- Preserved Assignment 1 behavior: one-time SQLite seeding from all four instructor CSVs, partial hotel-name search, demo users, simulated booking history, create, cancel-retain, delete, and restart persistence.
- A project-root `.env` is ignored and read only by `backend/app/config.py`; health reports configuration status without revealing a value.
- Exact U.S. postcode geocoding accepts a five-character digit string and preserves leading zeros.
- `backend/app/hotel_discovery.py` uses the verified postcode point as a strict 5 km Geoapify Places circle for `accommodation.hotel`, applies proximity bias, limits one page to 20, and normalizes only supported provider fields.
- `GET /api/hotels/nearby?postcode=...` maps invalid input, unresolved ZIP, missing configuration, provider failure, rate/quota failure, and successful empty results distinctly and safely.
- Vue sends only the postcode through the local `/api` proxy, clears stale state, prevents duplicate submission while loading, and displays the accepted center and provider-supported hotel information.
- `frontend/src/components/HotelDiscoveryMap.vue` renders OpenStreetMap Standard tiles, a distinct center marker, the 5 km circle, one marker per normalized hotel, popups, and visible attribution.
- The hotel list and map share one `selectedPlaceId`; selection is synchronized from list to marker and marker to list, including keyboard-operated list selection.
- Missing names and addresses use honest labels. The UI makes no price, rating, availability, room, booking, or exhaustive-inventory claim for Geoapify results.
- Research, early mockup, prompt records, verification instructions, evidence, and the submission report have been aligned with Assignment 2 Part 1.

## What passed

- Complete backend suite: 57 tests passed with two known upstream FastAPI/Starlette test-client deprecation warnings.
- Focused mocked hotel-discovery suite: 9 tests passed.
- Oxlint, ESLint, Vite production build, and `git diff --check` passed.
- One live search for ZIP `16802` on October 7, 2026 resolved State College, US at latitude `40.803167822`, longitude `-77.861384958`.
- The one live provider response contained a capped, variable page of 20 normalized hotels; the table and map had matching provider identities and counts.
- List-to-marker, marker-to-list, and keyboard selection stayed synchronized.
- Loading, invalid input, unresolved ZIP, zero hotels, provider failure, malformed response, rate/quota failure, and missing configuration were distinguished through local validation or mocked checks.
- Attribution remained visible, the narrow layout was usable, and the browser console had no application errors.
- The preserved `Harbor` search still returned trip IDs `T001` and `T009`.
- The user manually reviewed and approved the working Assignment 2 Part 1 interface.

Detailed action/expected/observed evidence and screenshot links are in [`../docs/evidence.md`](../docs/evidence.md).

## Git and publication state

- Current feature branch: `feature/assignment-2-part-1`.
- Public repository: [https://github.com/srinidhid2004-design/expedia-lite](https://github.com/srinidhid2004-design/expedia-lite).
- Preserved Part 1 implementation commit: `0c1666d2bb03fdefda55ccf3b905d80801d78d5f`.
- Assignment 1 Part 2 merge commit: `a98a9ccd1de2329d35b2924e2b1f121fe7359627`.
- First-public-API milestone commit: `91a20b0c009748393d1156cc2b83010b4a86fbf3`.
- Assignment 2 Part 1 assessed commit: **pending final review**.
- Assignment 2 Part 1 live demo-video URL: **pending**.
- The current documentation checkpoint did not commit, merge, or push.

## Limitations

- Geoapify coverage and optional fields can change. The interface shows one bounded page of up to 20 usable records and does not claim exhaustiveness.
- OpenStreetMap Standard tiles are suitable for this local, low-volume classroom demonstration but provide no production SLA; a production deployment would need a suitable tile-service plan.
- Exact five-digit U.S. ZIP input is required; broader location search is outside Part 1.
- The map is a discovery view. It does not supply routes, pricing, ratings, availability, booking, shortlist persistence, or chatbot/RAG behavior.
- The saved tall-page screenshots can contain a browser-stitching artifact below the primary evidence area; the documented center, list, selected marker, and attribution remain visible.
- Two upstream test-client deprecation warnings remain non-failing.

## Next task

The next checkpoint is final human review of the updated documentation and report, plus recording the live demonstration video. After separate authorization, create the assessed Assignment 2 Part 1 commit, replace the pending commit and video fields with final public values, rerun the documented checks if required, and publish normally. Do not begin Assignment 2 Part 2 shortlist or chatbot/RAG work as part of this checkpoint.

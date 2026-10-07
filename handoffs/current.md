# Current handoff

Updated: 2026-10-07

## Orientation

Expedia Lite is a FastAPI, Vue 3, and SQLite course application. Assignment 1 Part 2 is implemented, manually reviewed, merged into `main`, and published in the existing public repository. The approved first-public-API ZIP-location activity now continues on `feature/assignment-2-part-1`. Read [`../README.md`](../README.md), follow [`../AGENTS.md`](../AGENTS.md), and use [`../docs/verification.md`](../docs/verification.md) for the established Assignment 1 checks.

## What exists

- The unmodified instructor data pack remains under `data/`.
- SQLite is created locally and seeded once from all four CSVs; later application reads and writes use SQLite.
- Hotel search preserves the Part 1 partial, case-insensitive behavior.
- FastAPI exposes health, search, demo-traveler, booking-history, create-booking, cancel-booking, and delete-booking routes under `/api`.
- Vue exposes the required traveler selection, search, create, read, cancel-retain, and delete flow.
- A persistent booking counter allocates unique IDs without reusing deleted IDs.
- Generated databases, the virtual environment, dependency directory, caches, and build output are ignored.
- No Part 2 dependency declaration or instructor data file changed.
- The backend loads the project-root `.env` through an explicit configuration helper and reports only whether the Geoapify key is configured.
- A backend-only Geoapify controller resolves an exact U.S. postcode while keeping the credential and provider request out of Vue.
- The fixed `16802` demonstration route remains available, and a validated dynamic route accepts exactly five ASCII digits while preserving leading zeros.
- Vue provides a labeled ZIP text input and a semantic result table without adding a dependency or changing the existing hotel search and booking flows.

## Git and publication state

- Preserved Part 1 implementation commit: `0c1666d2bb03fdefda55ccf3b905d80801d78d5f`.
- Reviewed Part 2 feature commit: `5b329d4984caa1348af39c20d79e077420493c2c`.
- Part 2 merge commit on `main`: `a98a9ccd1de2329d35b2924e2b1f121fe7359627`.
- Public repository: [https://github.com/srinidhid2004-design/expedia-lite](https://github.com/srinidhid2004-design/expedia-lite).
- The feature branch was retained. No history rewrite, force-push, remote change, or additional remote occurred.
- The first-public-API milestone is isolated on `feature/assignment-2-part-1`; it has not been merged or pushed by this checkpoint.

## Verification state

- Backend: 15 tests passed with two previously documented upstream deprecation warnings.
- Frontend: Oxlint passed, ESLint passed, and the Vite production build passed.
- API and visible browser checks passed for matching and no-results hotel searches.
- Create/read, browser-refresh persistence, cancel-retain, and delete behavior passed.
- The final restart recovery used an ignored disposable database: U006 retained cancelled B007, deleted B008 stayed absent, and SQLite held 8 hotels, 12 trips, 6 users, and 7 bookings with `seeded=1` and `next_booking_number=9`.
- The browser console had no application errors.
- Only identified task-owned services were stopped; ports 8000 and 5173 were released.
- Only the exact disposable verification database was removed. The real `backend/expedia_lite.sqlite3` retained its baseline SHA-256.
- First-public-API automated verification: 36 backend tests passed with the same two upstream warnings; Oxlint, ESLint, and the production build passed.
- Live ZIP `16802` resolved to State College, US, at latitude `40.803167822` and longitude `-77.861384958`. The visible result table matched the sanitized backend response, Harbor search still returned `T001` and `T009`, and the browser console had no application errors.
- The user completed and approved manual review of the ZIP-input and result-table milestone.

Detailed commands and observed results are in [`../docs/evidence.md`](../docs/evidence.md). Public report links and immutable screenshot links are in [`../report.md`](../report.md).

## Remaining work

- Course-site submission remains for the user.
- Two upstream FastAPI/Starlette test-client deprecation warnings remain; no dependency change is required for passing checks.
- The classroom app intentionally has no authentication, payments, taxes, fees, or real inventory behavior.
- Assignment 2 hotel discovery, the synchronized Leaflet map, persistent shortlist/local-storage foundation, and revised chatbot/RAG requirements remain unimplemented by the first-public-API milestone.

## Next task

After a separate authorization, begin Assignment 2 Part 1 research and an early mockup, then implement live nearby-hotel discovery and the synchronized map on `feature/assignment-2-part-1`. Preserve the approved ZIP milestone and do not begin shortlist or chatbot work as part of Part 1.

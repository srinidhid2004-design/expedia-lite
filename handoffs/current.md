# Current handoff

Updated: 2026-09-17

## Orientation

Expedia Lite is a FastAPI, Vue 3, and SQLite course application. Part 2 is implemented, manually reviewed, merged into `main`, and published in the existing public repository. Read [`../README.md`](../README.md), follow [`../AGENTS.md`](../AGENTS.md), and use [`../docs/verification.md`](../docs/verification.md) for repeatable checks.

## What exists

- The unmodified instructor data pack remains under `data/`.
- SQLite is created locally and seeded once from all four CSVs; later application reads and writes use SQLite.
- Hotel search preserves the Part 1 partial, case-insensitive behavior.
- FastAPI exposes health, search, demo-traveler, booking-history, create-booking, cancel-booking, and delete-booking routes under `/api`.
- Vue exposes the required traveler selection, search, create, read, cancel-retain, and delete flow.
- A persistent booking counter allocates unique IDs without reusing deleted IDs.
- Generated databases, the virtual environment, dependency directory, caches, and build output are ignored.
- No Part 2 dependency declaration or instructor data file changed.

## Git and publication state

- Preserved Part 1 implementation commit: `0c1666d2bb03fdefda55ccf3b905d80801d78d5f`.
- Reviewed Part 2 feature commit: `5b329d4984caa1348af39c20d79e077420493c2c`.
- Part 2 merge commit on `main`: `a98a9ccd1de2329d35b2924e2b1f121fe7359627`.
- Public repository: [https://github.com/srinidhid2004-design/expedia-lite](https://github.com/srinidhid2004-design/expedia-lite).
- The feature branch was retained. No history rewrite, force-push, remote change, or additional remote occurred.

## Verification state

- Backend: 15 tests passed with two previously documented upstream deprecation warnings.
- Frontend: Oxlint passed, ESLint passed, and the Vite production build passed.
- API and visible browser checks passed for matching and no-results hotel searches.
- Create/read, browser-refresh persistence, cancel-retain, and delete behavior passed.
- The final restart recovery used an ignored disposable database: U006 retained cancelled B007, deleted B008 stayed absent, and SQLite held 8 hotels, 12 trips, 6 users, and 7 bookings with `seeded=1` and `next_booking_number=9`.
- The browser console had no application errors.
- Only identified task-owned services were stopped; ports 8000 and 5173 were released.
- Only the exact disposable verification database was removed. The real `backend/expedia_lite.sqlite3` retained its baseline SHA-256.

Detailed commands and observed results are in [`../docs/evidence.md`](../docs/evidence.md). Public report links and immutable screenshot links are in [`../report.md`](../report.md).

## Remaining work

- Course-site submission remains for the user.
- Two upstream FastAPI/Starlette test-client deprecation warnings remain; no dependency change is required for passing checks.
- The classroom app intentionally has no authentication, payments, taxes, fees, or real inventory behavior.

## Next task

Use the finalized public `report.md` for the course submission. Do not change the reviewed implementation unless a new assignment requirement is provided.

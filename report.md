# Expedia Lite — Part 1

## Repository and commit

Repository URL: **pending**. Git is initialized locally on branch `main`, but no GitHub repository or remote exists yet.

Exact Part 1 implementation commit: **pending until public GitHub publication and final report-link completion**.

Submission details: **pending instructor-accessible repository links and course-site upload**.

## Implementation

The Vue frontend accepts a full or partial hotel name, calls FastAPI through the Vite `/api` proxy, and presents loading, error, empty, and results states. FastAPI validates the query and returns JSON from a Python data layer. The data layer reads only the supplied `hotels.csv` and `trips.csv`, joins them on `hotel_id`, and derives nights and estimated stay price for the table. `users.csv` and `bookings.csv` remain preserved and unused; Part 2 behavior is not implemented.

## Verification

On September 11, 2026:

- Backend pytest: `9 passed` in `0.50s`; two upstream FastAPI/Starlette test-client deprecation warnings were reported.
- Frontend Oxlint: passed with no findings.
- Frontend ESLint: passed with no findings.
- Frontend production build: passed with Vite 8.3.0 and 12 transformed modules.
- API health check: expected and observed HTTP 200 with `{"status":"ok"}`.
- Successful API search for `Harbor`: expected and observed two stays, `T001` and `T009`.
- No-results API search for `Ocean Palace`: expected and observed HTTP 200 with zero stays.
- Successful browser search: expected and observed Harbor Lantern Hotel with two offered stays in a clearly labeled table. [View the successful-search screenshot](screenshots/hotel-search-harbor-results.png).
- No-results browser search: expected and observed a clear no-results message with no stale rows. [View the no-results screenshot](screenshots/hotel-search-no-results.png).
- Empty browser search: expected and observed useful guidance to enter a hotel name.
- Browser console: no application warnings or errors observed.
- Narrow viewport: the form, status, and horizontally scrollable table remained readable and usable at `390 × 844`.
- Cleanup: only task-owned service processes were stopped; ports 8000 and 5173 were released.

Detailed commands and evidence are recorded in [`docs/evidence.md`](docs/evidence.md).

## Project context and next steps

Project context: [`README.md`](README.md), [`AGENTS.md`](AGENTS.md), [`docs/design.md`](docs/design.md), [`docs/verification.md`](docs/verification.md), [`prompts/README.md`](prompts/README.md), and [`handoffs/current.md`](handoffs/current.md).

The remaining Part 1 work is public GitHub publication, insertion of the accessible repository URL and exact implementation commit above, final link verification, and course-site upload. Part 2 booking, history, SQLite, and CRUD remain intentionally deferred.

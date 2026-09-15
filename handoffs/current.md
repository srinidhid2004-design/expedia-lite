# Current handoff

Updated: 2026-09-15

## Orientation

Expedia Lite is a FastAPI, Vue 3, and SQLite course application. Part 1 remains preserved on `main`; Part 2 work is currently on `feature/part-2-sqlite-crud`. Read [`../README.md`](../README.md), follow [`../AGENTS.md`](../AGENTS.md), and use [`../docs/verification.md`](../docs/verification.md) for repeatable checks.

## What exists

- The unmodified instructor data pack is under `data/`.
- SQLite is created locally and seeded once from all four CSVs. A stored seed marker prevents reloads and duplicate starter rows on restart.
- Hotel search now reads a SQLite join while preserving Part 1 partial, case-insensitive behavior.
- FastAPI exposes health, hotel search, demo traveler, booking-history, create-booking, cancel-booking, and delete-booking routes under `/api`.
- Vue exposes the full required flow: select a demo traveler, search stays, create a booking, read history, cancel while retaining the row, and delete a test booking.
- New booking IDs use a persistent counter and are not reused after deletion.
- The generated database, virtual environment, dependency directory, and build output are ignored.
- No dependency declaration or instructor data file changed for Part 2.

## Verification state

On 2026-09-15:

- Standard-library SQLite 3.50.4 was confirmed with the project virtual-environment interpreter; no dependency installation was needed.
- Backend: 15 tests passed, covering search, API behavior, one-time seeding, unique IDs, CRUD, and persistence.
- Frontend: Oxlint passed, ESLint passed, and the Vite production build passed.
- API: health passed; matching and no-results searches passed through the frontend proxy.
- Browser: U006 started with no bookings; B007 was created, survived a browser refresh, was cancelled and retained, then deleted. B008 was created and remained after both services restarted.
- After restart, SQLite held 8 hotels, 12 trips, 6 users, and 7 current bookings; `seeded` remained `1`, the next booking number remained `9`, and B008 remained confirmed.
- Empty-input and no-results guidance passed, the interface remained usable in the narrow in-app browser, and the browser console contained no application errors.
- Browser evidence is stored under [`../screenshots/`](../screenshots/).
- Only the task-owned verification services were stopped; ports 8000 and 5173 are released.

Detailed commands and observed results are in [`../docs/evidence.md`](../docs/evidence.md).

## Remaining work

- The user completed the manual Visual Studio Code scan and browser demonstration and approved Part 2 on `feature/part-2-sqlite-crud`.
- Part 2 changes are ready for the reviewed feature commit and remain unmerged and unpushed at this point in the checkpoint.
- The exact reviewed Part 2 implementation commit, merge commit, and immutable public screenshot links remain pending.
- The existing public repository still reflects the submitted Part 1 checkpoint until review and publication are authorized.
- Two upstream FastAPI/Starlette test-client deprecation warnings remain; no dependency change is required for passing checks.

## Next task

Create the reviewed feature-branch commit, merge it into `main` without rewriting the Part 1 history, run the combined verification, finalize public report links, and publish the authorized commits.

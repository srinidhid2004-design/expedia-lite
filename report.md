# Expedia Lite — Part 2

## Repository and commit

Public repository: [srinidhid2004-design/expedia-lite](https://github.com/srinidhid2004-design/expedia-lite).

Preserved Part 1 implementation commit: [`0c1666d2bb03fdefda55ccf3b905d80801d78d5f`](https://github.com/srinidhid2004-design/expedia-lite/commit/0c1666d2bb03fdefda55ccf3b905d80801d78d5f).

Reviewed Part 2 implementation commit: pending the authorized feature commit and merge. Manual review is complete; Part 2 has not yet been merged into `main` or published.

## Implementation

The Vue 3 frontend keeps the Part 1 hotel search and adds a demo-traveler selector, booking actions on offered stays, and persistent booking history. Its API service sends all search and booking requests through the Vite `/api` proxy. FastAPI validates the requests and delegates work to typed Python search and booking modules.

On first use, the database layer creates SQLite tables and imports the instructor-provided hotels, trips, users, and starter bookings. It records a seed marker and the next booking number. All later application reads and writes use SQLite, so changes survive browser and service restarts without duplicating starter rows. New bookings preserve the supplied relationships and receive unique IDs; cancelling retains a row with `cancelled` status, while deletion removes a test record.

## Verification

On September 15, 2026:

- Backend pytest: 15 tests passed, including search, API validation, one-time seed counts, CRUD, persistent changes, deleted-record non-restoration, and non-reused booking IDs.
- Frontend Oxlint: passed with no findings.
- Frontend ESLint: passed with no findings.
- Frontend production build: passed with Vite 8.3.0 and 12 transformed modules.
- API health check: expected and observed HTTP 200 with `{"status":"ok"}`.
- Successful API search for `Harbor`: expected and observed two stays, `T001` and `T009`.
- No-results API search for `Ocean Palace`: expected and observed HTTP 200 with zero stays.
- Create/read browser check — Action: selected U006, searched `Harbor`, and chose an offered stay. Expected result: a unique confirmed booking appears in U006’s history. Observed result: B007 appeared as confirmed and remained after a browser refresh. Evidence: [`screenshots/part-2-booking-created.png`](screenshots/part-2-booking-created.png).
- Cancel browser check — Action: cancelled B007. Expected result: the booking remains in history with cancelled status. Observed result: B007 remained and displayed `cancelled`. Evidence: [`screenshots/part-2-booking-cancelled.png`](screenshots/part-2-booking-cancelled.png).
- Delete browser check — Action: deleted the B007 test booking. Expected result: the row disappears from U006’s history. Observed result: U006 returned to an empty history.
- Restart-persistence check — Action: created B008 for U006, stopped and restarted both task-owned services, reloaded the browser, and selected U006. Expected result: B008 remains without duplicate starter data. Observed result: B008 remained confirmed; SQLite still contained 8 hotels, 12 trips, 6 users, and 7 current bookings, with `seeded=1` and next booking number `9`. Evidence: [`screenshots/part-2-booking-after-restart.png`](screenshots/part-2-booking-after-restart.png).
- Empty and no-results searches displayed useful guidance, the interface remained usable below its 720-pixel responsive breakpoint, and the browser console contained no application errors.
- Manual Visual Studio Code review and browser demonstration: completed and approved before the reviewed feature commit.

Detailed commands and evidence are recorded in [`docs/evidence.md`](docs/evidence.md).

## Project context and next steps

Project context: [`README.md`](README.md), [`AGENTS.md`](AGENTS.md), [`docs/design.md`](docs/design.md), [`docs/evidence.md`](docs/evidence.md), [`prompts/README.md`](prompts/README.md), and [`handoffs/current.md`](handoffs/current.md).

Genuine limitations remain: demo identities are not authenticated, prices are fictional estimates without taxes or fees, inventory is not real, and the local SQLite database is designed for a single classroom application rather than production deployment. Two upstream FastAPI/Starlette test-client deprecation warnings remain.

Next steps are the reviewed feature-branch commit, merge to `main` without rewriting the Part 1 checkpoint, final verification, public push, immutable report links, and course-site submission. The manual review is complete; commit, merge, and publication remain pending at this point in the checkpoint.

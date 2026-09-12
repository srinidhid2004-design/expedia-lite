# Expedia Lite — Part 1

## Repository and commit

Public repository: [srinidhid2004-design/expedia-lite](https://github.com/srinidhid2004-design/expedia-lite).

Reviewed Part 1 implementation commit: [`0c1666d2bb03fdefda55ccf3b905d80801d78d5f`](https://github.com/srinidhid2004-design/expedia-lite/commit/0c1666d2bb03fdefda55ccf3b905d80801d78d5f).

Submission status: the public repository and Part 1 report are prepared; course-site upload remains pending.

## Implementation

The Vue 3 frontend uses the Composition API to accept a full or partial hotel name and send a GET request through the Vite `/api` proxy. FastAPI validates the query and delegates CSV parsing and search to a typed Python data layer. That layer reads only the instructor-provided `hotels.csv` and `trips.csv`, joins them on `hotel_id`, derives nights and estimated stay prices, and returns matching stays for the frontend table. `users.csv` and `bookings.csv` remain preserved and unused.

## Verification

On September 11, 2026:

- Backend pytest: `9 passed` in `0.50s`; two upstream FastAPI/Starlette test-client deprecation warnings were reported.
- Frontend Oxlint: passed with no findings.
- Frontend ESLint: passed with no findings.
- Frontend production build: passed with Vite 8.3.0 and 12 transformed modules.
- API health check: expected and observed HTTP 200 with `{"status":"ok"}`.
- Successful API search for `Harbor`: expected and observed two stays, `T001` and `T009`.
- No-results API search for `Ocean Palace`: expected and observed HTTP 200 with zero stays.
- Successful browser search — action: entered `Harbor` and submitted the hotel search; expected: Harbor Lantern Hotel with two offered stays in a clearly labeled table; observed: two rows for trips `T001` and `T009`, with the expected dates and prices. [View immutable successful-search evidence](https://github.com/srinidhid2004-design/expedia-lite/blob/0c1666d2bb03fdefda55ccf3b905d80801d78d5f/screenshots/hotel-search-harbor-results.png).
- No-results browser search — action: entered `Ocean Palace` and submitted the hotel search; expected: a clear no-results message with no stale rows; observed: “No hotel stays match ‘Ocean Palace’. Try another hotel name.” and no table rows. [View immutable no-results evidence](https://github.com/srinidhid2004-design/expedia-lite/blob/0c1666d2bb03fdefda55ccf3b905d80801d78d5f/screenshots/hotel-search-no-results.png).
- Empty browser search: expected and observed useful guidance to enter a hotel name.
- Browser console: no application warnings or errors observed.
- Narrow viewport: the form, status, and horizontally scrollable table remained readable and usable at `390 × 844`.
- Manual review: completed in Visual Studio Code; the reviewed Part 1 implementation was approved before the implementation commit.
- Cleanup: only task-owned service processes were stopped; ports 8000 and 5173 were released.

Detailed commands and evidence are recorded in [the public evidence log](https://github.com/srinidhid2004-design/expedia-lite/blob/main/docs/evidence.md).

## Project context and next steps

Project context: [README](https://github.com/srinidhid2004-design/expedia-lite/blob/main/README.md), [project rules](https://github.com/srinidhid2004-design/expedia-lite/blob/main/AGENTS.md), [design notes](https://github.com/srinidhid2004-design/expedia-lite/blob/main/docs/design.md), [evidence log](https://github.com/srinidhid2004-design/expedia-lite/blob/main/docs/evidence.md), [prompt record](https://github.com/srinidhid2004-design/expedia-lite/blob/main/prompts/README.md), and [current handoff](https://github.com/srinidhid2004-design/expedia-lite/blob/main/handoffs/current.md).

Genuine limitations remain: the application is intended for local development, reads the CSV files for search rather than using a database, and has no authentication, booking workflow, booking history, cancellation, CRUD, or persistence. Two upstream FastAPI/Starlette test-client deprecation warnings also remain. The course-site submission is still pending. Part 2 is the next development task and is explicitly not implemented in this Part 1 checkpoint.

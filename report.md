# Expedia Lite — Part 2

## Repository and commit

Public repository: [https://github.com/srinidhid2004-design/expedia-lite](https://github.com/srinidhid2004-design/expedia-lite).

Preserved Part 1 implementation commit: [`0c1666d2bb03fdefda55ccf3b905d80801d78d5f`](https://github.com/srinidhid2004-design/expedia-lite/commit/0c1666d2bb03fdefda55ccf3b905d80801d78d5f).

Reviewed Part 2 feature commit: [`5b329d4984caa1348af39c20d79e077420493c2c`](https://github.com/srinidhid2004-design/expedia-lite/commit/5b329d4984caa1348af39c20d79e077420493c2c).

Part 2 implementation merge commit: [`a98a9ccd1de2329d35b2924e2b1f121fe7359627`](https://github.com/srinidhid2004-design/expedia-lite/commit/a98a9ccd1de2329d35b2924e2b1f121fe7359627).

## Implementation

The Vue 3 frontend preserves the Part 1 partial, case-insensitive hotel search and adds a demo-traveler selector, booking actions on offered stays, and persistent booking history. The frontend API module sends search and booking requests through the Vite `/api` proxy. FastAPI validates those requests and delegates database and search rules to typed Python modules outside the route layer.

On first use, the backend creates a local SQLite database and seeds it once from all four instructor CSV files. A stored seed marker prevents duplicate starter rows. All later application reads and writes use SQLite, so booking changes survive browser reloads and backend restarts. Booking creation assigns a persistent, non-reused text ID; cancellation keeps the row with `cancelled` status; deletion removes the selected booking. The implementation intentionally has no authentication, payments, taxes, fees, or real inventory behavior.

## Verification

The user completed and approved a manual Visual Studio Code review and browser demonstration before the reviewed feature commit and merge.

- Automated checks — Action: ran the backend pytest suite through `backend/.venv`, Oxlint, ESLint, and the Vite production build after the merge. Expected result: every check passes without changing dependencies. Observed result: 15 backend tests passed with two upstream deprecation warnings; Oxlint and ESLint passed with no findings; Vite 8.3.0 transformed 12 modules and built successfully.
- Successful search — Action: searched for `Harbor`. Expected result: the case-insensitive partial-name search returns the offered Harbor Lantern Hotel stays. Observed result: the API and visible frontend returned T001 and T009 in a labeled results table.
- No-results search — Action: searched for `Ocean Palace`. Expected result: no stays are returned and clear guidance replaces stale results. Observed result: the API returned an empty list and the frontend displayed its no-results message.
- Create and read — Action: selected U006 and booked T001. Expected result: a new confirmed booking with a unique ID appears in U006's history. Observed result: B007 appeared as confirmed and remained after a browser reload. [View the creation screenshot](https://github.com/srinidhid2004-design/expedia-lite/blob/a98a9ccd1de2329d35b2924e2b1f121fe7359627/screenshots/part-2-booking-created.png).
- Cancel and retain — Action: cancelled B007. Expected result: B007 remains in history with `cancelled` status. Observed result: the row remained and displayed `cancelled`. [View the cancellation screenshot](https://github.com/srinidhid2004-design/expedia-lite/blob/a98a9ccd1de2329d35b2924e2b1f121fe7359627/screenshots/part-2-booking-cancelled.png).
- Delete — Action: created B008 as a separate disposable verification record and deleted it through the frontend. Expected result: B008 disappears while the cancelled B007 row remains. Observed result: B008 was absent and B007 remained cancelled.
- Restart persistence — Action: restarted the task-owned backend against the same disposable database, restarted the frontend, reloaded the visible app, and selected U006. Expected result: B007 remains cancelled, B008 remains absent, and starter data is not reseeded. Observed result: the UI showed only cancelled B007; SQLite contained 8 hotels, 12 trips, 6 users, and 7 bookings with `seeded=1` and `next_booking_number=9`. [View the restart screenshot](https://github.com/srinidhid2004-design/expedia-lite/blob/a98a9ccd1de2329d35b2924e2b1f121fe7359627/screenshots/part-2-booking-after-restart.png).
- Interface checks — Action: submitted an empty search, inspected a narrow viewport, and checked browser console errors after the workflow. Expected result: useful guidance, usable narrow-screen controls and tables, and no application errors. Observed result: all three checks passed.
- Cleanup — Action: stopped only the identified task-owned services and removed only the disposable verification database. Expected result: ports 8000 and 5173 are free and the real database is unchanged. Observed result: both ports were released; the disposable database was removed; `backend/expedia_lite.sqlite3` retained SHA-256 `E492632B5C26A5CF0A9EE1EE5E2D8C37108118EDA4B7C074A1EE3074B8F9E17B`.

Detailed commands and results are in [docs/evidence.md](https://github.com/srinidhid2004-design/expedia-lite/blob/main/docs/evidence.md).

## Project context and next steps

Project records: [README.md](https://github.com/srinidhid2004-design/expedia-lite/blob/main/README.md), [AGENTS.md](https://github.com/srinidhid2004-design/expedia-lite/blob/main/AGENTS.md), [docs/design.md](https://github.com/srinidhid2004-design/expedia-lite/blob/main/docs/design.md), [docs/evidence.md](https://github.com/srinidhid2004-design/expedia-lite/blob/main/docs/evidence.md), [prompts/README.md](https://github.com/srinidhid2004-design/expedia-lite/blob/main/prompts/README.md), and [handoffs/current.md](https://github.com/srinidhid2004-design/expedia-lite/blob/main/handoffs/current.md).

Genuine limitations remain: demo identities are not authenticated, prices are fictional estimates without taxes or fees, inventory is not real, and the local SQLite database is intended for a single classroom application rather than production deployment. Two upstream FastAPI/Starlette test-client deprecation warnings remain.

Assignment Part 2 is implemented, reviewed, merged, and published. The remaining next step is the user's course-site submission; this project did not access or submit anything to the course site.

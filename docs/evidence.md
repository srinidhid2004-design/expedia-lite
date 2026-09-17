# Evidence log

## 2026-09-11 — Part 1 implementation and recovery verification

Related prompts: [`01-assignment-intake.md`](../prompts/01-assignment-intake.md), [`02-environment-setup.md`](../prompts/02-environment-setup.md), [`03-part-1-csv-search.md`](../prompts/03-part-1-csv-search.md), [`04-part-1-verification.md`](../prompts/04-part-1-verification.md), and [`05-recovery-and-verification.md`](../prompts/05-recovery-and-verification.md).

The initial workflow should have stopped after summarizing acceptance criteria and uncertain decisions, but it continued through data extraction, scaffolding, implementation, dependency installation, and partial verification. Those actions occurred in one continuous, unapproved overrun—not as separate approved milestones. A subsequent audit recorded the full state. This recovery checkpoint provisionally accepted the existing Part 1 application and authorized verification evidence, screenshots, and documentation updates only.

### Scope and environment checks

- Command: `.\backend\.venv\Scripts\python.exe -c "import sys; print(f'executable={sys.executable}'); print(f'prefix={sys.prefix}'); print(f'base_prefix={sys.base_prefix}'); print(f'version={sys.version.split()[0]}')"`.
  - Observed executable: `C:\Users\srini\Documents\ChatGPT\expedia-lite\backend\.venv\Scripts\python.exe`.
  - Observed environment prefix: `C:\Users\srini\Documents\ChatGPT\expedia-lite\backend\.venv`.
  - Observed Python version: `3.14.7`.
- Command: `rg -n --glob '!**/.venv/**' --glob '!**/node_modules/**' --glob '!**/dist/**' "\.csv" backend/app frontend/src`.
  - Observed application references only to `hotels.csv` and `trips.csv`, both in `backend/app/travel_data.py`.
- Command: `rg -ni --glob '!**/.venv/**' --glob '!**/node_modules/**' --glob '!**/dist/**' "users\.csv|bookings\.csv|sqlite|\bcrud\b|booking|cancellation|cancelled|deletion|\bdelete\b|authentication|persistence|persisted|persisting" backend frontend/src`.
  - Observed no matches.
- Command: `Get-NetTCPConnection -State Listen -LocalPort <port>` for ports 8000 and 5173, followed by `Get-CimInstance Win32_Process -Filter "ProcessId=<owning PID>"`.
  - Ports 8000 and 5173 were initially owned by the exact task processes recorded in the audit: Uvicorn PID `6728` and Vite PID `29700`. Their command lines referenced this project, so the existing services were reused.

### Automated checks

Backend command, run from `backend/`:

```powershell
.\.venv\Scripts\python.exe -B -m pytest .\tests -q -p no:cacheprovider
```

Observed: `9 passed, 2 warnings in 0.50s`. Both warnings are upstream deprecations from FastAPI/Starlette's test client: `httpx` use is deprecated in favor of `httpx2`, and the `anyio.abc.BlockingPortal` alias is deprecated.

Frontend commands, run from `frontend/`:

```powershell
.\node_modules\.bin\oxlint.cmd .
.\node_modules\.bin\eslint.cmd .
npm run build
```

Observed: Oxlint passed with no findings; ESLint passed with no findings; Vite 8.3.0 transformed 12 modules and completed the production build in `179ms`.

### API checks through the frontend proxy

Commands:

```powershell
Invoke-WebRequest -Uri 'http://127.0.0.1:5173/api/health' -UseBasicParsing
Invoke-WebRequest -Uri 'http://127.0.0.1:5173/api/hotels/search?name=Harbor' -UseBasicParsing
Invoke-WebRequest -Uri 'http://127.0.0.1:5173/api/hotels/search?name=Ocean%20Palace' -UseBasicParsing
```

- `GET http://127.0.0.1:5173/api/health` — expected HTTP 200 with `{"status":"ok"}`; observed HTTP 200 with `{"status":"ok"}`.
- `GET http://127.0.0.1:5173/api/hotels/search?name=Harbor` — expected two matching stays; observed HTTP 200 with count `2` and trip IDs `T001,T009`.
- `GET http://127.0.0.1:5173/api/hotels/search?name=Ocean%20Palace` — expected no matches; observed HTTP 200 with count `0` and an empty results list.

### Visible browser checks

- Searched `Harbor`; observed the status “2 stays found,” a clearly labeled eight-column table, Harbor Lantern Hotel, and offered stays `T001` and `T009` with the expected dates, nights, $150 nightly rates, and $300 stay prices. Evidence: [`hotel-search-harbor-results.png`](../screenshots/hotel-search-harbor-results.png).
- Searched `Ocean Palace`; observed “No hotel stays match ‘Ocean Palace’. Try another hotel name.” and no stale table rows. Evidence: [`hotel-search-no-results.png`](../screenshots/hotel-search-no-results.png).
- Submitted an empty hotel-name field; observed “Enter a hotel name to search.”
- Checked browser console warnings and errors after the interactions; observed an empty log.
- Applied a temporary `390 × 844` viewport. The form stacked vertically, status remained readable, and the results table remained available through horizontal scrolling. Restored the normal viewport afterward.

### Cleanup

- Reconfirmed port ownership immediately before cleanup: port 8000 belonged to task PID `6728`, and port 5173 belonged to task PID `29700`.
- Sent Ctrl+C only to the original backend and frontend service sessions.
- Confirmed that both complete task process trees exited and ports `8000` and `5173` were released.
- No application source, dependency declaration, instructor data, Git state, or Part 2 behavior changed during this recovery checkpoint.

## 2026-09-11 — Manual Visual Studio Code review

Related prompt: [`06-part-1-local-commit.md`](../prompts/06-part-1-local-commit.md).

The user confirmed that the manual review in Visual Studio Code was complete and approved the current Part 1 implementation for the reviewed local commit.

## 2026-09-11 — Public GitHub publication

Related prompt: [`07-github-publication.md`](../prompts/07-github-publication.md).

- Public repository: [https://github.com/srinidhid2004-design/expedia-lite](https://github.com/srinidhid2004-design/expedia-lite).
- Reviewed implementation commit: [`0c1666d2bb03fdefda55ccf3b905d80801d78d5f`](https://github.com/srinidhid2004-design/expedia-lite/commit/0c1666d2bb03fdefda55ccf3b905d80801d78d5f).
- The repository was created public and empty in the GitHub browser, without a generated README, `.gitignore`, license, template, issue, project, release, or additional branch.
- Command: `git push -u origin main`.
  - Observed: the reviewed `main` implementation commit was pushed successfully, and local `main` began tracking `origin/main`.
- An unauthenticated public check confirmed that the repository and implementation commit were accessible before the submission documentation was finalized.

## 2026-09-15 — Part 2 implementation verification

Related prompt: [`08-part-2-implementation.md`](../prompts/08-part-2-implementation.md).

The user authorized Part 2 after the Part 1 submission. Work began on `feature/part-2-sqlite-crud` so the published Part 1 checkpoint remains preserved on `main`. No merge or push occurred during this implementation checkpoint.

### Scope, storage, and dependency checks

- Confirmed the backend interpreter as `C:\Users\srini\Documents\ChatGPT\expedia-lite\backend\.venv\Scripts\python.exe`.
- Confirmed Python’s standard-library `sqlite3` support with SQLite `3.50.4`; a temporary database row survived close and reopen. No dependency was installed or changed.
- Command: `rg -n --glob '!**/.venv/**' --glob '!**/node_modules/**' --glob '!**/dist/**' '\.csv' backend\app frontend\src`.
  - Observed: the only runtime CSV paths are the four one-time seed inputs in `backend/app/database.py`.
- Command: `git diff -- data`.
  - Observed: no instructor data change.
- Command: `git diff -- backend\requirements.txt frontend\package.json frontend\package-lock.json`.
  - Observed: no dependency declaration or lockfile change.

### Automated checks

Backend command, run from `backend/`:

```powershell
.\.venv\Scripts\python.exe -B -m pytest .\tests -q -p no:cacheprovider
```

Observed: `15 passed, 2 warnings in 2.17s`. The warnings are the same upstream FastAPI/Starlette test-client deprecations recorded for Part 1.

Frontend commands, run from `frontend/`:

```powershell
.\node_modules\.bin\oxlint.cmd .
.\node_modules\.bin\eslint.cmd .
npm run build
```

Observed: Oxlint passed with no findings; ESLint passed with no findings; Vite 8.3.0 transformed 12 modules and completed the production build in `247ms`.

### Services and API

- Ports 8000 and 5173 were free before service startup.
- Backend command from `backend/`: `.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`.
- Frontend command from `frontend/`: `npm run dev -- --host 127.0.0.1 --port 5173`.
- `GET http://127.0.0.1:8000/api/health` — expected and observed `{"status":"ok"}`.
- `GET http://127.0.0.1:5173/api/hotels/search?name=Harbor` — expected and observed count `2`, trip IDs `T001` and `T009`.
- `GET http://127.0.0.1:5173/api/hotels/search?name=Ocean%20Palace` — expected and observed count `0` with an empty results list.

### Visible browser CRUD checks

- Selected `Demo Traveler 6 (U006)`; expected an empty starter history and observed “Demo Traveler 6 has no bookings.”
- Searched `Harbor`; expected two offered stays and observed a labeled table containing T001 and T009.
- Created B007 from T001; expected a new unique confirmed booking and observed B007 in U006’s history. Refreshed the browser, reselected U006, and observed that B007 remained. Evidence: [`part-2-booking-created.png`](../screenshots/part-2-booking-created.png).
- Cancelled B007; expected the row to remain with cancelled status and observed “B007 was cancelled and remains in history” plus the `cancelled` status. Evidence: [`part-2-booking-cancelled.png`](../screenshots/part-2-booking-cancelled.png).
- Deleted the B007 test record; expected it to disappear and observed that U006 returned to no bookings.
- Created B008 from T009 for restart verification; expected a new ID rather than reuse of B007 and observed B008 confirmed.

### Restart persistence and one-time seed check

- Stopped only the backend and frontend service sessions started for this check and confirmed both ports were released.
- Restarted both services with the same commands, reloaded the browser, and selected U006.
- Expected B008 to survive and observed one confirmed U006 history row for B008/T009. Evidence: [`part-2-booking-after-restart.png`](../screenshots/part-2-booking-after-restart.png).
- SQLite query after restart observed table counts `{hotels: 8, trips: 12, users: 6, bookings: 7}`, `seeded=1`, `next_booking_number=9`, and B008 as `(B008, U006, T009, confirmed)`. The seven bookings equal the six starter rows minus deleted B007 plus retained B008; no starter rows were duplicated.
- Searched `Ocean Palace` and observed the clear no-results message. Submitted an empty field and observed “Enter a hotel name to search.”
- The visible in-app browser was narrower than the 720-pixel breakpoint; controls stacked correctly and both tables remained available through horizontal scrolling.
- Browser console error query after all interactions returned an empty list.

For final cleanup, port ownership was reconfirmed as task Uvicorn PID `33400` on 8000 and task Vite PID `34884` on 5173. Only their service sessions were stopped, and both ports were confirmed released. Manual Visual Studio Code review and merge/publication remain pending.

## 2026-09-15 — Part 2 manual review approval

Related prompt: [`09-part-2-review-merge-publication.md`](../prompts/09-part-2-review-merge-publication.md).

The user confirmed that the manual Visual Studio Code review and browser demonstration of Part 2 were complete and approved the implementation on `feature/part-2-sqlite-crud`. The pre-commit checkpoint reconfirmed 15 passing backend tests, passing Oxlint and ESLint checks, and a passing production build before the reviewed feature commit.

## 2026-09-17 — Part 2 merge and restart-recovery verification

Related prompt: [`09-part-2-review-merge-publication.md`](../prompts/09-part-2-review-merge-publication.md).

### Git checkpoints

- Preserved Part 1 implementation: `0c1666d2bb03fdefda55ccf3b905d80801d78d5f`.
- Reviewed Part 2 feature commit: `5b329d4984caa1348af39c20d79e077420493c2c` (`Complete Expedia Lite Part 2`).
- Normal non-fast-forward Part 2 merge commit on `main`: `a98a9ccd1de2329d35b2924e2b1f121fe7359627` (`Merge Expedia Lite Part 2`).
- The feature branch remains available. No amend, rebase, squash, force-push, remote change, or history rewrite occurred.

### Post-merge automated checks

Backend command, run from `backend/`:

```powershell
.\.venv\Scripts\python.exe -B -m pytest .\tests -q -p no:cacheprovider
```

Observed: `15 passed, 2 warnings in 2.63s`. The warnings are the previously recorded upstream FastAPI/Starlette test-client deprecations.

Frontend commands, run from `frontend/`:

```powershell
.\node_modules\.bin\oxlint.cmd .
.\node_modules\.bin\eslint.cmd .
npm run build
```

Observed: Oxlint passed with no findings; ESLint passed with no findings; Vite 8.3.0 transformed 12 modules and completed the production build in `239ms`.

### Disposable restart verification

- Real database preserved at `C:\Users\srini\Documents\ChatGPT\expedia-lite\backend\expedia_lite.sqlite3` with baseline and final SHA-256 `E492632B5C26A5CF0A9EE1EE5E2D8C37108118EDA4B7C074A1EE3074B8F9E17B`.
- Disposable database: `C:\Users\srini\Documents\ChatGPT\expedia-lite\backend\part2-final-verification.sqlite3`, ignored by `backend/*.sqlite3`.
- Before the interruption, B007 had been created and cancelled, then the separate B008 record had been created and deleted through the frontend.
- On recovery, a read-only SQLite query confirmed B007 as `(B007, U006, T001, cancelled)`, B008 absent, table counts `{hotels: 8, trips: 12, users: 6, bookings: 7}`, `seeded=1`, and `next_booking_number=9`.
- Port 8000 was still owned by the paused disposable verification backend, PID `39028`, whose full command line identified the project virtual environment, disposable database, loopback host, and port. Port 5173 was free. The existing backend was recovered, and only the missing frontend was started with `npm run dev -- --host 127.0.0.1 --port 5173 --strictPort`; its listener was task-owned Vite PID `22580`.
- The visible frontend was reloaded and U006 selected. Expected: B007 remains cancelled and B008 remains absent. Observed: the history showed exactly one row, cancelled B007/T001, and no B008 row.
- A second read-only database query observed the same counts and metadata: 8 hotels, 12 trips, 6 users, 7 bookings, `seeded=1`, and `next_booking_number=9`.
- Browser console errors after the restart workflow: none.
- A first recovery query attempt had a PowerShell quoting error and exited with a Python `SyntaxError` before opening or changing the database; the corrected read-only query produced the results above.

### Cleanup and publication record

- The frontend session was stopped with Ctrl+C. Immediately before stopping the remaining backend, its command line was rechecked and proved it was PID `39028` from this project using `part2-final-verification.sqlite3` on port 8000; only that process was stopped.
- Ports 8000 and 5173 were confirmed free.
- The disposable database path was resolved and matched the exact expected path before that one file was removed. The real database remained present with its baseline hash.
- Public repository: [https://github.com/srinidhid2004-design/expedia-lite](https://github.com/srinidhid2004-design/expedia-lite).
- The report uses immutable merge-commit URLs for the three Part 2 screenshots and public `main` links for the current project records.
- Course-site access and submission remain outside this checkpoint.

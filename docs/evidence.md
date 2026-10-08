# Evidence log

## 2026-09-11 — Part 1 implementation and recovery verification

Related prompts: [`01-assignment-intake.md`](../prompts/01-assignment-intake.md), [`02-environment-setup.md`](../prompts/02-environment-setup.md), [`03-part-1-csv-search.md`](../prompts/03-part-1-csv-search.md), [`04-part-1-verification.md`](../prompts/04-part-1-verification.md), and [`05-recovery-and-verification.md`](../prompts/05-recovery-and-verification.md).

The initial workflow should have stopped after summarizing acceptance criteria and uncertain decisions, but it continued through data extraction, scaffolding, implementation, dependency installation, and partial verification. Those actions occurred in one continuous, unapproved overrun—not as separate approved milestones. A subsequent audit recorded the full state. This recovery checkpoint provisionally accepted the existing Part 1 application and authorized verification evidence, screenshots, and documentation updates only.

### Scope and environment checks

- Command: `.\backend\.venv\Scripts\python.exe -c "import sys; print(f'executable={sys.executable}'); print(f'prefix={sys.prefix}'); print(f'base_prefix={sys.base_prefix}'); print(f'version={sys.version.split()[0]}')"`.
  - Observed executable: `backend/.venv/Scripts/python.exe`.
  - Observed environment prefix: `backend/.venv`.
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

- Confirmed the backend interpreter as `backend/.venv/Scripts/python.exe`.
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

For final cleanup, port ownership was reconfirmed as task Uvicorn PID `33400` on 8000 and task Vite PID `34884` on 5173. Only their service sessions were stopped, and both ports were confirmed released. At that checkpoint, manual Visual Studio Code review and merge/publication had not yet occurred; the later publication records supersede that state.

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

- Real database preserved at `backend/expedia_lite.sqlite3` with baseline and final SHA-256 `E492632B5C26A5CF0A9EE1EE5E2D8C37108118EDA4B7C074A1EE3074B8F9E17B`.
- Disposable database: `backend/part2-final-verification.sqlite3`, ignored by `backend/*.sqlite3`.
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

## 2026-10-07 — First public API activity

Related prompt: [`10-first-public-api-activity.md`](../prompts/10-first-public-api-activity.md).

The user completed a visible browser review and approved the first-public-API milestone before it was committed on `feature/assignment-2-part-1`. This checkpoint records only the completed Geoapify ZIP-location activity; Assignment 2 hotel discovery, map, shortlist, and chatbot behavior have not been added by this milestone.

### Configuration and security

- The project-root `.env` is ignored by Git and is not tracked. A safe name-only check confirmed one `GEOAPIFY_API_KEY` setting without displaying its value or any `.env` contents.
- `backend/app/config.py` loads the project-root `.env` through an explicit path. `GET /api/health` reports only `key is configured` or `key is not configured`.
- Geoapify requests and the credential remain in the backend. A comparison against the configured value found no credential match in the intended tracked or untracked project files, and the frontend source contains no API key or `GEOAPIFY_API_KEY` reference.

### Implemented activity behavior

- `backend/app/location_controller.py` resolves a supplied ZIP through Geoapify forward geocoding, requires an exact matching U.S. postcode with valid coordinates, and distinguishes missing configuration, an unresolved ZIP, and provider failure without returning a provider URL, credential, or raw exception.
- The fixed classroom route `GET /api/demo/zip-location` continues to use `16802`.
- `GET /api/zip-location?postcode=...` accepts the ZIP as a string, requires exactly five ASCII digits, and therefore preserves leading zeros.
- The Vue panel provides a labeled text input, numeric keyboard hint, five-character limit, accessible instructions, loading and error feedback, and a labeled result table. It calls only the local `/api` route through the existing Vite proxy.

### Automated verification

Backend command, run from `backend/`:

```powershell
.\.venv\Scripts\python.exe -B -m pytest .\tests -q -p no:cacheprovider
```

Observed: `36 passed, 2 warnings in 2.05s`. The warnings are the previously documented upstream FastAPI/Starlette test-client deprecations. The suite includes mocked success for `16802`, leading-zero preservation, invalid input, mismatched or unresolved responses, missing configuration, and sanitized provider failure behavior.

Frontend commands, run from `frontend/`:

```powershell
.\node_modules\.bin\oxlint.cmd .
.\node_modules\.bin\eslint.cmd .
npm run build
```

Observed: Oxlint passed with no findings; ESLint passed with no findings; Vite 8.3.0 transformed 12 modules and completed the production build in `313ms`.

### Live API and browser verification

- `GET /api/health` returned application status plus `key is configured`, without returning the key.
- A live request to `GET /api/zip-location?postcode=16802` returned the sanitized location `16802`, `State College`, `US`, latitude `40.803167822`, and longitude `-77.861384958` on October 7, 2026.
- In the visible frontend, entering and submitting `16802` displayed those same values in the labeled ZIP code, locality, country, latitude, and longitude table. The input, submit button, and complete result table were arranged together for review.
- The existing hotel-name search still returned Harbor stays `T001` and `T009`.
- The browser console contained no application warnings or errors.
- The user subsequently confirmed that the ZIP-input and result-table milestone passed manual review.

## 2026-10-07 — Assignment 2 Part 1 AutoLoop verification

This checkpoint verified the approved ZIP-to-hotel discovery and synchronized
Leaflet map on `feature/assignment-2-part-1`. It used exactly one live hotel
search for ZIP `16802`. All failure and empty-result checks used labeled HTTP
mocks or the credential-free Places fixture and consumed no additional provider
quota.

### Automated checks

Backend command, run from `backend/`:

```powershell
.\.venv\Scripts\python.exe -B -m pytest .\tests -q -p no:cacheprovider
```

Expected: all postcode, discovery, route, Assignment 1 search, and booking tests
pass. Observed: **57 passed** with two previously documented upstream
FastAPI/Starlette test-client deprecation warnings.

Focused mock command, run from `backend/`:

```powershell
.\.venv\Scripts\python.exe -B -m pytest .\tests\test_hotel_discovery.py -q -p no:cacheprovider
```

Observed: **9 passed** in `0.45s`. These tests make no live provider request and
cover the credential-free success fixture, missing optional fields, successful
zero results, malformed data, timeout, provider failure, rate limiting, missing
configuration, and unresolved exact ZIP behavior.

Frontend and whitespace commands:

```powershell
.\node_modules\.bin\oxlint.cmd .
.\node_modules\.bin\eslint.cmd . --no-cache
npm run build
git diff --check
```

Observed: Oxlint and ESLint passed without findings; Vite `8.3.0` transformed
16 modules and completed the production build in `289ms`; `git diff --check`
exited `0` with no whitespace findings.

### Live ZIP 16802 comparison

Observation date: **October 7, 2026**. Live versus mocked label: **live**.

- Action: entered the string `16802` in the labeled ZIP input and submitted it
  once through the visible Vue interface.
- Expected: loading feedback; exact U.S. postcode resolution; a sanitized
  search center; and one bounded hotel collection used by both the list and
  map, without relying on a fixed count.
- Observed loading text: `Finding hotels within 5 km of ZIP 16802…`.
- Observed center: postcode `16802`, locality `State College`, country `US`,
  latitude `40.803167822`, longitude `-77.861384958`.
- Observed provider page: 20 hotel records on this request. This is a variable,
  capped provider page—not an assertion that future requests return 20 or that
  it is an exhaustive inventory.
- Comparison: the visible table contained 20 unique provider place IDs; the map
  contained 20 hotel markers; and the normalized hotel-name sets matched. A
  separate ZIP-center marker and the 5 km circle were also visible.
- The initial shared selection identified `Scholar Hotel State College` in the
  row and the marker title. Evidence:
  [`assignment-2-part-1-live-list-map.png`](../screenshots/assignment-2-part-1-live-list-map.png).

### Selection, accessibility, and responsive checks

- Action: focused the second list control and pressed Enter.
  - Expected: one shared selection updates the row, marker styling, title, and
    popup.
  - Observed: the selected row, selected marker title, and popup all identified
    `Hotel State College`; exactly one row and one marker were selected.
- Action: focused the marker titled `Nittany Lion Inn near ZIP 16802` and
  pressed Enter.
  - Expected: the matching list item becomes selected without a separate map
    selection state.
  - Observed: the selected marker, popup, and list row all identified
    `Nittany Lion Inn`; the marker exposed `role="button"` and `tabindex="0"`.
- Evidence:
  [`assignment-2-part-1-synchronized-selection.png`](../screenshots/assignment-2-part-1-synchronized-selection.png).
- At a temporary `390 × 844` viewport, the ZIP form and list/map area used one
  column, the map retained a `380px` height, the hotel table remained available
  through its own horizontal scroller, and selection remained visible. The
  viewport override was reset after the check.
- Attribution remained visibly rendered as `Leaflet | © OpenStreetMap
  contributors`.

### Distinct states and mocked outcomes

Live-versus-mocked label for every item below: **mocked or local validation;
no provider quota used**.

| State | Action or fixture | Expected result | Observed result |
| --- | --- | --- | --- |
| Invalid input | Submit local value `1680` | Exact five-digit guidance and no request | `Enter exactly five digits for a U.S. ZIP code.`; previous rows, markers, and map cleared |
| Unresolved ZIP | Mock exact-postcode lookup failure | Safe unresolved response; no substitute hotel search | Dedicated unresolved exception and HTTP `404` mapping passed |
| No nearby hotels | Mock valid empty FeatureCollection | Successful empty hotel response | HTTP `200`, count `0`, and empty hotel list passed |
| Provider failure | Mock timeout and HTTP failure | Safe service failure without raw exception or credentials | Dedicated provider failure checks passed |
| Malformed response | Mock invalid/non-usable provider data | Malformed response is not reported as an empty success | Dedicated malformed-response checks passed |
| Rate or quota failure | Mock HTTP `429` | Distinct retry-later response | Dedicated rate/quota exception and HTTP `429` mapping passed |

Representative local-validation evidence:
[`assignment-2-part-1-invalid-zip.png`](../screenshots/assignment-2-part-1-invalid-zip.png).

### Assignment 1 regression and credential checks

- Action: searched `Harbor` through the visible browser.
  - Expected: the existing Assignment 1 search returns `T001` and `T009`.
  - Observed: status `2 stays found for “Harbor”.`, two result rows, and trip
    IDs `T001` and `T009`.
- Current-page browser console: zero application errors and zero warnings.
- `.env` remained ignored and untracked. A value comparison performed without
  printing the configured value found zero matches in tracked files and saved
  screenshots.
- Frontend source and production output contained zero occurrences of the
  configured credential and zero `GEOAPIFY_API_KEY` or `apiKey` identifiers.
  No environment file appeared in the production build.

### Corrections and limitations

- No application source correction was required by this AutoLoop. All
  acceptance checks passed on the first application cycle.
- The in-app browser's tall-element screenshot capture can repeat content below
  the primary viewport when stitching the long 20-row table. The live center,
  first result rows, selected marker/popup, and visible attribution in the
  linked evidence remain unaltered; the live result count is also recorded
  independently above.
- Geoapify coverage and fields can change. The UI intentionally reports a
  bounded page of up to 20 provider records and does not claim prices, ratings,
  rooms, availability, bookability, or exhaustive inventory.

## 2026-10-07 — Assignment 2 Part 1 final documentation checkpoint

Related prompt records:

- [`11-assignment-2-research-and-mockup.md`](../prompts/11-assignment-2-research-and-mockup.md)
- [`12-leaflet-dependency-checkpoint.md`](../prompts/12-leaflet-dependency-checkpoint.md)
- [`13-hotel-discovery-backend.md`](../prompts/13-hotel-discovery-backend.md)
- [`14-hotel-discovery-route-and-list.md`](../prompts/14-hotel-discovery-route-and-list.md)
- [`15-leaflet-list-map-synchronization.md`](../prompts/15-leaflet-list-map-synchronization.md)
- [`16-assignment-2-part-1-verification.md`](../prompts/16-assignment-2-part-1-verification.md)
- [`17-assignment-2-part-1-documentation.md`](../prompts/17-assignment-2-part-1-documentation.md)

The user reported completing manual review of the working Assignment 2 Part 1 interface before this documentation-only checkpoint. No application source, tests, dependency declaration, instructor data, or generated runtime data was authorized to change.

### Final expected-versus-observed summary

| Action | Expected result | Observed result |
| --- | --- | --- |
| Submit live ZIP `16802` once on October 7, 2026 | Resolve only the exact U.S. postcode, show the sanitized center, and return a bounded provider page from a strict 5 km hotel search without assuming a fixed count | Resolved `16802`, State College, `US`, latitude `40.803167822`, longitude `-77.861384958`; the live response contained 20 usable records on that request, correctly described as variable and capped rather than exhaustive |
| Compare the live backend response with the visible UI | Search center matches; the list and map contain the same normalized hotels | Center values matched; 20 unique list IDs matched 20 hotel-marker IDs; the separate center marker and radius circle remained visible |
| Select hotels from the list and map | One shared place ID keeps row, marker, title, and popup synchronized in both directions | List selection identified the matching marker; marker selection identified and scrolled to the matching row; keyboard activation passed |
| Inspect provider-field handling | Optional fields are represented honestly and unsupported commercial claims are absent | Missing names use `Name unavailable`, missing addresses use `Address not provided`, and no price, rating, room, availability, or bookability claim is shown |
| Check failure and empty states without another live search | Invalid input, unresolved ZIP, no hotels, provider failure, malformed response, rate/quota failure, and missing configuration remain distinct | Local validation plus the credential-free fixture and mocks verified each state with safe feedback and no additional provider quota |
| Check map disclosure and responsive behavior | Attribution remains visible and the list/map stay usable at a narrow viewport | `Leaflet | © OpenStreetMap contributors` remained visible; the 390 × 844 check stacked content and retained an operable map and table scroller |
| Recheck Assignment 1 behavior and browser health | `Harbor` still returns T001 and T009 and the console has no application error | Both trip IDs were present; zero application errors and warnings were observed in the final page state |
| Run repeatable automated checks | Backend, mocked discovery, frontend lint/build, and whitespace checks pass | 57 backend tests passed; 9 focused mocked discovery tests passed; Oxlint, ESLint, Vite production build, and `git diff --check` passed; two known upstream test-client deprecation warnings were non-failing |

### Evidence artifacts

- Live center, list, map, and attribution: [`assignment-2-part-1-live-list-map.png`](../screenshots/assignment-2-part-1-live-list-map.png)
- Synchronized selection: [`assignment-2-part-1-synchronized-selection.png`](../screenshots/assignment-2-part-1-synchronized-selection.png)
- Representative invalid-input state: [`assignment-2-part-1-invalid-zip.png`](../screenshots/assignment-2-part-1-invalid-zip.png)

The in-app browser’s tall-element capture may repeat content below the primary evidence region when stitching the long result table. This is a screenshot artifact, not an application result. The primary center, list, selected marker or popup, and attribution evidence remains visible.

### Revised approach and review record

The initial classroom milestone used one fixed `Look up ZIP 16802` button. That screenshot was insufficient for the Assignment 2 Part 1 rubric because it did not demonstrate user-entered five-digit ZIP input or the final table/list-and-map workflow. The panel was revised, through separately reviewed checkpoints, to a labeled text input that preserves leading zeros, a semantic result table, nearby-hotel discovery, and a synchronized Leaflet map.

An early startup check also opened FastAPI’s root URL and received the expected `{"detail":"Not Found"}` response. The procedure was corrected to use `/api/health` on port 8000 for backend health and the Vite interface on port 5173 for the application page.

The user manually reviewed and approved the working Assignment 2 Part 1 interface. At this checkpoint, the assessed merge and live demo-video URL had not yet been supplied; the publication record below supersedes that earlier state.

### AI assistance disclosure

OpenAI Codex — GPT-5 assisted with research summarization, the early mockup, implementation planning, code generation, tests, debugging, verification, and documentation. The Codex interface did not expose a more specific internal snapshot identifier, so no version or model suffix is claimed. Human review and approval were performed at each milestone.

## 2026-10-07 — Assignment 2 Part 1 publication and demo completion

Related prompt: [`18-assignment-2-part-1-publication-finalization.md`](../prompts/18-assignment-2-part-1-publication-finalization.md).

- Public repository: [https://github.com/srinidhid2004-design/expedia-lite](https://github.com/srinidhid2004-design/expedia-lite).
- Assessed merge commit: [`6c0575d092ad677b3ec25a6bdaa10aa7739fad29`](https://github.com/srinidhid2004-design/expedia-lite/commit/6c0575d092ad677b3ec25a6bdaa10aa7739fad29), subject `Merge Assignment 2 Part 1`.
- Public demo video: [Expedia Lite — Assignment 2 Part 1 demonstration](https://drive.google.com/file/d/1HIHOgmqgaugYnmLFjktFhjwINth2j6fC/view?usp=sharing).
- The merge commit and repository artifacts were reachable from an unauthenticated GitHub view.
- The Google Drive link opened in an unauthenticated viewer, displayed the recording preview, and did not show a request-access gate.
- Public links were checked for the report, assessed commit, research note, early mockup, evidence log, three screenshots, prompt index, and project documentation.
- The report and linked project artifacts contain no configured credential or local `.env` contents. The early mockup labels its generic hotel names and addresses as illustrative provider-field placeholders; the implementation and evidence use only provider-returned or explicitly mocked/placeholder data and make no unsupported commercial claim.
- No application source, dependency declaration, instructor data, generated runtime data, or Canvas content was changed or accessed during this documentation-only finalization.

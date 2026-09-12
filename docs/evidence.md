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

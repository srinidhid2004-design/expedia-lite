# Current handoff

Updated: 2026-09-11

## Orientation

Expedia Lite is a FastAPI and Vue 3 Part 1 application for searching fictional hotel stays. Read [`../README.md`](../README.md), follow [`../AGENTS.md`](../AGENTS.md), and use [`../docs/verification.md`](../docs/verification.md) for repeatable checks.

## What exists

- The unmodified instructor data pack is under `data/`.
- The Python data layer reads only `hotels.csv` and `trips.csv`, joins them on `hotel_id`, derives nights and price, and performs case-insensitive partial hotel-name search.
- FastAPI exposes `/api/health` and `/api/hotels/search?name=...`.
- Vue provides labeled hotel-name search, loading/error/empty feedback, and a clearly labeled results table through a narrow Vite `/api` proxy.
- Backend data/API tests and frontend lint/build tooling are configured.
- `users.csv` and `bookings.csv` are preserved but unused. SQLite, booking, history, CRUD, authentication, and persistence behavior are intentionally absent.

## Verification state

On 2026-09-11, the recovery checkpoint passed:

- Confirmed `backend/.venv` as Python 3.14.7 and the interpreter used for backend checks.
- Confirmed application CSV references are limited to `hotels.csv` and `trips.csv`; the Part 2 source scan returned no matches.
- Backend: `9 passed` with two upstream FastAPI/Starlette test-client deprecation warnings.
- Frontend: Oxlint passed, ESLint passed, and Vite 8.3.0 built 12 modules successfully.
- API: health passed; `Harbor` returned `T001` and `T009`; `Ocean Palace` returned zero rows.
- Browser: matching, no-results, and empty-input states passed; the console had no warnings/errors; the `390 × 844` responsive check passed.
- Screenshots are stored under [`../screenshots/`](../screenshots/).
- The task-owned backend and frontend process trees were stopped; ports 8000 and 5173 are released.

Full evidence, including the original stop-boundary mistake, is in [`../docs/evidence.md`](../docs/evidence.md).

## Remaining work

- The manual Visual Studio Code review is complete, and the current Part 1 implementation is approved.
- Git is initialized on branch `main`. Before this local-commit checkpoint, `HEAD` was unborn and no commit, remote, or push existed.
- The reviewed local Part 1 commit is complete; no GitHub remote is configured and nothing has been pushed.
- `report.md` still needs an accessible public GitHub repository URL and the exact Part 1 implementation commit during the publication checkpoint.
- Submission to the course site remains pending.
- The two upstream test-client deprecation warnings remain; no dependency change is authorized or required for the passing Part 1 checks.

## Next task

Publish the reviewed `main` branch to a public GitHub repository, then complete and verify the repository URL and exact implementation-commit link in `report.md` before submission.

# Assignment 2 verification

Run checks from the project root without installing or upgrading dependencies. Use `backend/.venv` for every backend command. Do not display `.env`, an API key, or a provider URL that contains credentials.

## Automated checks

```powershell
cd backend
.\.venv\Scripts\python.exe -B -m pytest .\tests -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pytest .\tests\test_hotel_discovery.py -q -p no:cacheprovider

cd ..\frontend
node --test .\tests\travelApi.test.js
.\node_modules\.bin\oxlint.cmd .
.\node_modules\.bin\eslint.cmd . --no-cache
npm run build

cd ..
git diff --check
```

Expected:

- the complete backend suite passes, including preserved Assignment 1 behavior;
- temporary-database tests pass for repeat saves, non-overwriting demo nights, ZIP-scoped retrieval, transactional removal, rollback after failure, and safe route errors;
- the three request-layer tests prove saved matches stop the workflow, successful empty local results permit provider fallback, and local failures prohibit provider fallback;
- the focused discovery suite uses mocks or the credential-free fixture and passes success, missing optional fields, zero results, malformed data, timeout/provider failure, rate limiting, missing configuration, and unresolved exact ZIP cases;
- Oxlint and ESLint report no findings;
- Vite builds ignored output under `frontend/dist/`; and
- the working diff has no whitespace errors.

The current local-storage checkpoint produced 69 passing backend tests and three passing local-first request tests. Two upstream FastAPI/Starlette test-client deprecation warnings were non-failing.

## Local API-hotel persistence check

Use a temporary database for automated mutation checks. For manual review, use the ignored `backend/expedia_lite.sqlite3` file and test records that you are prepared to remove through the interface; never edit Assignment 1 rows manually.

1. Search a ZIP with no saved associations. In the Network panel, expect `GET /api/hotels/saved` to complete successfully with zero matches before `GET /api/hotels/nearby` begins.
2. Select `Add to Local` on one API result. Expect backend success before the button becomes disabled or the row is marked saved.
3. Confirm five dates—October 10 through October 14, 2026—appear with `$100.00` and 20 rooms, all labeled simulated classroom data.
4. Search the same ZIP again or refresh and repeat the search. Expect the saved subset from `GET /api/hotels/saved`; the provider endpoint must not be requested.
5. Confirm the saved subset is labeled `Saved locally` and explicitly says it is not a complete inventory.
6. Use `Remove from Local`. Expect the row and marker to change only after backend success. Confirm that only its saved hotel, ZIP associations, and five demo rows were removed.
7. Repeat with two saved hotels sharing one ZIP. Removing one must preserve the other hotel and the still-used ZIP context.

For a controlled failure, use the temporary-database rollback test rather than altering the project database. The test installs a temporary trigger that aborts the hotel-row deletion after child-row deletes begin; the transaction must roll back so the hotel, association, and all five nights remain.

## Configuration and credential checks

Confirm by filename and Git metadata—not by printing contents—that the project-root `.env` is ignored and untracked. Confirm frontend source and built output contain neither `GEOAPIFY_API_KEY` nor a backend credential. `GET /api/health` may report only `key is configured` or `key is not configured`; it must never include the value.

Do not paste the credential into a shell command, log, screenshot, report, or test fixture. The fixture at `backend/tests/fixtures/geoapify_places_hotels.json` must remain labeled and credential-free.

## Services

Check ports 8000 and 5173 and inspect each listener’s PID and full command line before reusing, restarting, or stopping it. Preserve unrelated processes.

Start FastAPI when no healthy project-owned backend is available:

```powershell
cd backend
.\.venv\Scripts\python.exe -B -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Start Vue when no project-owned frontend is available:

```powershell
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Use `http://127.0.0.1:8000/api/health` for backend health and `http://127.0.0.1:5173/` for the application. An HTTP 404 at the FastAPI root `/` is expected and is not an application failure.

## Live ZIP and hotel check

Use one explicit live search for `16802`; provider data is variable, so never require a fixed hotel count.

1. Request `GET http://127.0.0.1:8000/api/hotels/nearby?postcode=16802` once and retain only its sanitized response.
2. Enter `16802` in the visible Vue form and submit.
3. Expect exact-postcode resolution, loading feedback, the same sanitized search center, and a bounded result statement for a 5 km radius and limit of 20.
4. Compare the backend hotel IDs with the visible table and hotel-marker IDs. Expect one list row and one hotel marker for every normalized result, plus a distinct center marker and radius circle.
5. Select a hotel from the list. Expect the matching marker to become visibly selected and identified.
6. Select a different marker. Expect the matching list row to become visibly selected and identified.
7. Operate a list selection by keyboard and confirm meaningful marker titles or labels.
8. Confirm `Leaflet | © OpenStreetMap contributors` and the Geoapify attribution remain visible.
9. At a narrow viewport, confirm the form, list, and map remain readable and operable.
10. Confirm the browser console has no application errors.

Record the observation date, sanitized center, observed variable hotel count, list count, marker count, and selected provider identity. Do not record the key or raw provider request URL.

## Mocked state checks

Use the automated mocks or fixed fixture—not additional live quota—to verify:

| State | Expected result |
| --- | --- |
| Invalid ZIP | Five-digit guidance; stale list, markers, and selection clear. |
| Unresolved exact ZIP | Safe 404-style feedback; no substitute location search. |
| No nearby hotels | Successful empty response; accepted center remains and no hotel markers appear. |
| Provider timeout/failure | Safe service feedback distinct from an empty result. |
| Malformed provider response | Safe malformed/provider failure, not a false zero-result success. |
| Rate or quota limit | Distinct retry-later response and HTTP 429 mapping. |
| Missing configuration | Safe unavailable/configuration response without exposing a value. |
| Saved local matches | Display only the stored subset and do not request the provider endpoint. |
| Empty local lookup | Proceed to the existing provider search. |
| Local database failure | Show a safe local error and do not request the provider endpoint. |
| Repeated save | Keep one hotel, one ZIP association, and five dates without overwriting stored demo values. |
| Remove failure | Show useful feedback and leave database/UI saved state unchanged. |

Restore normal behavior after any browser-level mock.

## Assignment 1 regression

Through the visible frontend, search for `Harbor`. Expect two existing stay rows with trip IDs `T001` and `T009`. Confirm the booking controls and history still load. When full booking CRUD is in scope, follow the existing create/read/cancel-retain/delete and restart-persistence procedure recorded in `docs/evidence.md`; use a disposable ignored database and never alter instructor CSV files.

## Evidence and cleanup

Save only credential-free screenshots under project-root `screenshots/`:

- `assignment-2-part-1-live-list-map.png`
- `assignment-2-part-1-synchronized-selection.png`
- `assignment-2-part-1-invalid-zip.png`
- `local-hotel-storage-manual-rate-edit.png`

Record each action, expected result, observed result, live-versus-mocked label, correction, and limitation in `docs/evidence.md`. Unless the user asks to keep the app running, stop only service processes whose command lines prove they belong to this project and confirm the relevant ports are released.

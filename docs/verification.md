# Assignment 2 verification

Run checks from the project root without installing or upgrading dependencies. Use `backend/.venv` for every backend command. Do not display `.env`, an API key, or a provider URL that contains credentials.

## Automated checks

```powershell
cd backend
.\.venv\Scripts\python.exe -B -m pytest .\tests -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pytest .\tests\test_hotel_discovery.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pytest .\tests\test_chatbot_route.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pytest .\tests\test_gemini_rag.py .\tests\test_chatbot_retrieval.py -q -p no:cacheprovider

cd ..\frontend
node --test .\tests\travelApi.test.js .\tests\chatbotApi.test.js
.\node_modules\.bin\oxlint.cmd .
.\node_modules\.bin\eslint.cmd . --no-cache
npm run build

cd ..
git diff --check
```

Expected:

- the complete backend suite passes, including preserved Assignment 1 behavior;
- chatbot route, RAG, and retrieval tests use temporary databases, injected
  fake credentials, fixed fixtures, and HTTPX mock transports only;
- successful nonempty chatbot retrieval uses exactly two mocked provider
  requests, while invalid/configuration cases use zero and rejected SQL,
  no-match, and database failures stop after one;
- Request 1 uses Gemini schema-constrained JSON with required `sql` and
  `parameters` plus optional intent; independent exact-field, type, size,
  parameter, SQL, and read-only retrieval validation still applies;
- Request 2 uses separate schema-constrained JSON with required answer, row
  references, and explanation plus optional limitation; independent grounding
  and row-reference validation still applies;
- fixed malformed/schema-invalid fixtures cover missing and unknown fields,
  unsafe parameter types, malformed JSON, top-level arrays, oversized output,
  empty candidates, and safety blocks; each Request 1 failure stops without SQL
  execution or Request 2;
- `POST /api/chatbot/query` accepts only `question`, preserves safe rejected-SQL
  trace evidence, returns no credentials or internal prompts, and maps provider,
  database, malformed-output, no-match, and grounding outcomes distinctly;
- temporary-database tests pass for repeat saves, non-overwriting demo nights, ZIP-scoped retrieval, transactional removal, rollback after failure, and safe route errors;
- the three request-layer tests prove saved matches stop the workflow, successful empty local results permit provider fallback, and local failures prohibit provider fallback;
- chatbot request-layer tests use stubbed `fetch` only, send exactly
  `{ "question": "..." }`, preserve stable success, no-match, and rejected-SQL
  traces, and keep every defined configuration/provider failure distinct;
- the focused discovery suite uses mocks or the credential-free fixture and passes success, missing optional fields, zero results, malformed data, timeout/provider failure, rate limiting, missing configuration, and unresolved exact ZIP cases;
- Oxlint and ESLint report no findings;
- Vite builds ignored output under `frontend/dist/`; and
- the working diff has no whitespace errors.

The current local-storage checkpoint produced 69 passing backend tests and three passing local-first request tests. Two upstream FastAPI/Starlette test-client deprecation warnings were non-failing.

## Fixed mocked chatbot negative cases

Run these commands exactly. They use fixed credential-free Gemini fixtures,
fake keys, `httpx.MockTransport`, stubbed frontend `fetch`, and temporary SQLite
databases. They must not read the project `.env`, contact any provider, or open
`backend/expedia_lite.sqlite3`.

```powershell
cd backend
.\.venv\Scripts\python.exe -B -m pytest .\tests\test_gemini_rag.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pytest .\tests\test_chatbot_retrieval.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pytest .\tests\test_chatbot_route.py -q -p no:cacheprovider

cd ..\frontend
node --test .\tests\chatbotApi.test.js

cd ..
git diff --check
```

For `no_match_sql`, expect one mocked provider request, zero retrieved rows,
`no_match`, no Request 2, no answer/explanation/references/limitation, and an
identical pre/post temporary-database snapshot. For `mutation_sql`, expect one
mocked provider request, `rejected_sql`, no Request 2, no records or generated
answer, visible unexecuted-query labeling, and an identical snapshot. The RAG
test snapshot combines a whole-file SHA-256 with counts for all four allowed
local-hotel tables and an unrelated `users` table.

## Mocked Part 2 chatbot route check

All checks in this section are mocked. They must not read the project-root
`.env`, use a real Gemini credential, contact Gemini, or open
`backend/expedia_lite.sqlite3`.

Send only this request shape to a test application configured with a temporary
database and injected RAG service:

```json
{"question":"Which saved hotel has simulated rooms for the requested dates?"}
```

The stable response includes `outcome`, the bounded question, fixed model ID,
safe proposed SQL and bound-parameter display values when available, bounded
columns and rows, grounded answer fields, and the simulated-classroom-data
notice. It excludes credentials, authorization headers, provider bodies,
system prompts, environment contents, database paths, stack traces, and
unrelated records.

Expected outcome/status mapping:

| Outcome | HTTP status |
| --- | ---: |
| `success`, `no_match` | 200 |
| `invalid_question` | 400; malformed or extra request fields are sanitized as 422 |
| `rejected_sql` | 422 |
| `quota_failure`, `rate_limit_failure` | 429 |
| `database_failure` | 500 |
| `authentication_failure`, `permission_failure`, `invalid_request`, `provider_failure`, `safety_blocked`, `empty_response`, `malformed_response`, `grounding_failure` | 502 |
| `missing_configuration` | 503 |
| `timeout` | 504 |

Requests containing browser-controlled `model`, `endpoint`, `api_key`, `sql`,
`database_path`, `prompt`, or `provider` fields must fail validation before the
RAG service is called.

## Vue chatbot interface check

Run `node --test .\tests\travelApi.test.js .\tests\chatbotApi.test.js` from
`frontend/`. These framework-free tests stub `fetch`; they never read `.env`,
use a real credential, or contact Gemini. Confirm the request body contains
only `question`, and that defined non-2xx responses retain their safe trace.

With a mocked backend response, inspect the visible chatbot at 390 × 844 and a
desktop viewport:

1. Confirm the labeled textarea, visible example question, character bound,
   submit action, and simulated-classroom-data notice are present.
2. Submit by keyboard and confirm repeat submission is disabled while the
   concise loading status is announced.
3. Confirm a new request clears stale answer, error, SQL, and record state while
   preserving the entered question.
4. For `success`, confirm the answer and trace show the exact returned model ID,
   SQL, safe parameters, record column/row order, explanation, row references,
   and limitation.
5. For `no_match`, confirm explicit no-match/insufficient-data feedback rather
   than a provider or database error.
6. For `rejected_sql`, confirm the proposed SQL remains visible as rejection
   evidence and is explicitly labeled not executed.
7. Confirm `invalid_question`, `missing_configuration`, authentication,
   permission, quota, rate-limit, timeout, provider, malformed-response,
   database, and grounding failures each have distinct text and are never
   described as an empty successful search.
8. Confirm wide SQL and record tables scroll inside the panel, visible focus is
   retained, and no result relies on color alone.
9. Confirm the existing ZIP/list/map, local save/remove, hotel search, booking,
   and history sections remain present and operational.

Do not use a live model for these repeatable checks. Three controlled Nemotron
attempts stopped at malformed Request 1 output; each skipped Request 2 and
executed no SQL. Those failures are retained as revised-approach evidence. One
separately authorized bounded Gemini flow subsequently completed both requests,
validated the proposed SQL, retrieved both saved classroom hotels, and returned
a grounded answer. Do not repeat that live check without new authorization;
continue to use the fixed mocks for repeatable verification.

The approved current runtime-database file SHA-256 is
`6ec793f68ae34af67927f81199ab68653a7a6c1c47be2f687deed75e4ae572b3`.
Verify it only with read-only file hashing. A `mode=ro`, `query_only` canonical
snapshot over sorted rows in `saved_hotels`, `saved_search_contexts`,
`saved_hotel_zip_associations`, and `demo_hotel_nights` has logical SHA-256
`698d758b3b0201ab9941f2ac90b7e208e0661881f7f132cbc3948f4440c3da27`.
That latter value is a historical logical/snapshot baseline, not the expected
current SQLite file hash. Do not claim a proven cause for the byte-level change.

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

# Expedia Lite

Expedia Lite is a Vue 3, FastAPI, and SQLite course project. The preserved Assignment 1 application searches instructor-provided hotel stays and supports simulated booking history, cancellation, deletion, and one-time SQLite seeding. Assignment 2 Part 1 adds a backend-only Geoapify workflow that resolves an exact five-digit U.S. ZIP code, requests a bounded page of hotels inside a 5 km circle, and presents the same normalized results in a selectable list and Leaflet map. The current in-class checkpoint adds local-first API-hotel saving, dated simulated rates and room counts, and transactional removal.

Geoapify results are discovery information only. They do not establish price, rating, room availability, bookability, or an exhaustive hotel inventory.

## Project structure

```text
backend/app/                           FastAPI, SQLite, geocoding, and discovery logic
backend/app/saved_hotel_data.py        Typed local API-hotel persistence operations
backend/tests/                         Mocked provider, route, persistence, and API tests
data/                                  Unmodified instructor-provided data pack
frontend/src/                          Vue interface, API service, and Leaflet component
docs/assignment-2-part-1-research.md   Primary-source research and decisions
docs/assignment-2-part-1-mockup.svg    Approved early annotated wireframe
docs/design.md                         MVC responsibilities and request flows
docs/verification.md                   Repeatable Assignment 2 Part 1 checks
docs/evidence.md                       Expected-versus-observed evidence
handoffs/current.md                    Current state, limitations, and next task
prompts/                               Selected project instruction records
screenshots/                           Credential-free browser evidence
report.md                              Assignment 2 Part 1 submission report
```

Project rules are in [`AGENTS.md`](AGENTS.md). The active continuation notes are in [`handoffs/current.md`](handoffs/current.md).

## Requirements

- Python 3.10 or newer
- Node.js `^22.18.0 || >=24.12.0`
- npm
- A Geoapify API key for live ZIP and hotel discovery

The verified environment used Python 3.14.7, SQLite 3.50.4, Node.js 24.20.0, npm 11.19.0, and Leaflet 1.9.4. Python dependencies are declared in `backend/requirements.txt`; frontend dependencies are declared and locked in `frontend/package.json` and `frontend/package-lock.json`.

## Setup

Run these commands in PowerShell from the project root:

```powershell
python -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt

cd frontend
npm install
cd ..
```

Dependencies remain inside the project. Do not commit `backend/.venv`, `frontend/node_modules`, `frontend/dist`, generated SQLite databases, caches, or environment files.

### Safe backend configuration

Create a project-root `.env` file beside `backend/` and `frontend/`:

```dotenv
GEOAPIFY_API_KEY=your-key-here
```

The checked-in `.gitignore` excludes `.env` and `.env.*` while allowing a future key-free `.env.example`. Never put the key in Vue source, a `VITE_` variable, screenshots, logs, test fixtures, documentation, or Git.

`backend/app/config.py` loads the project-root `.env` through an explicit path. `GET /api/health` reports only whether the key is configured; it never returns the value. Restart FastAPI after creating or editing `.env`. The Vue development server does not need a restart for a backend-only configuration change.

## Run the application

Start FastAPI from the project root:

```powershell
cd backend
.\.venv\Scripts\python.exe -B -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal, start Vue:

```powershell
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open `http://127.0.0.1:5173/`. The FastAPI root at `http://127.0.0.1:8000/` has no application page; an HTTP 404 there is expected. Use `http://127.0.0.1:8000/api/health` for backend health. Vite forwards browser requests under `/api` to FastAPI on port 8000.

The first Assignment 1 data request creates and seeds `backend/expedia_lite.sqlite3`; later starts reuse it. Additive `CREATE TABLE IF NOT EXISTS` migrations add the local API-hotel tables without replacing or reseeding that file. The traveler selector represents fictional demo identities only. There is no authentication, payment, or real reservation system.

## Hotel discovery and map

Enter exactly five digits in the nearby-hotel form. The ZIP remains a string so leading zeros survive validation. Vue first requests saved hotels associated with that exact ZIP. A successful local response with matches is displayed immediately and does not consume provider quota. Only a successful empty local response proceeds to the preserved provider workflow. A local database failure is shown and does not fall through to Geoapify.

The provider workflow:

1. resolves only the exact requested U.S. postcode through Geoapify geocoding;
2. uses the returned longitude and latitude as the center of a 5,000-meter Geoapify Places circle;
3. requests category `accommodation.hotel` with a proximity bias and limit of 20;
4. normalizes only usable provider IDs, coordinates, optional names, optional addresses, and valid distances; and
5. returns a sanitized search center and bounded hotel collection to Vue.

Vue renders one result collection in both the table and the Leaflet map. A shared provider place ID synchronizes list and marker selection in both directions. The search center and 5 km circle are visually distinct from hotel markers. Missing names appear as `Name unavailable`; missing addresses appear as `Address not provided`. OpenStreetMap Standard tiles are used for the low-volume classroom demonstration, with Leaflet and `© OpenStreetMap contributors` attribution kept visible. Geoapify attribution appears beside the result summary.

### Local API-hotel storage

`Add to Local` sends only the displayed provider-supported hotel fields and current verified ZIP context to FastAPI. Provider IDs are stored exactly and remain the unique hotel key. ZIP centers are stored separately and associated with hotels through a composite-key table. Saving is idempotent: repeat saves do not duplicate hotels, ZIP associations, or dated rows and do not overwrite existing demo values.

Each newly saved hotel receives five `demo_hotel_nights` rows for October 10–14, 2026. Their default nightly rate is 10,000 cents and their default room count is 20. These values are **simulated classroom data**, not Geoapify prices, availability, or real inventory. Saved results display the five dated values and explain that the saved subset is not a complete hotel inventory.

`Remove from Local` deletes only the selected hotel, its ZIP associations, and its demo-night rows in one SQLite transaction. Other saved hotels, shared ZIP context still in use, Assignment 1 records, and provider-search behavior remain unchanged. Saved state is read from FastAPI by provider ID on every ZIP search, including after a browser refresh.

## API summary

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Return application health and key-configuration status without returning the key. |
| `GET` | `/api/demo/zip-location` | Preserve the fixed classroom demonstration for ZIP `16802`. |
| `GET` | `/api/zip-location?postcode=16802` | Validate and resolve one exact five-digit U.S. ZIP string. |
| `GET` | `/api/hotels/nearby?postcode=16802` | Return the verified center and up to 20 normalized hotels within 5 km. |
| `GET` | `/api/hotels/saved?postcode=16802` | Return the saved local subset for an exact ZIP plus backend-derived saved provider IDs. |
| `POST` | `/api/hotels/saved` | Idempotently save one provider hotel, its ZIP context, and five simulated classroom nights. |
| `DELETE` | `/api/hotels/saved?hotel_id=...` | Transactionally remove one saved hotel, its associations, and its demo nights. |
| `GET` | `/api/hotels/search?name=Harbor` | Preserve the case-insensitive Assignment 1 hotel-name search. |
| `GET` | `/api/users` | List fictional demo travelers. |
| `GET` | `/api/bookings?user_id=U001` | Read one traveler’s booking history. |
| `POST` | `/api/bookings` | Create a simulated confirmed booking. |
| `PATCH` | `/api/bookings/{booking_id}/cancel` | Retain a booking and mark it cancelled. |
| `DELETE` | `/api/bookings/{booking_id}` | Permanently delete a test booking. |

Invalid ZIP input, unresolved ZIPs, missing configuration, provider failures, malformed responses, rate/quota failures, and successful zero-hotel responses remain distinct. Safe responses do not expose provider URLs, raw exceptions, or credentials.

Local database failure is also distinct: it stops the local-first workflow and never triggers a provider request. Local saved matches are labeled `Saved locally`; fallback provider records are labeled `API results`.

## Checks

Follow [`docs/verification.md`](docs/verification.md) for the complete repeatable workflow. Core checks are:

```powershell
cd backend
.\.venv\Scripts\python.exe -B -m pytest .\tests -q -p no:cacheprovider

cd ..\frontend
node --test .\tests\travelApi.test.js
.\node_modules\.bin\oxlint.cmd .
.\node_modules\.bin\eslint.cmd . --no-cache
npm run build

cd ..
git diff --check
```

The current local-storage checkpoint passed 69 backend tests, three dependency-free local-first request tests, Oxlint, ESLint, and the production build. See [`docs/verification.md`](docs/verification.md) for the repeatable local save/remove procedure and [`docs/evidence.md`](docs/evidence.md) for the published Assignment 2 Part 1 record and current manual local-storage evidence.

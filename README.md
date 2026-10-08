# Expedia Lite

Expedia Lite is a Vue 3, FastAPI, and SQLite course project. The preserved Assignment 1 application searches instructor-provided hotel stays and supports simulated booking history, cancellation, deletion, and one-time SQLite seeding. Assignment 2 Part 1 adds a backend-only Geoapify workflow that resolves an exact five-digit U.S. ZIP code, requests a bounded page of hotels inside a 5 km circle, and presents the same normalized results in a selectable list and Leaflet map.

Geoapify results are discovery information only. They do not establish price, rating, room availability, bookability, or an exhaustive hotel inventory.

## Project structure

```text
backend/app/                           FastAPI, SQLite, geocoding, and discovery logic
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

The first Assignment 1 data request creates and seeds `backend/expedia_lite.sqlite3`; later starts reuse it. The traveler selector represents fictional demo identities only. There is no authentication, payment, or real reservation system.

## Hotel discovery and map

Enter exactly five digits in the nearby-hotel form. The ZIP remains a string so leading zeros survive validation. The backend:

1. resolves only the exact requested U.S. postcode through Geoapify geocoding;
2. uses the returned longitude and latitude as the center of a 5,000-meter Geoapify Places circle;
3. requests category `accommodation.hotel` with a proximity bias and limit of 20;
4. normalizes only usable provider IDs, coordinates, optional names, optional addresses, and valid distances; and
5. returns a sanitized search center and bounded hotel collection to Vue.

Vue renders one result collection in both the table and the Leaflet map. A shared provider place ID synchronizes list and marker selection in both directions. The search center and 5 km circle are visually distinct from hotel markers. Missing names appear as `Name unavailable`; missing addresses appear as `Address not provided`. OpenStreetMap Standard tiles are used for the low-volume classroom demonstration, with Leaflet and `© OpenStreetMap contributors` attribution kept visible. Geoapify attribution appears beside the result summary.

## API summary

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Return application health and key-configuration status without returning the key. |
| `GET` | `/api/demo/zip-location` | Preserve the fixed classroom demonstration for ZIP `16802`. |
| `GET` | `/api/zip-location?postcode=16802` | Validate and resolve one exact five-digit U.S. ZIP string. |
| `GET` | `/api/hotels/nearby?postcode=16802` | Return the verified center and up to 20 normalized hotels within 5 km. |
| `GET` | `/api/hotels/search?name=Harbor` | Preserve the case-insensitive Assignment 1 hotel-name search. |
| `GET` | `/api/users` | List fictional demo travelers. |
| `GET` | `/api/bookings?user_id=U001` | Read one traveler’s booking history. |
| `POST` | `/api/bookings` | Create a simulated confirmed booking. |
| `PATCH` | `/api/bookings/{booking_id}/cancel` | Retain a booking and mark it cancelled. |
| `DELETE` | `/api/bookings/{booking_id}` | Permanently delete a test booking. |

Invalid ZIP input, unresolved ZIPs, missing configuration, provider failures, malformed responses, rate/quota failures, and successful zero-hotel responses remain distinct. Safe responses do not expose provider URLs, raw exceptions, or credentials.

## Checks

Follow [`docs/verification.md`](docs/verification.md) for the complete repeatable workflow. Core checks are:

```powershell
cd backend
.\.venv\Scripts\python.exe -B -m pytest .\tests -q -p no:cacheprovider

cd ..\frontend
.\node_modules\.bin\oxlint.cmd .
.\node_modules\.bin\eslint.cmd . --no-cache
npm run build

cd ..
git diff --check
```

The final recorded Assignment 2 Part 1 run passed 57 backend tests, a focused 9-test mocked discovery suite, Oxlint, ESLint, the production build, and the whitespace check. See [`docs/evidence.md`](docs/evidence.md) for live-versus-mocked labels, observed values, browser checks, and limitations.

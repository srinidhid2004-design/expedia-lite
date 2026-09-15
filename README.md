# Expedia Lite

Expedia Lite is a two-part course project built with Vue 3, FastAPI, and SQLite. Part 2 preserves the Part 1 hotel-name search and adds simulated booking, traveler booking history, cancellation, deletion, and persistent storage.

The application imports the instructor-provided hotel, trip, user, and booking CSV files into a local SQLite database on first use. That import happens only once. Later searches and booking changes read and write SQLite, so changes survive browser refreshes and application restarts without duplicating the starter records.

## Project structure

```text
backend/app/           FastAPI routes, SQLite setup, search, and booking rules
backend/tests/         Data, persistence, and API tests
data/                  Unmodified instructor-provided data pack
frontend/src/          Vue interface and API service
docs/design.md         Responsibilities, schema, and request flows
docs/verification.md   Repeatable Part 2 checks
docs/evidence.md       Completed-check evidence
handoffs/current.md    Current state and next task
prompts/               Selected project instruction record
screenshots/           Browser verification evidence
report.md              Part 2 report draft
```

Project-specific rules are in [`AGENTS.md`](AGENTS.md). The active continuation notes are in [`handoffs/current.md`](handoffs/current.md).

## Requirements

- Python 3.10 or newer with the standard-library `sqlite3` module
- Node.js `^22.18.0 || >=24.12.0`
- npm

The verified environment uses Python 3.14.7, SQLite 3.50.4, Node.js 24.20.0, and npm 11.19.0. Part 2 required no new dependency declaration or installation.

## Setup

Run these commands in PowerShell from the project root.

```powershell
python -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt

cd frontend
npm install
cd ..
```

Dependencies stay inside the project. Do not commit `backend/.venv`, `frontend/node_modules`, `frontend/dist`, or `backend/expedia_lite.sqlite3`.

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

Open `http://127.0.0.1:5173/`. Vite forwards `/api` requests to FastAPI on port 8000. The first search or booking-data request creates and seeds `backend/expedia_lite.sqlite3`; later starts reuse that database.

The traveler selector represents fictional demo identities only. There is no authentication, payment, or real reservation system.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Return `{"status":"ok"}`. |
| `GET` | `/api/hotels/search?name=Harbor` | Search hotel names using case-insensitive partial matching. |
| `GET` | `/api/users` | List demo travelers. |
| `GET` | `/api/bookings?user_id=U001` | Read one traveler’s booking history. |
| `POST` | `/api/bookings` | Create a confirmed booking from `user_id` and `trip_id`. |
| `PATCH` | `/api/bookings/{booking_id}/cancel` | Retain a booking and update its status to cancelled. |
| `DELETE` | `/api/bookings/{booking_id}` | Permanently delete a test booking. |

## Verify

Follow [`docs/verification.md`](docs/verification.md) for automated, API, browser CRUD, restart-persistence, and cleanup checks. Core automated checks are:

```powershell
cd backend
.\.venv\Scripts\python.exe -B -m pytest .\tests -q -p no:cacheprovider

cd ..\frontend
.\node_modules\.bin\oxlint.cmd .
.\node_modules\.bin\eslint.cmd .
npm run build
```

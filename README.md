# Expedia Lite

Expedia Lite is a small Part 1 course project for searching fictional hotel stays. A Vue 3 frontend sends a hotel-name query to FastAPI. The Python backend reads the instructor-provided `hotels.csv` and `trips.csv`, joins them on `hotel_id`, and returns matching stays with dates and derived prices.

Part 2 booking, history, SQLite, and CRUD behavior are intentionally not implemented.

## Project structure

```text
backend/app/           CSV search rules and FastAPI application
backend/tests/         Data and API tests
data/                  Unmodified instructor-provided data pack
frontend/src/          Vue interface and API service
docs/design.md         Responsibility and request-flow note
docs/verification.md   Repeatable Part 1 checks
docs/evidence.md       Completed-check evidence
handoffs/current.md    Current state and next task
prompts/               Selected project instruction record
report.md              Part 1 submission report
```

Project-specific rules are in [`AGENTS.md`](AGENTS.md). The active continuation notes are in [`handoffs/current.md`](handoffs/current.md).

## Requirements

- Python 3.10 or newer
- Node.js `^22.18.0 || >=24.12.0`
- npm

The initial verified environment used Python 3.14.7, Node.js 24.20.0, and npm 11.19.0.

## Setup

Run these commands in PowerShell from the project root.

```powershell
python -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt

cd frontend
npm install
cd ..
```

Dependencies stay inside the project. Do not commit `backend/.venv`, `frontend/node_modules`, or `frontend/dist`.

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

Open `http://127.0.0.1:5173/`. Vite forwards `/api` requests to FastAPI on port 8000.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Return `{"status":"ok"}`. |
| `GET` | `/api/hotels/search?name=Harbor` | Search hotel names using case-insensitive partial matching. |

A successful search returns the normalized query, result count, and joined hotel stays. A whitespace-only query returns HTTP 400. A valid query with no matches returns HTTP 200 with an empty `results` list.

## Verify

Follow [`docs/verification.md`](docs/verification.md) for the full process. Core automated checks are:

```powershell
cd backend
.\.venv\Scripts\python.exe -B -m pytest .\tests -q -p no:cacheprovider

cd ..\frontend
.\node_modules\.bin\oxlint.cmd .
.\node_modules\.bin\eslint.cmd .
npm run build
```

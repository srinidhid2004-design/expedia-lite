# Part 1 verification

Run checks from the project root. Verification must not install or upgrade dependencies.

## Automated checks

```powershell
cd backend
.\.venv\Scripts\python.exe -B -m pytest .\tests -q -p no:cacheprovider

cd ..\frontend
.\node_modules\.bin\oxlint.cmd .
.\node_modules\.bin\eslint.cmd .
npm run build
cd ..
```

Expected: backend tests pass, both frontend linters exit successfully without changing source, and Vite creates `frontend/dist/`.

## Services and API

Check ports 8000 and 5173 before starting anything. Do not stop an unrelated process.

Start FastAPI:

```powershell
cd backend
.\.venv\Scripts\python.exe -B -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Start Vue in a second terminal:

```powershell
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Verify requests through the frontend proxy:

- `GET http://127.0.0.1:5173/api/health` → HTTP 200 and `{"status":"ok"}`.
- `GET http://127.0.0.1:5173/api/hotels/search?name=Harbor` → HTTP 200, two rows, trip IDs `T001` and `T009`.
- `GET http://127.0.0.1:5173/api/hotels/search?name=Ocean%20Palace` → HTTP 200 and zero rows.

## Browser checks

1. Open `http://127.0.0.1:5173/`.
2. Search for `Harbor`; expect two table rows for Harbor Lantern Hotel, with clear dates and prices.
3. Search for `Ocean Palace`; expect a clear no-results message and no stale rows.
4. Submit an empty field; expect an instruction to enter a hotel name.
5. Confirm the page has no application error and remains readable at a narrow viewport.

Record expected and observed results in `docs/evidence.md` and store submission screenshots under `screenshots/`. Unless asked to keep the app running, stop only the service processes started for verification.

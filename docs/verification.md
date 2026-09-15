# Part 2 verification

Run checks from the project root. Verification must not install or upgrade dependencies. Use `backend/.venv` for every backend command.

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

Expected: backend search, seed, persistence, and CRUD tests pass; both frontend linters exit successfully without changing source; and Vite creates ignored output under `frontend/dist/`.

## Services and API

Check ports 8000 and 5173 before starting anything. Do not reuse or stop an unrelated process.

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

Verify through the frontend proxy:

- `GET http://127.0.0.1:5173/api/health` → HTTP 200 and `{"status":"ok"}`.
- `GET http://127.0.0.1:5173/api/hotels/search?name=Harbor` → two rows, trip IDs `T001` and `T009`.
- `GET http://127.0.0.1:5173/api/hotels/search?name=Ocean%20Palace` → zero rows.
- `GET http://127.0.0.1:5173/api/users` → six demo travelers.
- `GET http://127.0.0.1:5173/api/bookings?user_id=U001` → seeded booking history.

## Browser CRUD and persistence checks

1. Open `http://127.0.0.1:5173/` and select `Demo Traveler 6 (U006)`.
2. Search for `Harbor`; expect two offered stays in a clearly labeled table.
3. Book one offered stay; expect a new unique booking ID, confirmed status, and a matching row in U006’s history.
4. Refresh the browser; reselect U006 and confirm the new row remains.
5. Cancel that new booking; expect its status to change to cancelled while the row remains.
6. Delete that test booking; accept the deletion prompt and expect the row to disappear.
7. Create another test booking, then stop and restart only the task-owned backend and frontend process trees.
8. Reload the browser, reselect U006, and confirm the second new booking remains.
9. Confirm the database still contains 8 hotels, 12 trips, and 6 users, with only the expected booking-count changes. Restarting must not reload or duplicate starter records.
10. Search for `Ocean Palace`; expect a clear no-results message. Submit an empty search; expect guidance to enter a hotel name.
11. Confirm the page has no application error and remains readable and operable below the 720-pixel responsive breakpoint.

Record actions, expected results, and observed results in `docs/evidence.md`. Store review screenshots under the project-root `screenshots/` directory. Unless asked to keep the app running, stop only service processes started for the check and confirm ports 8000 and 5173 are released.

# Expedia Lite project rules

## Scope

- Complete Part 2 search, simulated booking, booking history, SQLite persistence, and booking CRUD only.
- Preserve the reviewed Part 1 implementation commit and develop Part 2 on a feature branch until manual review is complete.
- Keep backend code in `backend/`, frontend code in `frontend/`, and instructor data in `data/`.
- Treat the assignment and `data/README.md` as authoritative when reference material differs.
- Do not modify the instructor-provided data files.
- Do not add authentication, payments, taxes, fees, or real inventory behavior.

## Backend

- Use typed Python application code under `backend/app/`.
- Keep FastAPI routes under `/api` and database/search rules outside the web layer.
- Seed SQLite once from all four supplied CSV files. After seeding, application reads and writes must use SQLite rather than reload the CSV files.
- Join hotel, trip, user, and booking records using their supplied text IDs.
- Preserve seeded IDs and allocate unique IDs to new bookings without reusing deleted IDs.
- Cancelling a booking changes its status to `cancelled` and retains its row; deleting removes the row.
- Add or update pytest coverage when backend behavior changes.

## Frontend

- Use Vue 3 single-file components and the Composition API under `frontend/src/`.
- Keep requests separate from presentation code.
- Preserve labeled controls, status feedback, clear table headings, and usable narrow-screen behavior.
- Expose create, read, cancel/update, and delete booking actions through the frontend.

## Quality and continuity

- Follow CHECK → TAKE ACTION → VERIFY for dependency changes.
- Do not commit secrets, virtual environments, dependency directories, caches, build output, or the generated SQLite database.
- Keep `README.md`, `docs/`, `prompts/`, `report.md`, and `handoffs/current.md` consistent with verified behavior.
- Do not merge Part 2 into `main` until the user completes manual Visual Studio Code review.

## Course macros

### AutoLoop

When the user says **AutoLoop**, state the current acceptance check, run the smallest relevant check, and make no more than five narrowly scoped correction cycles. Stop if progress requires a new dependency, machine-level change, destructive action, unrelated process termination, or wider scope.

### SmokeTest

When the user says **Run the smoke test**, read `README.md` and `docs/verification.md`; run backend pytest, frontend lint, and the production build; check ports before starting services; verify health, matching and no-result searches, and booking CRUD through the frontend; restart only task-owned services to verify persistence and no reseeding; then stop only services started for the check and record the outcome in `docs/evidence.md`.

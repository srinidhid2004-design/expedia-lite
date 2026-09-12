# Expedia Lite project rules

## Scope

- Complete Part 1 CSV hotel search only. Do not implement Part 2 booking, history, SQLite, or CRUD behavior.
- Keep backend code in `backend/`, frontend code in `frontend/`, and instructor data in `data/`.
- Treat the assignment and `data/README.md` as authoritative when reference material differs.
- Do not modify the instructor-provided data files.

## Backend

- Use typed Python application code under `backend/app/`.
- Keep FastAPI routes under `/api` and CSV parsing/search rules outside the web layer.
- Part 1 application code may open only `data/hotels.csv` and `data/trips.csv`.
- Join hotel and trip records with `hotel_id`; keep IDs as text.
- Add or update pytest coverage when backend behavior changes.

## Frontend

- Use Vue 3 single-file components and the Composition API under `frontend/src/`.
- Keep requests separate from presentation code.
- Preserve labeled controls, status feedback, and clear table headings.

## Quality and continuity

- Follow CHECK → TAKE ACTION → VERIFY for dependency changes.
- Do not commit secrets, virtual environments, dependency directories, caches, or build output.
- Keep `README.md`, `docs/`, `prompts/`, `report.md`, and `handoffs/current.md` consistent with verified behavior.

## Course macros

### AutoLoop

When the user says **AutoLoop**, state the current acceptance check, run the smallest relevant check, and make no more than five narrowly scoped correction cycles. Stop if progress requires a new dependency, machine-level change, destructive action, unrelated process termination, or wider scope.

### SmokeTest

When the user says **Run the smoke test**, read `README.md` and `docs/verification.md`; run backend pytest, frontend lint, and the production build; check ports before starting services; verify the health route and one matching and one no-result hotel search through the frontend proxy; then operate the visible UI for the same two searches. Stop only services started for the check and record the outcome in `docs/evidence.md`.


# Expedia Lite project rules

## Scope and continuity

- Preserve the reviewed Assignment 1 hotel search, simulated booking, history, SQLite persistence, and booking CRUD behavior.
- Assignment 2 Part 1 adds nearby-hotel discovery for an exact five-digit U.S. ZIP code and a synchronized list/Leaflet map. Do not add the later shortlist, chatbot/RAG, authentication, payment, real inventory, taxes, or fees unless separately authorized.
- Develop Assignment 2 on `feature/assignment-2-part-1` until the user approves the assessed checkpoint and separately authorizes any merge or publication.
- Keep backend code in `backend/`, frontend code in `frontend/`, instructor data in `data/`, and browser evidence in the project-root `screenshots/` directory.
- Treat the assignment documents and `data/README.md` as authoritative. Do not modify instructor-provided CSV files.

## Assignment 2 MVC responsibilities

- **Model and provider layer:** typed Python modules under `backend/app/` own configuration, exact-postcode resolution, Geoapify Places requests, normalization, and safe provider-specific exceptions. The Geoapify credential remains backend-only.
- **Controller layer:** thin FastAPI routes under `/api` validate request input, call the provider-independent controllers/services, and map domain outcomes to safe HTTP responses. Routes must not return credentials, full provider URLs, or raw exception text.
- **Frontend request layer:** `frontend/src/services/` owns browser requests to local `/api` endpoints. Vue must never call Geoapify directly or receive the API key.
- **View layer:** Vue 3 Composition API components under `frontend/src/` own labeled controls, loading and error feedback, the hotel list, and Leaflet rendering. One shared provider place ID controls selection in both the list and map.
- The ZIP search must preserve leading zeros, require exactly five ASCII digits, resolve that exact U.S. postcode, and use the verified point as the center of a 5,000-meter Places circle.
- The normalized nearby-hotel result may contain only supported provider fields. Never invent a name, address, price, rating, availability, room count, or bookability claim.
- The bounded result page is not an exhaustive hotel inventory. Keep the selected provider and map attribution visible.

## Assignment 1 persistence responsibilities

- Seed SQLite once from all four supplied CSV files. After seeding, Assignment 1 search and booking reads/writes use SQLite rather than reloading CSV files.
- Join hotel, trip, user, and booking records using their supplied text IDs.
- Preserve seeded IDs and allocate unique booking IDs without reusing deleted IDs.
- Cancelling a booking changes its status to `cancelled` and retains its row; deleting removes the row.
- Generated SQLite databases are runtime data and must remain ignored.

## Verification and security rules

- Follow CHECK → TAKE ACTION → VERIFY for dependency changes. Do not install or upgrade a dependency without a separate approved dependency checkpoint.
- Use `backend/.venv` for backend checks. Run the complete pytest suite, Oxlint, ESLint, the production build, and `git diff --check` before an Assignment 2 review checkpoint.
- Mock Geoapify responses for automated success, missing optional fields, unresolved ZIP, zero hotels, malformed response, provider failure/timeout, rate/quota failure, and missing configuration. Limit live verification to an explicitly requested search and never rely on a fixed provider result count.
- In browser verification, compare the sanitized backend response with the visible center, list, map-marker count, and selected place identity. Check list-to-marker and marker-to-list selection, keyboard operation, narrow layout, attribution, console errors, and the existing Assignment 1 Harbor search.
- Before starting, reusing, restarting, or stopping services, inspect ports 8000 and 5173 and prove process ownership. Never stop an unrelated process.
- Never print, log, return, screenshot, stage, or commit `.env`, the API key, credentials, raw provider URLs containing credentials, virtual environments, dependency directories, caches, build output, or generated databases.
- Keep `README.md`, `docs/`, `prompts/`, `report.md`, and `handoffs/current.md` consistent with verified behavior. Distinguish live observations from mocked outcomes and record genuine limitations.

## Course macros

### AutoLoop

When the user says **AutoLoop**, state the current acceptance check, run the smallest relevant check, and make no more than five narrowly scoped correction cycles. Stop if progress requires a new dependency, machine-level change, destructive action, unrelated process termination, or wider scope.

### SmokeTest

When the user says **Run the smoke test**, read `README.md` and `docs/verification.md`; run backend pytest, Oxlint, ESLint, the production build, and `git diff --check`; check ports before starting services; verify health, the Assignment 2 ZIP/list/map workflow, synchronized selection, and the preserved Assignment 1 search and booking behavior. Restart only task-owned services when persistence is in scope, stop only services started for the check unless asked to leave them running, and record the outcome in `docs/evidence.md`.

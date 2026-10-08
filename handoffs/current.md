# Current handoff

Updated: 2026-10-08

## Orientation

Expedia Lite is on `assignment2_part2_in_class` at the reviewed Local Hotel Storage checkpoint. The published Assignment 1 and Assignment 2 Part 1 history on `main` remains preserved. This branch adds only the in-class SQLite save/list/remove workflow around the frozen ZIP discovery, list, and Leaflet map.

Read [`../README.md`](../README.md), follow [`../AGENTS.md`](../AGENTS.md), and use [`../docs/verification.md`](../docs/verification.md) and [`../docs/evidence.md`](../docs/evidence.md) for the current checks and evidence.

## What exists

- Additive, repeatable tables for unique provider hotels, verified ZIP contexts, hotel/ZIP associations, and dated demo nights.
- Typed backend save, ZIP-scoped list, and transactional remove operations plus thin FastAPI routes.
- Exact provider IDs, nullable provider names/addresses, valid coordinates, and five October 10–14, 2026 demo rows per newly saved hotel.
- Default values of 10,000 cents and 20 rooms clearly labeled simulated classroom data rather than API-supplied price or availability.
- Idempotent repeat saves that do not duplicate rows or overwrite stored nightly values.
- A frontend `Add to Local` and `Remove from Local` workflow whose saved state comes from FastAPI by provider ID.
- Local-first ZIP search: saved matches stop provider fallback; only a successful empty local result calls the preserved nearby-hotel endpoint; a local database failure stops with safe feedback.
- The same shared provider ID continues to synchronize list and Leaflet marker selection.
- Preserved Assignment 1 search, booking, history, cancellation, deletion, and one-time SQLite seeding.

## Verified state

- Complete backend suite: **69 passed** with two known, non-failing upstream test-client deprecation warnings.
- Local-first request tests: **3 passed**.
- Oxlint, ESLint, Vite production build, and `git diff --check`: passed.
- Temporary-database tests cover repeat saves, non-overwriting nights, ZIP-scoped lookup, successful transactional removal, forced rollback, and safe API failures.
- Live health and frontend startup passed; the preserved Assignment 1 `Harbor` search returned `T001` and `T009`.
- The user completed manual DB Browser and browser review on October 8, 2026 using ZIP `16802` and `Scholar Hotel State College`.
- The user reported exact hotel/context persistence, five default demo dates, refresh persistence, display of a manually changed 50-cent/10-room value, transactional removal, preservation of Assignment 1 data, and return to API results after removal.
- Evidence includes the saved-local edited-value view, the matching DB Browser demo-night rows, the empty `saved_hotels` view after removal, and the repeated ZIP search labeled `API results`. The evidence contains no API key or `.env` content.
- An initial read-only audit found a lingering saved record. After the user repeated removal, a new read-only audit confirmed 0 rows in `saved_hotels`, `saved_search_contexts`, `saved_hotel_zip_associations`, and `demo_hotel_nights`. Assignment 1 tables remained present with 8 hotels, 12 trips, 6 users, and 11 bookings. The earlier discrepancy is resolved.

## Current Git and runtime state

- Active branch: `assignment2_part2_in_class`.
- This handoff is part of the reviewed feature-branch checkpoint recorded by the commit subject `Complete local hotel storage activity`.
- Nothing from this checkpoint is merged into or pushed to `main`.
- `backend/expedia_lite.sqlite3` and `.env` remain ignored and untracked.
- Dependency directories and build output remain ignored and are not proposed for commit.
- The current runtime database contains no saved local hotel, context, association, or demo-night rows after the repeated removal. The ignored database is not part of the feature checkpoint.

## Limitations

- Saved results are a user-selected subset, not a complete hotel inventory.
- The dated rates and room counts are classroom simulation data only; no real price, availability, or bookability is claimed.
- Provider coverage and optional fields remain variable.
- The supplied screenshots capture the saved state, edited demo value, empty saved-hotel view, and provider fallback. The user-reported manual checks and supplementary read-only database counts are distinguished in the evidence log.
- No shortlist, chatbot, RAG, Nemotron, authentication, payment, taxes, fees, or other LLM behavior is implemented.
- Two upstream FastAPI/Starlette test-client deprecation warnings remain non-failing.

## Next task

The next task is a separately authorized review and merge decision for `assignment2_part2_in_class`. Do not merge, rebase, squash, amend, force-push, or modify `main` without that authorization. Chatbot, RAG, Nemotron, and other LLM behavior remain outside this checkpoint.

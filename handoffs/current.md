# Current handoff

Updated: 2026-10-27

## Orientation

Expedia Lite Assignment 2 Part 2 is complete on `main`, merged and published at assessed implementation commit `007aea0429ed3ce8abc0cfc4ff6e7401f24cb810` (`Merge Assignment 2 Part 2 RAG workflow`). The public demo is recorded, and the final submission report is complete. The active transport is Google Gemini API with exact model `gemini-3.5-flash-lite`; one explicitly authorized two-request live success and fixed mocked negative cases are verified. Three earlier controlled OpenRouter/Nemotron Request 1 failures remain documented as failed/revised evidence.

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
- Part 2 research covering the retired OpenRouter/Nemotron approach, the selected Gemini migration, SQLite read-only/authorizer controls, bounded SQL generation, accessible states, and grounded answers.
- A fixed-model, no-fallback, zero-retry Gemini GenerateContent flow using schema-constrained JSON for both requests, a thin `POST /api/chatbot/query` route, and the existing accessible Vue trace interface.
- Defense-in-depth read-only retrieval over only the four local API-hotel tables, with exact-key structured-output parsing, internal safe diagnostics, and unchanged SQL validation.
- The early chatbot mockup remains labeled as an early design artifact rather than implementation evidence.

## Verified state

- Most recent complete backend suite after the Gemini prompt correction: **196 passed** with two known, non-failing upstream test-client deprecation warnings.
- This negative-case checkpoint: **38** focused Gemini/RAG, **53** retrieval-security, and **30** chatbot-route tests passed; the route suite reported the same two known non-failing warnings.
- Framework-free chatbot request tests: **29 passed** after one test-only optional-chaining regex correction.
- Oxlint, ESLint, Vite production build, and `git diff --check`: passed.
- Final regression on October 27: **196 backend tests passed**, `pip check` reported no broken requirements, **29 chatbot request tests passed**, Oxlint and ESLint reported no findings, and the production build transformed 17 modules.
- Temporary-database tests cover repeat saves, non-overwriting nights, ZIP-scoped lookup, successful transactional removal, forced rollback, and safe API failures.
- Live health and frontend startup passed; the preserved Assignment 1 `Harbor` search returned `T001` and `T009`.
- The user completed manual DB Browser and browser review on October 8, 2026 using ZIP `16802` and `Scholar Hotel State College`.
- The user reported exact hotel/context persistence, five default demo dates, refresh persistence, display of a manually changed 50-cent/10-room value, transactional removal, preservation of Assignment 1 data, and return to API results after removal.
- Evidence includes the saved-local edited-value view, the matching DB Browser demo-night rows, the empty `saved_hotels` view after removal, and the repeated ZIP search labeled `API results`. The evidence contains no API key or `.env` content.
- An initial read-only audit found a lingering saved record. After the user repeated removal, a new read-only audit confirmed 0 rows in `saved_hotels`, `saved_search_contexts`, `saved_hotel_zip_associations`, and `demo_hotel_nights`. Assignment 1 tables remained present with 8 hotels, 12 trips, 6 users, and 11 bookings. The earlier discrepancy is resolved.
- Three controlled Nemotron chatbot attempts used the exact free model and returned a safe `malformed_response` before SQL validation. Each made only Request 1; Request 2 was skipped, no SQL executed, and no row changed. Credential-free screenshots and attempt records remain in the evidence log.
- One authorized live Gemini flow completed exactly two requests. Its validated SQL bound both occupied dates, the positive-availability threshold, and required-night count; retrieval returned only the two saved hotels at a simulated two-night total of `$200.00` each, excluded checkout October 12, and left the runtime database unchanged.
- Fixed mocked `no_match_sql` verification completed one provider request, returned zero rows and no generated answer, skipped Request 2, and preserved the temporary database.
- Fixed mocked `mutation_sql` verification reached the unchanged validator, returned `rejected_sql`, skipped execution and Request 2, produced no records or answer, and preserved the complete temporary-database snapshot.
- Gemini fixtures also cover schema-constrained success for both requests, optional intent/limitation, missing/unknown/unsafe fields, malformed and oversized responses, empty and safety-blocked candidates, provider error classes, grounding failures, and header-only key placement.

## Current Git and publication state

- Active branch: `main`.
- Assessed implementation merge: `007aea0429ed3ce8abc0cfc4ff6e7401f24cb810` (`Merge Assignment 2 Part 2 RAG workflow`).
- The feature history, screenshot-sanitization commit, and earlier Assignment 1 and Assignment 2 Part 1 history remain preserved through the normal two-parent merge.
- Public repository: <https://github.com/srinidhid2004-design/expedia-lite>.
- Public demo: <https://drive.google.com/file/d/1zhnSblbBfTXlPtfD9Oh8gHV-tCraqoQn/view?usp=sharing>.
- The final report identifies the assessed implementation commit even though a later documentation-only finalization commit follows it.
- `backend/expedia_lite.sqlite3` and `.env` remain ignored and untracked.
- Dependency directories and build output remain ignored and are not proposed for commit.
- The ignored runtime database currently contains 2 saved hotels, 1 search context, 2 ZIP associations, and 10 demo-night rows created through the authorized Add to Local workflow. Its approved current file SHA-256 is `6ec793f68ae34af67927f81199ab68653a7a6c1c47be2f687deed75e4ae572b3`; its sorted-row canonical logical digest is the historical snapshot value `698d758b3b0201ab9941f2ac90b7e208e0661881f7f132cbc3948f4440c3da27`. The reason for the byte-level transition is not proven. October 10 and 11 contain 10,000 cents and 20 rooms for both saved hotels.

## Limitations

- Saved results are a user-selected subset, not a complete hotel inventory.
- The dated rates and room counts are classroom simulation data only; no real price, availability, or bookability is claimed.
- Provider coverage and optional fields remain variable.
- The supplied screenshots capture the saved state, edited demo value, empty saved-hotel view, and provider fallback. The user-reported manual checks and supplementary read-only database counts are distinguished in the evidence log.
- No shortlist, authentication, payment, taxes, fees, or database-mutating chatbot behavior is implemented.
- Gemini structured-output enforcement does not replace backend SQL, parameter, retrieval, or grounding validation.
- Gemini free-tier availability and project limits remain external and variable. Unpaid-tier inputs/outputs may be used to improve Google products and may receive human review, so only non-confidential classroom content is permitted.
- One bounded live Gemini success is evidence for the tested classroom question only; it is not a guarantee of future free-tier availability or arbitrary-question behavior.
- Two upstream FastAPI/Starlette test-client deprecation warnings remain non-failing.

## Next task

Implementation, review, merge, publication, demo recording, and report finalization are complete. The remaining action is user-controlled course-site submission. Do not access or submit to Canvas on the user's behalf. Any future live Gemini request still requires separate explicit authorization and must retain exact model `gemini-3.5-flash-lite`, no fallback, and zero retries.

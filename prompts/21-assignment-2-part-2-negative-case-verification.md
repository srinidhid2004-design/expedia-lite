# 21 — Assignment 2 Part 2 negative-case verification

Verify the required chatbot negative cases using fixed labeled fixtures and
mocks only on `feature/assignment-2-part-2-rag`.

## Scope

- Use fake credentials, `httpx.MockTransport`, fixed credential-free Gemini
  JSON fixtures, stubbed frontend `fetch`, and temporary SQLite databases.
- Do not contact Gemini, OpenRouter, Geoapify, or another network service.
- Do not read the project `.env` or runtime SQLite database.
- Add only missing test assertions; do not change application behavior,
  dependencies, provider behavior, SQL validation, configuration, or fixtures.

## Required evidence

- `no_match_sql`: valid read-only proposal, zero rows, `no_match`, one provider
  request, no Request 2, no generated answer or invented facts, and identical
  pre/post temporary-database snapshots.
- `mutation_sql`: unchanged validator rejects the proposed mutation before
  execution, returns `rejected_sql`, makes one provider request and no Request
  2, returns no records or generated answer, and preserves every temporary
  table.
- Frontend parsing preserves exact safe messages and one-request counts. The
  existing Vue labels must distinguish no-match from provider/empty-response
  failures and identify rejected SQL as never executed.

## Verification and records

Run the focused Gemini/RAG, retrieval-security, chatbot-route, and framework-free
frontend chatbot tests plus `git diff --check`. After they pass, update
`docs/evidence.md`, `docs/verification.md`, and `handoffs/current.md`, clearly
distinguishing the previously authorized live Gemini success from these fixed
mocked negative cases. Do not stage, commit, merge, rebase, or push.

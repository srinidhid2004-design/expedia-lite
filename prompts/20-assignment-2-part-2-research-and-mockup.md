# 20 — Assignment 2 Part 2 RAG research and early mockup

## Approved selection

- Provider: OpenRouter
- Exact model: `nvidia/nemotron-3.5-lightning:free`

## Check

- Read the project rules, current documentation, and revised Assignment 2 Part 2 requirements.
- Research authoritative current sources for OpenRouter chat behavior and limits, SQLite read-only controls, bounded SQL generation, accessible chatbot states, and grounded answers.
- Preserve the reviewed local-storage foundation and all Assignment 1 and Assignment 2 Part 1 behavior.

## Take action

- Create the Part 2 research note and an accessible early chatbot mockup.
- Update project rules, design responsibilities, the handoff, and prompt index for the planned two-request RAG flow.
- Keep credentials/model calls backend-only and the remote model disconnected from SQLite.
- Permit only validated, bounded, read-only retrieval; the second request receives only the question and limited retrieved records.

## Boundaries

- Research and design only: no application code, dependency installation, `.env` change, model request, or database change.
- Do not commit or push.
- Stop for visual approval of the mockup.

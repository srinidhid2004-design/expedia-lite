# 10 — First public API activity

## Checkpoint purpose

Record and commit the manually approved in-class milestone that extends the fixed Geoapify ZIP demonstration into a user-entered five-digit ZIP lookup. Preserve every existing Assignment 1 search, booking, and SQLite behavior. Treat the attached Assignment 2 overview as future requirements context only.

## Required checks

- Review the complete working tree and confirm the changes belong to the first-public-API activity.
- Confirm the project-root `.env` is ignored and untracked without displaying its contents.
- Confirm no configured credential appears in intended project files.
- Run the backend test suite through `backend/.venv`, then run Oxlint, ESLint, and the frontend production build.
- Confirm the reviewed dynamic ZIP input preserves leading zeros, uses the backend `/api` proxy, and displays the sanitized response in a labeled table.

## Security and scope

- Keep the Geoapify credential and provider request entirely in the backend.
- Never print, return, log, screenshot, stage, or commit the API key or `.env` contents.
- Do not implement Assignment 2 hotel discovery, map, shortlist, local-storage tutorial, or chatbot behavior in this checkpoint.
- Do not modify instructor data or dependency declarations.

## Version-control checkpoint

- Create and switch to `feature/assignment-2-part-1` while preserving the approved changes.
- Update the evidence log, current handoff, and prompt index.
- Stage only intended source, tests, and documentation; exclude generated files, databases, dependencies, caches, and credentials.
- Verify the staged diff and create one commit named `Complete first public API activity`.
- Do not merge or push.

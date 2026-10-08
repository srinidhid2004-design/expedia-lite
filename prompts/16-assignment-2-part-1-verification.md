# 16 — Assignment 2 Part 1 AutoLoop verification

## Purpose

Verify every Assignment 2 Part 1 acceptance criterion with one live ZIP search and repeatable mocked failure cases.

## Selected instruction excerpt

> Compare the sanitized backend response with the visible search center, hotel list, map-marker count, and selected hotel identity. Verify selection in both directions, keyboard operation, narrow viewport, attribution, no console errors, and the existing Harbor search.

## Verification outcome

- The complete backend suite passed 57 tests; the focused mocked discovery suite passed 9 tests.
- Oxlint, ESLint, the production build, and `git diff --check` passed.
- One live `16802` search on October 7, 2026 returned the State College center and a variable capped page of 20 normalized records; the list and hotel-marker counts and identities matched.
- List-to-marker, marker-to-list, and keyboard selection stayed synchronized.
- Invalid, unresolved, zero-hotel, provider-failure, malformed-response, rate-limit, and missing-configuration behavior was checked locally or with mocks.
- Harbor still returned `T001` and `T009`; the browser console had no application errors.
- Credential-free screenshots were saved under `screenshots/`.

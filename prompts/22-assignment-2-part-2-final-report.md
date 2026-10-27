# 22 — Assignment 2 Part 2 final report

Finalize only the Assignment 2 Part 2 submission documentation on `main` after
confirming the reviewed merge, public repository, and public demo are
accessible.

## Required report content

- Identify the public repository, the assessed implementation merge commit,
  and the public demo. Make clear that a later documentation-only commit does
  not replace the assessed implementation commit.
- Document safe startup and backend-only Geoapify/Gemini configuration without
  including a credential, header value, environment content, or raw provider
  response.
- Link the Part 2 research and early mockup and explain the implemented
  two-request flow: proposed SQL, independent read-only validation and bounded
  retrieval, then a grounded answer over retrieved classroom records only.
- Record the SQLite protections, live Gemini success, fixed mocked no-match and
  rejected-mutation evidence, failed/revised provider approaches, final
  regression results, AI disclosure, prompt evidence, limitations, and manual
  course-submission boundary.
- Distinguish the current runtime database file hash from the historical
  logical/snapshot digest without inventing a reason for their difference.

## Continuity and publication

- Update `docs/evidence.md`, `handoffs/current.md`, and `prompts/README.md`.
- Stage documentation only, audit links and content, run the staged whitespace
  check, and scan for credentials, private paths, placeholders, unsupported
  claims, and generated files.
- Commit exactly `Finalize Assignment 2 Part 2 report` and push `main`
  normally. Do not force-push, merge, rebase, squash, amend, access Canvas, or
  make a live provider request.

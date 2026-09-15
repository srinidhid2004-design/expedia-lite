# 09 — Part 2 review, merge, and publication

User instruction received on 2026-09-15:

> My manual Visual Studio Code review and browser demonstration of Part 2 are complete. I approve the current Part 2 implementation on `feature/part-2-sqlite-crud`.

Authorized checkpoint:

- Reconfirm the feature branch, preserved Part 1 history, complete changed-file set, ignore rules, screenshots, and absence of dependency or instructor-data changes.
- Run backend pytest through `backend/.venv`, Oxlint, ESLint, and the production build.
- Record the completed manual review, stage only intended Part 2 files, run the staged whitespace check, and create one feature commit named `Complete Expedia Lite Part 2`.
- Switch to `main` and create a normal non-fast-forward merge commit named `Merge Expedia Lite Part 2`, without rebasing, squashing, amending, force-pushing, resolving unexpected conflicts, or deleting branches.
- Verify the combined app with a disposable ignored SQLite database, including frontend search, booking history, create, cancel-retain, delete, refresh persistence, service-restart persistence, no reseeding, and non-reused IDs.
- Finalize the Part 2 report and project records with the exact merge SHA and immutable public links, create one documentation-only commit named `Finalize Part 2 submission report`, and push `main` normally to the unchanged existing origin.
- Verify the repository and all report links without authentication. Do not access or submit to the course site.

Preserve the Part 1 implementation checkpoint `0c1666d2bb03fdefda55ccf3b905d80801d78d5f`. Never commit SQLite databases, environments, dependency directories, build output, caches, secrets, or temporary files. Do not change dependencies, instructor CSVs, or add behavior beyond Assignment 1 Part 2.

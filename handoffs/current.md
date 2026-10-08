# Current handoff

Updated: 2026-10-07

## Orientation

Expedia Lite is a FastAPI, Vue 3, SQLite, Geoapify, and Leaflet course application. Assignment 2 Part 1 is implemented, manually reviewed, merged into `main`, published in the public repository, and documented with a public demonstration video. Assignment 1 history and behavior remain preserved.

Read [`../README.md`](../README.md), follow [`../AGENTS.md`](../AGENTS.md), use [`../docs/verification.md`](../docs/verification.md) for repeatable checks, and consult [`../docs/evidence.md`](../docs/evidence.md) and [`../report.md`](../report.md) for the completed submission record.

## What exists

- Preserved Assignment 1 one-time SQLite seeding, hotel-name search, demo users, simulated booking history, create, cancel-retain, delete, and restart persistence.
- Backend-only Geoapify configuration that reports only whether the key is configured.
- Exact five-digit U.S. postcode resolution that preserves leading zeros.
- A strict 5 km Geoapify Places search for `accommodation.hotel`, proximity ordering, a 20-record result cap, and typed provider-independent normalization.
- Safe, distinct handling for invalid input, unresolved ZIP, missing configuration, provider failure, malformed response, rate/quota failure, and successful zero-hotel responses.
- A Vue ZIP workflow that calls only the local `/api` proxy and presents the verified center and provider-supported fields without inventing names, addresses, prices, ratings, rooms, availability, or bookability.
- A Leaflet/OpenStreetMap map with a separate center marker, 5 km circle, hotel markers, visible attribution, cleanup, and narrow-screen behavior.
- One shared provider place ID that synchronizes list-to-marker and marker-to-list selection, including keyboard operation.
- Primary-source research, an approved early mockup, repeatable verification instructions, evidence, prompt records, screenshots, the final report, and the public demo video.

## Verified state

- Complete backend suite: 57 tests passed with two known upstream FastAPI/Starlette test-client deprecation warnings.
- Focused mocked hotel-discovery suite: 9 tests passed.
- Oxlint, ESLint, Vite production build, and whitespace checks passed.
- A live ZIP `16802` check on October 7, 2026 resolved State College, US at latitude `40.803167822`, longitude `-77.861384958`.
- The observed provider page contained 20 normalized hotels; the number is variable, capped, and not an exhaustive-inventory claim.
- The table and map contained matching provider identities and counts; list-to-marker, marker-to-list, and keyboard selection passed.
- Required attribution, narrow layout, failure/empty states, browser console, and preserved Assignment 1 `Harbor` results T001 and T009 passed.
- Credential comparisons and screenshot checks found no configured key or local `.env` contents in published artifacts.

## Git and publication state

- Current branch: `main`, tracking `origin/main`.
- Public repository: [https://github.com/srinidhid2004-design/expedia-lite](https://github.com/srinidhid2004-design/expedia-lite).
- Preserved Assignment 1 Part 1 implementation commit: `0c1666d2bb03fdefda55ccf3b905d80801d78d5f`.
- Assignment 1 Part 2 merge commit: `a98a9ccd1de2329d35b2924e2b1f121fe7359627`.
- First-public-API milestone commit: `91a20b0c009748393d1156cc2b83010b4a86fbf3`.
- Reviewed Assignment 2 Part 1 feature commit: `77572078b0e6342a32e4d0fcc60ae05b7f20bb1a`.
- Assessed Assignment 2 Part 1 merge commit: [`6c0575d092ad677b3ec25a6bdaa10aa7739fad29`](https://github.com/srinidhid2004-design/expedia-lite/commit/6c0575d092ad677b3ec25a6bdaa10aa7739fad29).
- Public demo video: [Expedia Lite — Assignment 2 Part 1 demonstration](https://drive.google.com/file/d/1HIHOgmqgaugYnmLFjktFhjwINth2j6fC/view?usp=sharing).
- The feature branch remains retained. No squash, rebase, amend, force-push, or history rewrite occurred.

## Limitations

- Geoapify coverage and optional fields can change. The interface shows one bounded page of up to 20 usable records and does not claim exhaustive coverage.
- OpenStreetMap Standard tiles suit this local, low-volume classroom demonstration but do not provide a production SLA.
- Only exact five-digit U.S. ZIP input is supported in Part 1.
- The discovery map does not provide routes, pricing, ratings, availability, real booking, shortlist persistence, or chatbot/RAG behavior.
- Tall-page screenshot stitching can repeat content below the primary evidence area; the recorded center, list, selected marker, and attribution remain independently verified.
- Two upstream test-client deprecation warnings remain non-failing.

## Next task

The project-side Assignment 2 Part 1 work is complete. Course-site submission remains a manual user action; this project did not access or submit anything to Canvas. Begin Assignment 2 Part 2 shortlist or chatbot/RAG work only after a separate authorization and requirements review.

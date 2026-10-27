# Expedia Lite — Assignment 2, Part 2

## Project and repository access

Public repository: [https://github.com/srinidhid2004-design/expedia-lite](https://github.com/srinidhid2004-design/expedia-lite)

Assessed Assignment 2 Part 2 implementation: [`007aea0429ed3ce8abc0cfc4ff6e7401f24cb810`](https://github.com/srinidhid2004-design/expedia-lite/commit/007aea0429ed3ce8abc0cfc4ff6e7401f24cb810) (`Merge Assignment 2 Part 2 RAG workflow`). This two-parent merge commit is the assessed application implementation. The later commit that finalizes this report changes documentation only and does not replace the assessed implementation commit.

Public demo video: [Assignment 2 part 2 demo.mp4](https://drive.google.com/file/d/1zhnSblbBfTXlPtfD9Oh8gHV-tCraqoQn/view?usp=sharing)

Project records: [README](https://github.com/srinidhid2004-design/expedia-lite/blob/main/README.md), [project rules](https://github.com/srinidhid2004-design/expedia-lite/blob/main/AGENTS.md), [design](https://github.com/srinidhid2004-design/expedia-lite/blob/main/docs/design.md), [verification procedure](https://github.com/srinidhid2004-design/expedia-lite/blob/main/docs/verification.md), [evidence log](https://github.com/srinidhid2004-design/expedia-lite/blob/main/docs/evidence.md), [prompt index](https://github.com/srinidhid2004-design/expedia-lite/blob/main/prompts/README.md), and [current handoff](https://github.com/srinidhid2004-design/expedia-lite/blob/main/handoffs/current.md).

## Startup and safe configuration

From the project root, create the backend virtual environment and install the declared backend and locked frontend dependencies:

```powershell
python -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt
cd frontend
npm install
cd ..
```

Use the blank, tracked [`.env.example`](https://github.com/srinidhid2004-design/expedia-lite/blob/main/.env.example) as the variable-name template for an ignored project-root `.env`. The required backend-only variable names are `GEOAPIFY_API_KEY` and `GEMINI_API_KEY`. Supply values only in the local ignored file; never place them in Vue, `VITE_` variables, documentation, screenshots, logs, fixtures, or Git. Restart FastAPI after changing local configuration.

Start the backend and frontend in separate terminals:

```powershell
cd backend
.\.venv\Scripts\python.exe -B -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```powershell
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

The Vue application is at `http://127.0.0.1:5173/`; the backend health endpoint is `http://127.0.0.1:8000/api/health`. Health reports configuration status only, never secret values. The runtime provider is fixed to Google Gemini API model `gemini-3.5-flash-lite`, with zero automatic retries and no provider or model fallback.

## Research and early design

The [Part 2 research](https://github.com/srinidhid2004-design/expedia-lite/blob/main/docs/assignment-2-part-2-research.md) records direct primary-source links and access dates for Gemini structured output and limits, SQLite read-only controls, bounded SQL-generation practices, accessible chatbot states, and grounded answers. The [early annotated mockup](https://github.com/srinidhid2004-design/expedia-lite/blob/main/docs/assignment-2-part-2-rag-mockup.svg) shows the planned question, loading, proposed-SQL, retrieved-record, answer, no-match, rejected-query, provider-error, and simulated-data states while preserving the existing hotel workflow.

The adopted design is a two-request retrieval-augmented workflow: Request 1 proposes a parameterized read-only query; the backend independently validates and executes it against a bounded local saved-hotel view; Request 2 receives only the bounded question and retrieved classroom records and produces a grounded explanation. Provider schema constraints improve consistency but never replace backend validation.

Important research decisions and risks were:

- Gemini REST structured output was selected because the earlier class free Nemotron endpoint did not reliably return a usable structured proposal.
- Direct REST through the already declared `httpx` dependency avoids an unnecessary provider SDK.
- Gemini unpaid-tier data may be used to improve Google products and may receive human review, so live checks use only non-confidential classroom data.
- `mode=ro` and `PRAGMA query_only` are combined with a default-deny authorizer, strict allowlists, bound parameters, execution and payload bounds, and independent grounding checks; no one control is treated as sufficient.

## Implemented workflow

The browser sends only JSON containing the natural-language `question` to `POST /api/chatbot/query`. It cannot supply a model, endpoint, key, SQL, database path, prompt, or provider choice.

```text
Natural-language question
        ↓
Gemini Request 1: schema-constrained SQL proposal and parameters
        ↓
Backend shape checks and unchanged read-only SQL validator
        ↓
Bounded read-only SQLite retrieval over saved-hotel tables
        ↓
zero rows → deterministic no-match response; Request 2 skipped
        ↓ rows exist
Gemini Request 2: original bounded question + retrieved records only
        ↓
Grounding and row-reference checks
        ↓
Vue trace and grounded answer
```

The visible trace presents the bounded question, exact model, provider-request count, proposed SQL, safe parameters, retrieved columns and rows, grounded answer, explanation, referenced row numbers, limitation, and simulated-classroom-data notice. SQL rejected by the validator is shown as rejected evidence and is never described as executed.

The chatbot builds on the reviewed local-storage workflow. A user may save provider hotels with their ZIP association and verified search context. Each newly saved hotel receives October 10–14, 2026 demo-night rows. These local nightly rates and room counts are simulated classroom data, not provider-supplied or real inventory. Local-first ZIP lookup continues to show the saved subset before falling back to the provider only when local lookup succeeds with zero matches.

## Database and security controls

Generated SQL is untrusted. Retrieval uses a separate verified SQLite `file:` URI with `mode=ro`, enables `PRAGMA query_only`, and installs a default-deny Python `sqlite3` authorizer. Reads are limited to approved columns in `saved_hotels`, `saved_hotel_zip_associations`, `saved_search_contexts`, and `demo_hotel_nights`; Assignment 1 users, bookings, SQLite metadata, temporary objects, unsafe functions, attachments, pragmas, and every mutation are denied.

The validator requires exactly one bounded read-only statement, unnumbered `?` parameters for every value except the final top-level integer `LIMIT`, and a final limit from 1 through 20. It rejects comments, multiple statements, unauthorized tables or columns, unbound literals, writable or deceptive CTEs, and prohibited operations. A progress deadline bounds execution. Results are capped by row count, column count, cell size, and total serialized payload.

Checkout is excluded. Every occupied night must exist and have positive `rooms_available`; missing nights are not treated as available. The backend derives date coverage and sums stored integer cents rather than trusting the model to invent or calculate facts. Tests prove rejected mutation proposals stop before execution and leave complete temporary-database snapshots unchanged.

Both provider keys remain backend-only in the ignored `.env`. Browser responses, UI traces, fixtures, screenshots, and Git contain neither credentials nor raw provider messages.

## Verification and evidence

Detailed commands, live-versus-mocked labels, and expected-versus-observed results are in the public [evidence log](https://github.com/srinidhid2004-design/expedia-lite/blob/main/docs/evidence.md) and [verification procedure](https://github.com/srinidhid2004-design/expedia-lite/blob/main/docs/verification.md).

### Real live Gemini success

On October 20, 2026, one explicitly authorized live flow submitted this classroom question:

> Among my saved hotels, which are available for both October 10 and October 11, 2026, and what is each hotel's total simulated cost for those two nights? Checkout is October 12, 2026.

Request 1 proposed one read-only query using parameters `2026-10-10`, `2026-10-11`, `0`, and `2` in placeholder order and a final `LIMIT 20`. The unchanged validator accepted it. Retrieval returned exactly the two saved records relevant to the question:

| Retrieved hotel | Included nights | Positive room requirement | Simulated total |
| --- | --- | --- | ---: |
| Hotel State College | October 10 and 11, 2026 | Met on both nights | 20,000 cents / $200.00 |
| Scholar Hotel State College | October 10 and 11, 2026 | Met on both nights | 20,000 cents / $200.00 |

October 12 was correctly excluded as checkout. Request 2 grounded its answer only in those two rows and referenced both rows. The trace recorded exactly two provider requests, and the runtime database SHA-256 and logical counts were identical before and after.

Public-safe live screenshots tied to the assessed merge commit:

- [Question and Gemini model](https://github.com/srinidhid2004-design/expedia-lite/blob/007aea0429ed3ce8abc0cfc4ff6e7401f24cb810/screenshots/assignment-2-part-2-gemini-live-success-question-model.jpg)
- [Proposed SQL and safe parameters](https://github.com/srinidhid2004-design/expedia-lite/blob/007aea0429ed3ce8abc0cfc4ff6e7401f24cb810/screenshots/assignment-2-part-2-gemini-live-success-sql-parameters.jpg)
- [Retrieved-record continuation](https://github.com/srinidhid2004-design/expedia-lite/blob/007aea0429ed3ce8abc0cfc4ff6e7401f24cb810/screenshots/assignment-2-part-2-gemini-live-success-sql-parameters-continuation.jpg)
- [Question and grounded answer](https://github.com/srinidhid2004-design/expedia-lite/blob/007aea0429ed3ce8abc0cfc4ff6e7401f24cb810/screenshots/assignment-2-part-2-gemini-live-success-question-answer.jpg)
- [Explanation, row references, and simulated-data notice](https://github.com/srinidhid2004-design/expedia-lite/blob/007aea0429ed3ce8abc0cfc4ff6e7401f24cb810/screenshots/assignment-2-part-2-gemini-live-success-grounded-answer-evidence.jpg)

### Fixed mocked negative cases

These were credential-free fixed-fixture checks using fake keys, `httpx.MockTransport`, stubbed frontend requests, and temporary SQLite databases—not live Gemini calls.

| Scenario | Expected result | Observed result |
| --- | --- | --- |
| `no_match_sql` | Request 1 proposes valid SQL; zero rows return `no_match`; Request 2 is skipped; no hotel, price, availability, or answer is invented | Passed with one provider request, zero rows, no answer, and an unchanged temporary database |
| `mutation_sql` | A proposed `DELETE` reaches the unchanged validator and is rejected before execution; Request 2 is skipped | Passed with `rejected_sql`, one provider request, no records or answer, and an unchanged complete temporary-database snapshot |

The repeatable negative-case instruction is [Prompt 21](https://github.com/srinidhid2004-design/expedia-lite/blob/main/prompts/21-assignment-2-part-2-negative-case-verification.md); the assertions and commands are recorded in the [evidence log](https://github.com/srinidhid2004-design/expedia-lite/blob/main/docs/evidence.md) and [verification procedure](https://github.com/srinidhid2004-design/expedia-lite/blob/main/docs/verification.md).

### Failed and revised approach

Three controlled attempts with the class-demonstrated free OpenRouter/Nemotron model repeatedly returned unusable Request 1 structured output. Each attempt failed safely before SQL execution: Request 2 was skipped and the database was unchanged. Compatibility work supported strict tool-call and complete-object forms without weakening the SQL validator, but the endpoint remained unreliable for this flow. The documented revision migrated the provider-specific transport to Gemini while preserving the provider-independent retrieval, route, UI, and security contracts.

The first Gemini live attempt then exposed a GenerateContent request-structure issue, which was corrected against the documented REST contract. A later schema-valid proposal was correctly rejected because numeric SQL values had not been bound. Request 1 instructions were tightened so dates, the zero availability threshold, and the required-night count use parameters; the final live attempt then passed the unchanged validator. None of the failed attempts is presented as success, and no raw provider response or credential is retained.

Public-safe failed/revised evidence includes the [initial malformed Nemotron proposal](https://github.com/srinidhid2004-design/expedia-lite/blob/007aea0429ed3ce8abc0cfc4ff6e7401f24cb810/screenshots/assignment-2-part-2-live-malformed-proposal.jpg), [later safe malformed-response classification](https://github.com/srinidhid2004-design/expedia-lite/blob/007aea0429ed3ce8abc0cfc4ff6e7401f24cb810/screenshots/assignment-2-part-2-live-corrected-third-attempt-malformed-response.jpg), and [initial Gemini invalid-request evidence](https://github.com/srinidhid2004-design/expedia-lite/blob/007aea0429ed3ce8abc0cfc4ff6e7401f24cb810/screenshots/assignment-2-part-2-gemini-live-failure-invalid-request.jpg).

### Final automated regression

| Check | Observed result |
| --- | --- |
| Complete backend pytest suite through `backend/.venv` | 196 passed; two known non-failing FastAPI/Starlette dependency deprecation warnings |
| `pip check` in `backend/.venv` | No broken requirements found |
| Framework-free frontend chatbot request tests | 29 passed |
| Oxlint | Passed with no findings |
| ESLint | Passed with no findings |
| Vite production build | Passed; 17 modules transformed |
| Working-tree and staged whitespace checks | Passed |

The live case was only the explicitly authorized two-request Gemini success described above. Provider failures, malformed output, grounding failures, no match, and rejected SQL were verified with fixed mocked inputs.

The approved current runtime SQLite **file** SHA-256 is `6ec793f68ae34af67927f81199ab68653a7a6c1c47be2f687deed75e4ae572b3`. The separately calculated historical sorted-row logical/snapshot digest is `698d758b3b0201ab9941f2ac90b7e208e0661881f7f132cbc3948f4440c3da27`. They are different measurements; the cause of the byte-level file transition is not proven.

## Public demo

The public [Assignment 2 Part 2 demo video](https://drive.google.com/file/d/1zhnSblbBfTXlPtfD9Oh8gHV-tCraqoQn/view?usp=sharing) demonstrates the reviewed chatbot workflow in the published application. The Drive page was checked without an authenticated session and displayed `Assignment 2 part 2 demo.mp4` without an additional access request.

## AI assistance disclosure

The application's runtime generative model is Google Gemini API model `gemini-3.5-flash-lite`. It proposes structured SQL and produces the final grounded explanation; the backend independently validates both stages.

OpenAI Codex, based on GPT-5, assisted with research summarization, planning, the early mockup, code generation, tests, debugging, verification, documentation, and prompt records. The Codex interface did not expose a more specific internal snapshot identifier, so none is invented. Human review and approval occurred at project milestones, and outputs were checked through automated tests, read-only database evidence, browser evidence, and manual review.

## Prompt evidence

The complete numbered record is indexed in [prompts/README.md](https://github.com/srinidhid2004-design/expedia-lite/blob/main/prompts/README.md). Representative decisions include:

- [Prompt 19](https://github.com/srinidhid2004-design/expedia-lite/blob/main/prompts/19-local-hotel-storage-manual-verification.md): preserve manual database evidence and verify that save, edited simulated values, refresh persistence, and transactional removal match the local tables.
- [Prompt 20](https://github.com/srinidhid2004-design/expedia-lite/blob/main/prompts/20-assignment-2-part-2-research-and-mockup.md): keep model calls backend-only, treat SQL as untrusted, permit bounded read-only retrieval, and show proposed SQL, records, and answer together.
- [Prompt 21](https://github.com/srinidhid2004-design/expedia-lite/blob/main/prompts/21-assignment-2-part-2-negative-case-verification.md): prove mocked no-match and rejected-mutation stopping behavior and database immutability.
- [Prompt 22](https://github.com/srinidhid2004-design/expedia-lite/blob/main/prompts/22-assignment-2-part-2-final-report.md): bind the final report to the assessed merge, public demo, verified evidence, security audit, and documentation-only finalization.

These descriptions deliberately omit credentials, environment contents, and raw provider payloads.

## Limitations and next steps

- Saved hotels are a user-selected local subset, not a complete hotel inventory.
- Dated rates and room counts are simulated classroom data, not live provider inventory, prices, availability, or a booking guarantee.
- Geoapify and Gemini require valid backend configuration and remain subject to external availability, quota, policy, and coverage changes.
- Generated SQL runs only when it passes the strict validator and SQLite defenses; this limits the range of questions the chatbot can answer.
- One live classroom question verifies that bounded flow, not every possible natural-language question.
- The application has no authentication, payments, taxes, fees, real inventory, autonomous booking, or database-mutating chatbot action.
- Reasonable future work could add more deterministic question templates, clearer query guidance, broader adversarial test coverage, and production-grade tile/provider arrangements. Those improvements are not implemented or claimed here.
- Implementation, merge, publication, demo recording, and report completion are finished. Uploading or submitting materials to Canvas remains a manual user action.

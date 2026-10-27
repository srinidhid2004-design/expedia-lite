# Assignment 2 Part 2 — RAG chatbot research and early design

Status: **research/design record plus mocked implementation evidence; live Gemini verification is not yet authorized or claimed**. Original sources were accessed October 8, 2026; Gemini migration sources were rechecked October 20, 2026.

## Course requirement and selected model

The revised Assignment 2 Part 2 brief requires a SQL-based retrieval-and-generation workflow on top of the reviewed local-hotel storage checkpoint. The backend must send a natural-language question, relevant schema, and rules to one approved model; validate and execute only a bounded read-only query; then send the original question and limited retrieved records in a second model request. The remote model never receives a database connection and the chatbot never changes records or creates bookings.

- Selected API provider: **Google Gemini API**
- Model publisher: **Google**
- Exact model identifier: **`gemini-3.5-flash-lite`**
- Backend-only configuration name: `GEMINI_API_KEY`
- Endpoint: `POST https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent`
- Vector database: not required and not planned

The course brief permits paid OpenAI, Gemini, or the class-demonstrated free Nemotron option. The project initially selected OpenRouter model `nvidia/nemotron-3.5-lightning:free`. Three controlled live attempts all stopped at Request 1 with malformed proposal output despite bounded tool-call and assistant-content compatibility work. Those attempts remain evidence of a failed/revised approach. The user then selected Gemini as the assignment-permitted no-cost migration target.

## Sources consulted

| Source | Direct link | Useful evidence |
| --- | --- | --- |
| Course-provided Assignment 2 overview | Attached course document; no public URL supplied | Defines the two-request SQL RAG flow, local-storage foundation, read-only validation, grounded answer, required states, and mock/live verification boundaries. |
| OpenRouter — NVIDIA Nemotron 3.5 Lightning (free) | [Model page](https://openrouter.ai/nvidia/nemotron-3.5-lightning:free) | Confirms the exact slug, zero token price, 1,000,000-token context, 65,536-token completion ceiling, tool support, lack of `response_format`, and the free-endpoint data-use notice. |
| OpenRouter — API authentication | [Authentication](https://openrouter.ai/docs/api/reference/authentication) | Requires an OpenRouter API key as a Bearer token and recommends backend environment variables and per-key credit limits. |
| OpenRouter — create a chat completion | [Chat completion API](https://openrouter.ai/docs/api/api-reference/chat/create-a-chat-completion) | Documents the `/api/v1/chat/completions` request, `model`, `messages`, `tools`, `tool_choice`, token bounds, response shape, and HTTP errors. |
| OpenRouter — structured outputs | [Structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs) | Explains `response_format` and strict JSON Schema for supported models. The approved free model does not list that parameter, so this project cannot rely on enforced JSON output. |
| OpenRouter — limits | [Credit and rate limits](https://openrouter.ai/docs/api/reference/limits) | Documents daily/per-minute free-model limits, quota inspection, 402/429 behavior, `Retry-After`, rate-limit headers, and exponential backoff. |
| OpenRouter — free plan | [Pricing](https://openrouter.ai/pricing) | Records the current free-plan daily request ceiling and that free access is limited to free models. |
| OpenRouter — free-model rate-limit explanation | [Lowest-cost inference guide](https://openrouter.ai/blog/tutorials/how-to-get-the-lowest-cost-llm-inference-on-openrouter/) | Records 20 requests/minute, 50 requests/day for a free account, and 1,000 requests/day after at least $10 in lifetime credit purchases. |
| Google — Gemini 3.5 Flash-Lite model | [Model page](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite) | Confirms exact stable model ID `gemini-3.5-flash-lite`, text output, structured-output support, function-calling support, and model token limits. |
| Google — GenerateContent REST API | [Generate content](https://ai.google.dev/api/generate-content) | Documents the `v1beta/models/{model}:generateContent` endpoint, `systemInstruction`, `contents`, `generationConfig`, candidate response envelope, and current `responseFormat.text` JSON schema contract. |
| Google — structured outputs | [Structured outputs](https://ai.google.dev/gemini-api/docs/structured-output) | Documents `application/json`, schema-constrained text output, and the supported JSON Schema subset. |
| Google — Gemini API pricing | [Pricing](https://ai.google.dev/gemini-api/docs/pricing) | Records free-tier availability and the important disclosure that free-tier content is used to improve Google products. |
| Google — Gemini API rate limits | [Rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) | Explains RPM/TPM/RPD enforcement and that active project limits are shown in Google AI Studio rather than assumed as one universal fixed allowance. |
| Google — Gemini API Additional Terms | [Terms](https://ai.google.dev/gemini-api/terms) | States that unpaid-tier submissions and responses may be used to improve Google products and may be reviewed; sensitive, confidential, or personal information must not be submitted. |
| SQLite — URI filenames | [SQLite URI documentation](https://www.sqlite.org/uri.html) | Documents `file:` URIs and `mode=ro`, which opens an existing database read-only and fails instead of creating it. |
| SQLite — `PRAGMA query_only` | [SQLite PRAGMA documentation](https://www.sqlite.org/pragma.html#pragma_query_only) | Rejects `CREATE`, `DELETE`, `DROP`, `INSERT`, and `UPDATE`, but is not a complete security boundary by itself. |
| Python 3.14 — `sqlite3` | [Python `sqlite3` documentation](https://docs.python.org/3.14/library/sqlite3.html) | Documents URI connections, bound placeholders, `set_authorizer`, `SQLITE_DENY`, and `set_progress_handler` for aborting excessive work. |
| OWASP — SQL Injection Prevention | [SQL Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet) | Recommends parameterized values, allowlist validation, least privilege, and views/limited access rather than escaping or trusting dynamic SQL. |
| W3C WAI-ARIA — status role | [WAI-ARIA status role](https://www.w3.org/TR/wai-aria-1.2/#status) | A status is a polite, atomic live region and should not receive focus merely because its text changes. |
| W3C APG — alert pattern | [Alert pattern](https://www.w3.org/WAI/ARIA/apg/patterns/alert/) | Important dynamic errors may use `role="alert"`; alerts should not steal focus or disappear automatically. |

## Gemini migration findings

`gemini-3.5-flash-lite` is the selected exact stable model. Official documentation lists structured outputs and function calling; this implementation uses only schema-constrained JSON text. Each request sends a fixed schema under `generationConfig.responseFormat.text` with MIME type `application/json`. The transport uses the existing declared `httpx` dependency, a finite timeout, a bounded request and response, one candidate, no SDK, zero automatic retries, and no provider or model fallback.

Authentication uses only the backend `x-goog-api-key` header. The key is never placed in the URL, body, browser, response trace, fixture, documentation, or Git. Request 1 sends only the bounded question, the four-table classroom schema description, and query rules. Request 2 is impossible until SQL passes the unchanged retrieval validator and returns rows; it sends only the question and bounded normalized classroom rows.

The official pricing page lists free-tier access, but active free-tier RPM/TPM/RPD limits are project-specific and should be checked in Google AI Studio. The project therefore records no invented numeric allowance. Unpaid-tier inputs and outputs may be used to improve Google products and may receive human review. Only non-confidential classroom schema/questions and the minimum retrieved classroom records are appropriate for a future explicitly authorized live check.

Safe outcomes distinguish missing configuration, authentication, permission, daily/project quota, short-window rate limit, invalid fixed request, timeout, provider failure, safety block, empty candidates, malformed/schema-invalid output, rejected SQL, database failure, no match, and grounding failure. Raw Gemini responses and exception text are never returned.

## Historical OpenRouter/Nemotron findings

### Chat API and authentication

OpenRouter exposes an OpenAI-compatible chat-completion endpoint. The retired transport reused the installed `httpx` client with a finite timeout and no SDK. Its credential remained backend-only in an `Authorization` header; Vue never received the key or contacted OpenRouter directly.

The approved free model is currently listed at zero prompt and completion token cost. Free does not mean unlimited: the current general limits are 20 requests per minute and 50 requests per day for a free account. An account with at least $10 in lifetime credit purchases receives up to 1,000 free-model requests per day while retaining the 20-per-minute cap. A successful chatbot question normally consumes two model requests, so the lower daily tier supports at most 25 complete successful flows before failed attempts or verification calls.

### Structured output behavior

`nvidia/nemotron-3.5-lightning:free` supports `tools` and `tool_choice`, but its model page explicitly says it does not support `response_format`. Strict JSON Schema output therefore cannot be assumed. The first request exposes one non-executing tool contract named `propose_read_only_query`, with required SQL text and positional parameters plus optional intent metadata. The compatibility boundary accepts one correctly named tool call or, only when no tool call is emitted, one complete bounded assistant-content JSON object. Both forms use duplicate-key rejection plus the same exact-key and type validation. Model output remains untrusted, and malformed or ambiguous forms stop before database execution.

The second request uses a separate `provide_grounded_answer` contract and receives fixed grounding instructions, the original question, and the bounded normalized record payload only. It accepts one correctly named tool call or, only when no tool call is emitted, one complete bounded assistant-content JSON object. The interface keeps the retrieved records visible beside the answer so a reviewer can compare every claim with evidence.

### Availability, privacy, and errors

Model and upstream capacity are variable. The application must map errors without returning raw provider messages or request headers:

- missing local configuration or 401/403 authentication failure → safe configuration/unavailable response;
- 402 credit/limit state → safe provider-limit response;
- 408 or local HTTP timeout → timeout response;
- 413 → question or request is too large;
- 422 or malformed model output → rejected model proposal/response;
- 429 → distinct rate/quota response that honors `Retry-After` without an aggressive retry loop;
- 500, 502, 503, 524, or 529 → safe provider failure/overload response.

The free endpoint states that inputs and outputs may be logged for security and NVIDIA product improvement. The interface will tell users not to enter personal or confidential information. Only the natural-language question, the fixed public schema description, and a minimal set of local classroom records may leave the backend. Credentials, the database file, Assignment 1 users/bookings, and unrelated records must never be sent.

## Safe bounded SQL-generation design

Model-generated SQL is hostile input even when the question is benign. No single safeguard is sufficient, so the planned execution path layers independent controls.

1. **Constrain the input.** Trim the question, require meaningful text, and cap it at 500 characters. Do not concatenate the question into SQL.
2. **Constrain the model contract.** Request exactly one `propose_read_only_query` call containing one statement, `?` placeholders, and a positional parameter list; intent is optional trace metadata. Include one minimal exact-key example with a final bounded `LIMIT`, and cap the SQL proposal response to a small completion budget.
3. **Validate shape before SQLite.** Reject blank or oversized SQL, comments, multiple statements, non-`SELECT`/read-only `WITH` statements, unbound values, unexpected parameter types, and a missing or excessive result bound.
4. **Allowlist data access.** Permit reads only from `saved_hotels`, `saved_hotel_zip_associations`, `saved_search_contexts`, and `demo_hotel_nights`, and only their documented columns. Deny `sqlite_schema`, Assignment 1 tables, temporary objects, attached databases, extension loading, and unsafe functions. Allow only required scalar/aggregate functions such as `COUNT`, `MIN`, `MAX`, `SUM`, `ROUND`, and `COALESCE` after focused review.
5. **Open a separate read-only connection.** Use a verified absolute `file:` URI with `mode=ro` and `uri=True`; do not use `immutable=1` because the application database can legitimately change in another connection.
6. **Add SQLite defenses.** Enable `PRAGMA query_only = ON`; install `Connection.set_authorizer` and return `SQLITE_DENY` for every action except approved `SELECT`, `READ`, and allowlisted function operations; explicitly keep extension loading disabled.
7. **Bound work and output.** Use `Connection.set_progress_handler` with a short monotonic deadline, require a deterministic `LIMIT` no greater than 20, fetch at most 21 rows to detect overflow, and cap the serialized record payload at 32 KiB. A timeout, excess row, or excess payload becomes a rejected-query result.
8. **Execute one statement only.** Use `Connection.execute(sql, parameters)`, never `executescript`, and close the isolated connection after retrieval.
9. **Normalize records.** Convert rows to a fixed provider-independent structure. Keep integer cents and room counts as stored; do not convert missing values into claims.
10. **Verify immutability.** Tests compare relevant table counts/content before and after allowed and rejected queries, including `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ATTACH`, `PRAGMA`, multiple statements, unsafe functions, recursive/excessive work, and attempts to read Assignment 1 data.

This is defense in depth. A keyword blocklist alone is rejected because comments, alternate syntax, functions, CTEs, and SQLite extensions can bypass superficial string checks. `PRAGMA query_only` alone is also rejected because SQLite documents that it is not a fully read-only connection boundary.

## Selected two-request RAG flow

```text
Natural-language question (≤ 500 characters)
        ↓
FastAPI validation; backend-only key/model configuration
        ↓
REQUEST 1 to Gemini GenerateContent
question + fixed allowed schema + query rules
        ↓
Schema-constrained JSON proposes SQL + bound parameters
        ↓
Backend shape validation + table/column/function allowlists
        ↓
SQLite file: URI mode=ro + query_only + authorizer + progress deadline
        ↓
At most 20 normalized records / 32 KiB
        ↓
zero rows ──→ deterministic no-match/insufficient-data response
        ↓ rows exist
REQUEST 2 to Gemini GenerateContent
fixed grounding rules + original question + limited records only
        ↓
Grounded explanatory answer + cited record identifiers
        ↓
Vue shows question, proposed SQL, retrieved records, and answer together
```

The second model request will not receive credentials, database paths, the full schema, the proposed SQL, Assignment 1 records, or unselected database content. The backend—not the model—will compute multi-night row counts, checkout-exclusive date ranges, totals in cents, and minimum stored room counts. Missing nights produce insufficient-data feedback and must never be described as available.

## Grounding and honest-answer rules

- Answer only from retrieved rows and name the number of records used.
- Preserve `NULL` provider names/addresses as unavailable; do not fill them from model knowledge.
- Label every rate, total, and room count as **simulated classroom data**.
- Treat checkout as excluded. A requested stay is answerable only when every required night is present.
- Use backend-computed totals and coverage fields; do not ask the model to perform financial arithmetic.
- Do not describe stored room counts as live inventory or guarantee bookability.
- If no rows match, return deterministic no-match guidance without spending the second model request.
- If rows exist but dates or fields are incomplete, return an insufficient-data result; do not infer or interpolate.
- Keep retrieved records visible so the answer can be audited.
- Never let an answer trigger save, remove, booking, cancellation, or any other mutation.

## Accessible interaction decisions

- Use a real `<label>` and helper text for a multiline question field; keep native keyboard behavior and visible focus.
- Give the submit control a clear verb such as **Ask about saved hotels** and disable repeat submission while busy.
- Clear stale SQL, records, answers, and errors when a new request begins.
- Put loading and successful progress in a persistent `role="status"`/polite live region without moving focus.
- Put validation, rejected-query, missing-configuration, quota, timeout, and provider failures in persistent `role="alert"` feedback that does not disappear automatically.
- Present proposed SQL in a labeled `<pre><code>` region and records in a semantic table with a caption and scoped headers.
- Use headings and text labels—not color alone—to distinguish answer, no match, insufficient data, rejected query, and provider failure.
- On narrow screens, stack SQL, records, and answer; keep any wide record table in its own horizontal scrolling region.
- Preserve the existing hotel search, ZIP/list/map, and Add/Remove Local interfaces above the chatbot rather than replacing them.

## Adopted decisions

- Use Google Gemini API with exactly `gemini-3.5-flash-lite`; do not use a moving alias, alternate provider, paid fallback, or model fallback.
- Reuse installed `httpx` with finite timeouts; add no SDK or dependency at this stage.
- Use the current GenerateContent `responseFormat.text` JSON schema contract for both requests, then independently validate every returned field and treat the proposal as untrusted.
- Use a separate read-only SQLite connection and authorizer for every generated query.
- Limit retrieval to the four local API-hotel tables and never expose Assignment 1 user or booking data.
- Make the successful full-credit path two model requests. Short-circuit deterministic validation and no-match cases.
- Keep SQL, retrieved evidence, and the grounded answer visible together for verification.
- Use mocks and labeled fixtures for all automated provider outcomes. Allow one minimal live-model check only after explicit authorization.

## Rejected approaches

- **Model or browser connects to SQLite:** rejected; the remote model receives text only and Vue never receives a database path.
- **Frontend calls any model provider:** rejected because it would expose the credential and bypass backend validation.
- **Execute SQL because it starts with `SELECT`:** rejected as an inadequate single check.
- **Trust `PRAGMA query_only` alone:** rejected because SQLite says it is not a complete read-only boundary.
- **Use `executescript`:** rejected because multiple statements expand the attack surface.
- **Send the full database, complete schema, users, or bookings:** rejected as unnecessary disclosure.
- **Continue relaxing the Nemotron parser after three malformed live Request 1 attempts:** rejected as speculative and less reliable than migrating to an assignment-permitted provider with documented schema-constrained output.
- **Use `openrouter/free`, a moving model alias, or automatic provider fallback:** rejected because the assignment record needs an exact assessed model and explicit cost control.
- **Trust schema-constrained JSON without backend validation:** rejected; provider enforcement does not replace the SQL, parameter, retrieval, and grounding safeguards.
- **Add a vector database, embedding model, agent framework, Gemini SDK, or OpenRouter SDK:** rejected as unnecessary for the required SQL retrieval flow; direct REST with existing `httpx` is sufficient.
- **Let the LLM calculate totals or invent missing nights:** rejected; the backend derives totals and coverage from stored rows.
- **Retry model failures automatically without a bound:** rejected because free quota is small and failed attempts may still consume allowance.

## Weaknesses, risks, and open verification items

- Schema-constrained output does not guarantee safe SQL or grounded answers. Independent validation and rejection tests remain mandatory.
- Three controlled Nemotron live Request 1 attempts returned malformed proposal output across the original and compatibility-revised parsers. Raw provider payloads were deliberately not retained. The screenshots and safe outcomes remain preserved as failed/revised-approach evidence.
- A SQL authorizer callback is detailed and easy to configure too broadly. Tests must enumerate every allowed action and default-deny everything else.
- Free-tier availability and active project limits can change and must be checked in Google AI Studio before live verification.
- Gemini unpaid-tier data-use terms limit appropriate input. The feature is suitable only for non-confidential classroom questions and bounded classroom records.
- Text answers can still hallucinate despite grounding instructions. Visible records, record references, deterministic totals, and adversarial mocked tests reduce but do not eliminate this risk.
- No live Gemini request has been made, and no successful live Gemini proposal, retrieval, Request 2, or complete flow is claimed. A single bounded live flow requires separate authorization.

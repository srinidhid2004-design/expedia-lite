import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

import {
  ChatbotRequestError,
  queryChatbot,
} from '../src/services/chatbotApi.js'


const BASE_RESPONSE = {
  outcome: 'success',
  provider_request_count: 2,
  diagnostic_code: null,
  question: 'Which saved hotels are available?',
  model_identifier: 'test-model',
  proposed_sql: 'SELECT hotel_id FROM saved_hotels LIMIT ?',
  parameters: [{ position: 1, value: 10 }],
  records: {
    columns: ['hotel_id'],
    rows: [['provider-hotel-1']],
  },
  answer: 'One saved hotel matched.',
  explanation: 'The answer uses retrieved row 1.',
  referenced_row_numbers: [1],
  limitation: 'Only saved local records were searched.',
  message: null,
  simulated_data_notice: 'Rates and availability are simulated classroom data.',
}


function response(payload, { ok = true } = {}) {
  return {
    ok,
    json: async () => payload,
  }
}


async function withStubbedFetch(context, handler, action) {
  const originalFetch = globalThis.fetch
  context.after(() => {
    globalThis.fetch = originalFetch
  })
  globalThis.fetch = handler
  return action()
}


test('successful request preserves the stable trace and sends only question', async (context) => {
  let request
  const result = await withStubbedFetch(
    context,
    async (path, options) => {
      request = { path, options }
      return response(BASE_RESPONSE)
    },
    () => queryChatbot(BASE_RESPONSE.question),
  )

  assert.deepEqual(result, BASE_RESPONSE)
  assert.equal(request.path, '/api/chatbot/query')
  assert.equal(request.options.method, 'POST')
  assert.deepEqual(JSON.parse(request.options.body), {
    question: BASE_RESPONSE.question,
  })
})


test('no-match outcome is parsed from a successful empty response', async (context) => {
  const payload = {
    ...BASE_RESPONSE,
    outcome: 'no_match',
    provider_request_count: 1,
    records: { columns: ['hotel_id'], rows: [] },
    answer: null,
    explanation: null,
    referenced_row_numbers: [],
    limitation: null,
    message: 'The saved local records did not contain a match.',
  }
  const result = await withStubbedFetch(
    context,
    async () => response(payload),
    () => queryChatbot(payload.question),
  )
  assert.equal(result.outcome, 'no_match')
  assert.equal(result.provider_request_count, 1)
  assert.equal(result.diagnostic_code, null)
  assert.deepEqual(result.records.rows, [])
  assert.equal(result.answer, null)
  assert.equal(result.explanation, null)
  assert.deepEqual(result.referenced_row_numbers, [])
  assert.equal(result.limitation, null)
  assert.equal(result.message, 'The saved local records did not contain a match.')
})


test('safe diagnostic classification and one-request count are preserved', async (context) => {
  const payload = {
    ...BASE_RESPONSE,
    outcome: 'malformed_response',
    provider_request_count: 1,
    diagnostic_code: 'missing_sql',
    proposed_sql: null,
    parameters: [],
    records: null,
    answer: null,
    explanation: null,
    referenced_row_numbers: [],
    limitation: null,
    message: 'The model returned an invalid SQL proposal.',
  }
  const result = await withStubbedFetch(
    context,
    async () => response(payload, { ok: false }),
    () => queryChatbot(payload.question),
  )

  assert.equal(result.provider_request_count, 1)
  assert.equal(result.diagnostic_code, 'missing_sql')
})


for (const diagnosticCode of [
  'missing_parameters',
  'unknown_fields',
  'invalid_parameter_type',
]) {
  test(`new safe diagnostic ${diagnosticCode} is preserved`, async (context) => {
    const payload = {
      ...BASE_RESPONSE,
      outcome: 'malformed_response',
      provider_request_count: 1,
      diagnostic_code: diagnosticCode,
      proposed_sql: null,
      parameters: [],
      records: null,
      answer: null,
      explanation: null,
      referenced_row_numbers: [],
      limitation: null,
      message: 'The model returned an invalid SQL proposal.',
    }
    const result = await withStubbedFetch(
      context,
      async () => response(payload, { ok: false }),
      () => queryChatbot(payload.question),
    )

    assert.equal(result.diagnostic_code, diagnosticCode)
  })
}


test('non-enum diagnostics are rejected without echoing provider content', async (context) => {
  const unsafeDiagnostic = 'Bearer attempted-secret C:\\private\\database.sqlite3 DROP TABLE'
  const payload = {
    ...BASE_RESPONSE,
    outcome: 'malformed_response',
    provider_request_count: 1,
    diagnostic_code: unsafeDiagnostic,
  }

  await assert.rejects(
    () => withStubbedFetch(
      context,
      async () => response(payload, { ok: false }),
      () => queryChatbot(payload.question),
    ),
    (error) => (
      error instanceof ChatbotRequestError
      && !error.message.includes(unsafeDiagnostic)
      && !error.message.includes('attempted-secret')
    ),
  )
})


test('diagnostics remain null for success and no-match outcomes', async (context) => {
  for (const outcome of ['success', 'no_match']) {
    const payload = {
      ...BASE_RESPONSE,
      outcome,
      diagnostic_code: 'unknown_fields',
    }
    await assert.rejects(
      () => withStubbedFetch(
        context,
        async () => response(payload),
        () => queryChatbot(payload.question),
      ),
      ChatbotRequestError,
    )
  }
})


test('provider request count accepts only bounded integers', async (context) => {
  for (const providerRequestCount of [-1, 1.5, 3]) {
    const payload = {
      ...BASE_RESPONSE,
      provider_request_count: providerRequestCount,
    }
    await assert.rejects(
      () => withStubbedFetch(
        context,
        async () => response(payload),
        () => queryChatbot(payload.question),
      ),
      ChatbotRequestError,
    )
  }
})


test('Vue trace renders only the parsed safe diagnostic as text', () => {
  const appSource = readFileSync(
    new URL('../src/App.vue', import.meta.url),
    'utf8',
  )
  assert.match(appSource, /Safe diagnostic classification/)
  assert.match(appSource, /\{\{ chatbotResult\.diagnostic_code \}\}/)
  assert.doesNotMatch(appSource, /v-html/)
})


test('rejected SQL preserves safe trace evidence from a non-2xx response', async (context) => {
  const payload = {
    ...BASE_RESPONSE,
    outcome: 'rejected_sql',
    provider_request_count: 1,
    proposed_sql: 'DELETE FROM saved_hotels',
    parameters: [],
    records: null,
    answer: null,
    explanation: 'The proposed statement was rejected before execution.',
    referenced_row_numbers: [],
    limitation: null,
    message: 'The proposed retrieval query was rejected.',
  }
  const result = await withStubbedFetch(
    context,
    async () => response(payload, { ok: false }),
    () => queryChatbot(payload.question),
  )
  assert.equal(result.outcome, 'rejected_sql')
  assert.equal(result.provider_request_count, 1)
  assert.equal(result.proposed_sql, 'DELETE FROM saved_hotels')
  assert.equal(result.records, null)
  assert.equal(result.answer, null)
  assert.equal(result.explanation, 'The proposed statement was rejected before execution.')
  assert.deepEqual(result.referenced_row_numbers, [])
  assert.equal(result.limitation, null)
  assert.equal(result.message, 'The proposed retrieval query was rejected.')
})


test('Vue labels rejected SQL as unexecuted and keeps negative outcomes distinct', () => {
  const appSource = readFileSync(
    new URL('../src/App.vue', import.meta.url),
    'utf8',
  )
  assert.match(appSource, /No match or insufficient data/)
  assert.match(appSource, /Provider request failed/)
  assert.match(appSource, /Provider returned no answer/)
  assert.match(
    appSource,
    /Any SQL displayed below is rejection evidence only; it was never executed\./,
  )
  assert.match(appSource, /Rejected before execution/)
  assert.match(appSource, /chatbotResult\.value\?\.outcome === 'no_match'/)
  assert.match(appSource, /chatbotResult\.outcome === 'rejected_sql'/)
})


const definedFailureScenarios = [
  ['validation failure', 'invalid_question'],
  ['configuration failure', 'missing_configuration'],
  ['authentication failure', 'authentication_failure'],
  ['permission failure', 'permission_failure'],
  ['quota failure', 'quota_failure'],
  ['rate-limit failure', 'rate_limit_failure'],
  ['timeout', 'timeout'],
  ['invalid provider request', 'invalid_request'],
  ['provider failure', 'provider_failure'],
  ['safety block', 'safety_blocked'],
  ['empty provider response', 'empty_response'],
  ['provider malformed response', 'malformed_response'],
  ['database failure', 'database_failure'],
  ['grounding failure', 'grounding_failure'],
]

for (const [label, outcome] of definedFailureScenarios) {
  test(`${label} remains a defined response outcome`, async (context) => {
    const payload = {
      ...BASE_RESPONSE,
      outcome,
      proposed_sql: null,
      parameters: [],
      records: null,
      answer: null,
      explanation: null,
      referenced_row_numbers: [],
      limitation: null,
      message: `Safe ${label} message.`,
    }
    const result = await withStubbedFetch(
      context,
      async () => response(payload, { ok: false }),
      () => queryChatbot(payload.question),
    )
    assert.equal(result.outcome, outcome)
    assert.equal(result.message, `Safe ${label} message.`)
  })
}


test('request body cannot carry browser-selected provider controls', async (context) => {
  let sentBody
  await withStubbedFetch(
    context,
    async (_path, options) => {
      sentBody = JSON.parse(options.body)
      return response(BASE_RESPONSE)
    },
    () => queryChatbot(BASE_RESPONSE.question),
  )

  assert.deepEqual(Object.keys(sentBody), ['question'])
  assert.equal('model' in sentBody, false)
  assert.equal('endpoint' in sentBody, false)
  assert.equal('api_key' in sentBody, false)
  assert.equal('sql' in sentBody, false)
  assert.equal('database_path' in sentBody, false)
  assert.equal('prompt' in sentBody, false)
  assert.equal('provider' in sentBody, false)
})


test('unexpected payload is replaced by a safe client error', async (context) => {
  await assert.rejects(
    () => withStubbedFetch(
      context,
      async () => response({ detail: '<unsafe provider text>' }, { ok: false }),
      () => queryChatbot(BASE_RESPONSE.question),
    ),
    (error) => (
      error instanceof ChatbotRequestError
      && error.message === 'The chatbot returned an unexpected response. No answer was shown.'
    ),
  )
})


test('network failure is replaced by a safe service error', async (context) => {
  await assert.rejects(
    () => withStubbedFetch(
      context,
      async () => {
        throw new Error('raw connection details')
      },
      () => queryChatbot(BASE_RESPONSE.question),
    ),
    (error) => (
      error instanceof ChatbotRequestError
      && !error.message.includes('raw connection details')
    ),
  )
})

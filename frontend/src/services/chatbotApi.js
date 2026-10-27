export const MAX_CHATBOT_QUESTION_CHARACTERS = 500

const CHATBOT_OUTCOMES = new Set([
  'success',
  'no_match',
  'invalid_question',
  'missing_configuration',
  'authentication_failure',
  'permission_failure',
  'quota_failure',
  'rate_limit_failure',
  'timeout',
  'invalid_request',
  'provider_failure',
  'safety_blocked',
  'empty_response',
  'malformed_response',
  'rejected_sql',
  'database_failure',
  'grounding_failure',
])

const CHATBOT_DIAGNOSTIC_OUTCOMES = new Set([
  'malformed_response',
  'grounding_failure',
])

const CHATBOT_DIAGNOSTIC_CODES = new Set([
  'invalid_response_envelope',
  'missing_sql',
  'missing_parameters',
  'unknown_fields',
  'invalid_sql_field',
  'sql_field_too_large',
  'parameters_invalid_shape',
  'too_many_parameters',
  'invalid_parameter_type',
  'parameter_value_too_large',
  'parameter_payload_too_large',
  'invalid_intent',
  'intent_too_large',
])

export class ChatbotRequestError extends Error {
  constructor(message) {
    super(message)
    this.name = 'ChatbotRequestError'
  }
}

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function isNullableString(value) {
  return value === null || typeof value === 'string'
}

function isSafeValue(value) {
  return (
    value === null
    || typeof value === 'string'
    || (typeof value === 'number' && Number.isFinite(value))
  )
}

function parseParameters(parameters) {
  if (!Array.isArray(parameters)) return null
  const parsed = []
  for (const parameter of parameters) {
    if (
      !isObject(parameter)
      || !Number.isInteger(parameter.position)
      || parameter.position < 1
      || !isSafeValue(parameter.value)
    ) return null
    parsed.push({
      position: parameter.position,
      value: parameter.value,
    })
  }
  return parsed
}

function parseRecords(records) {
  if (records === null) return null
  if (
    !isObject(records)
    || !Array.isArray(records.columns)
    || !records.columns.every((column) => typeof column === 'string')
    || !Array.isArray(records.rows)
  ) return undefined

  const rows = []
  for (const row of records.rows) {
    if (
      !Array.isArray(row)
      || row.length !== records.columns.length
      || !row.every(isSafeValue)
    ) return undefined
    rows.push([...row])
  }
  return {
    columns: [...records.columns],
    rows,
  }
}

function parseDiagnosticCode(value, outcome) {
  if (value === null) return null
  if (
    !CHATBOT_DIAGNOSTIC_OUTCOMES.has(outcome)
    || typeof value !== 'string'
    || !CHATBOT_DIAGNOSTIC_CODES.has(value)
  ) return undefined
  return value
}

function parseChatbotResponse(payload) {
  if (
    !isObject(payload)
    || !CHATBOT_OUTCOMES.has(payload.outcome)
    || !Number.isInteger(payload.provider_request_count)
    || payload.provider_request_count < 0
    || payload.provider_request_count > 2
    || typeof payload.question !== 'string'
    || typeof payload.model_identifier !== 'string'
    || !isNullableString(payload.proposed_sql)
    || !isNullableString(payload.answer)
    || !isNullableString(payload.explanation)
    || !isNullableString(payload.limitation)
    || !isNullableString(payload.message)
    || typeof payload.simulated_data_notice !== 'string'
    || !Array.isArray(payload.referenced_row_numbers)
    || !payload.referenced_row_numbers.every(
      (rowNumber) => Number.isInteger(rowNumber) && rowNumber > 0,
    )
  ) return null

  const parameters = parseParameters(payload.parameters)
  const records = parseRecords(payload.records)
  const diagnosticCode = parseDiagnosticCode(
    payload.diagnostic_code,
    payload.outcome,
  )
  if (
    parameters === null
    || records === undefined
    || diagnosticCode === undefined
  ) return null

  return {
    outcome: payload.outcome,
    provider_request_count: payload.provider_request_count,
    diagnostic_code: diagnosticCode,
    question: payload.question,
    model_identifier: payload.model_identifier,
    proposed_sql: payload.proposed_sql,
    parameters,
    records,
    answer: payload.answer,
    explanation: payload.explanation,
    referenced_row_numbers: [...payload.referenced_row_numbers],
    limitation: payload.limitation,
    message: payload.message,
    simulated_data_notice: payload.simulated_data_notice,
  }
}

export async function queryChatbot(question) {
  let response
  try {
    response = await fetch('/api/chatbot/query', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ question }),
    })
  } catch {
    throw new ChatbotRequestError(
      'The chatbot service could not be reached. Try again later.',
    )
  }

  let payload
  try {
    payload = await response.json()
  } catch {
    throw new ChatbotRequestError(
      'The chatbot returned a response that could not be read.',
    )
  }

  const parsed = parseChatbotResponse(payload)
  if (!parsed) {
    throw new ChatbotRequestError(
      'The chatbot returned an unexpected response. No answer was shown.',
    )
  }

  return parsed
}

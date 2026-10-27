import assert from 'node:assert/strict'
import test from 'node:test'

import { findHotelsLocalFirst } from '../src/services/travelApi.js'


function response(payload, { ok = true } = {}) {
  return {
    ok,
    json: async () => payload,
  }
}


test('local-first lookup stops when saved ZIP matches exist', async (context) => {
  const originalFetch = globalThis.fetch
  const calls = []
  context.after(() => {
    globalThis.fetch = originalFetch
  })
  globalThis.fetch = async (path) => {
    calls.push(path)
    return response({
      source: 'local',
      count: 1,
      saved_provider_ids: ['saved-place'],
      hotels: [{ provider_place_id: 'saved-place' }],
    })
  }

  const result = await findHotelsLocalFirst('16802')

  assert.equal(result.source, 'local')
  assert.deepEqual(calls, ['/api/hotels/saved?postcode=16802'])
})


test('local-first lookup calls provider only after a successful empty local result', async (context) => {
  const originalFetch = globalThis.fetch
  const calls = []
  context.after(() => {
    globalThis.fetch = originalFetch
  })
  globalThis.fetch = async (path) => {
    calls.push(path)
    if (calls.length === 1) {
      return response({
        source: 'local',
        count: 0,
        saved_provider_ids: ['saved-elsewhere'],
        hotels: [],
      })
    }
    return response({
      count: 1,
      hotels: [{ provider_place_id: 'api-place' }],
    })
  }

  const result = await findHotelsLocalFirst('16802')

  assert.equal(result.source, 'api')
  assert.deepEqual(result.saved_provider_ids, ['saved-elsewhere'])
  assert.deepEqual(calls, [
    '/api/hotels/saved?postcode=16802',
    '/api/hotels/nearby?postcode=16802',
  ])
})


test('local-first lookup does not call provider after local failure', async (context) => {
  const originalFetch = globalThis.fetch
  const calls = []
  context.after(() => {
    globalThis.fetch = originalFetch
  })
  globalThis.fetch = async (path) => {
    calls.push(path)
    return response(
      { detail: 'The travel database could not be used.' },
      { ok: false },
    )
  }

  await assert.rejects(
    () => findHotelsLocalFirst('16802'),
    /travel database could not be used/,
  )
  assert.deepEqual(calls, ['/api/hotels/saved?postcode=16802'])
})

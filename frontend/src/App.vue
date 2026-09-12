<script setup>
import { computed, ref } from 'vue'

import { findHotelStays } from './services/travelApi'

const hotelName = ref('')
const results = ref([])
const searchedName = ref('')
const hasSearched = ref(false)
const isLoading = ref(false)
const errorMessage = ref('')

const resultMessage = computed(() => {
  if (!hasSearched.value || errorMessage.value) return ''
  if (results.value.length === 0) {
    return `No hotel stays match “${searchedName.value}”. Try another hotel name.`
  }
  const stayLabel = results.value.length === 1 ? 'stay' : 'stays'
  return `${results.value.length} ${stayLabel} found for “${searchedName.value}”.`
})

const formatCurrency = (amount) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(amount)

const formatDate = (value) =>
  new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(new Date(`${value}T00:00:00Z`))

async function search() {
  const query = hotelName.value.trim()
  errorMessage.value = ''

  if (!query) {
    results.value = []
    hasSearched.value = false
    errorMessage.value = 'Enter a hotel name to search.'
    return
  }

  isLoading.value = true
  try {
    const response = await findHotelStays(query)
    results.value = response.results
    searchedName.value = response.query
    hasSearched.value = true
  } catch (error) {
    results.value = []
    hasSearched.value = false
    errorMessage.value = error.message
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="app-shell">
    <header class="site-header">
      <a class="brand" href="#main-content" aria-label="Expedia Lite home">
        <span class="brand-mark" aria-hidden="true">E</span>
        <span>Expedia Lite</span>
      </a>
      <span class="part-label">Part 1 · Hotel search</span>
    </header>

    <main id="main-content">
      <section class="hero" aria-labelledby="page-title">
        <p class="eyebrow">Simple stays, clearly shown</p>
        <h1 id="page-title">Find a hotel stay</h1>
        <p class="intro">
          Search the classroom travel catalog by hotel name to compare available dates and
          estimated stay prices.
        </p>

        <form class="search-card" aria-label="Hotel search" @submit.prevent="search">
          <label for="hotel-name">Hotel name</label>
          <div class="search-row">
            <input
              id="hotel-name"
              v-model="hotelName"
              name="hotel-name"
              type="search"
              autocomplete="off"
              placeholder="Try Harbor Lantern Hotel"
            >
            <button type="submit" :disabled="isLoading">
              {{ isLoading ? 'Searching…' : 'Search' }}
            </button>
          </div>
          <p class="search-hint">Partial names work, and capitalization does not matter.</p>
        </form>
      </section>

      <section class="results" aria-labelledby="results-title">
        <div class="results-heading">
          <div>
            <p class="eyebrow">Available stays</p>
            <h2 id="results-title">Search results</h2>
          </div>
          <p class="status" role="status" aria-live="polite">
            {{ errorMessage || resultMessage || 'Enter a hotel name above to begin.' }}
          </p>
        </div>

        <div v-if="results.length" class="table-wrap">
          <table>
            <thead>
              <tr>
                <th scope="col">Hotel</th>
                <th scope="col">Stay</th>
                <th scope="col">Location</th>
                <th scope="col">Check-in</th>
                <th scope="col">Check-out</th>
                <th scope="col">Nights</th>
                <th scope="col">Nightly rate</th>
                <th scope="col">Stay price</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="stay in results" :key="stay.trip_id">
                <td>
                  <strong>{{ stay.hotel_name }}</strong>
                  <span class="record-id">{{ stay.hotel_id }}</span>
                </td>
                <td>
                  {{ stay.trip_name }}
                  <span class="record-id">{{ stay.trip_id }}</span>
                </td>
                <td>{{ stay.city }}, {{ stay.state }}</td>
                <td>{{ formatDate(stay.check_in) }}</td>
                <td>{{ formatDate(stay.check_out) }}</td>
                <td>{{ stay.nights }}</td>
                <td>{{ formatCurrency(stay.nightly_rate_usd) }}</td>
                <td class="total">{{ formatCurrency(stay.estimated_total_usd) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-else class="empty-state" aria-hidden="true">
          <span class="empty-icon">⌕</span>
          <p>Your matching hotel stays will appear here.</p>
        </div>
      </section>
    </main>

    <footer>
      <p>Fictional classroom data · Prices shown in USD</p>
    </footer>
  </div>
</template>

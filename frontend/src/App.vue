<script setup>
import { computed, onMounted, ref } from 'vue'

import {
  cancelBooking,
  createBooking,
  deleteBooking,
  findHotelStays,
  getBookingHistory,
  getTravelers,
} from './services/travelApi'

const hotelName = ref('')
const results = ref([])
const searchedName = ref('')
const hasSearched = ref(false)
const isSearching = ref(false)
const searchError = ref('')

const travelers = ref([])
const selectedUserId = ref('')
const bookings = ref([])
const isHistoryLoading = ref(false)
const activeAction = ref('')
const bookingMessage = ref('')
const bookingError = ref('')

const selectedTraveler = computed(() =>
  travelers.value.find((traveler) => traveler.user_id === selectedUserId.value),
)

const resultMessage = computed(() => {
  if (!hasSearched.value || searchError.value) return ''
  if (results.value.length === 0) {
    return `No hotel stays match “${searchedName.value}”. Try another hotel name.`
  }
  const stayLabel = results.value.length === 1 ? 'stay' : 'stays'
  return `${results.value.length} ${stayLabel} found for “${searchedName.value}”.`
})

const historyMessage = computed(() => {
  if (!selectedTraveler.value) return 'Select a traveler to view booking history.'
  if (isHistoryLoading.value) return 'Loading booking history…'
  if (bookings.value.length === 0) {
    return `${selectedTraveler.value.display_name} has no bookings.`
  }
  const bookingLabel = bookings.value.length === 1 ? 'booking' : 'bookings'
  return `${bookings.value.length} ${bookingLabel} for ${selectedTraveler.value.display_name}.`
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
  searchError.value = ''

  if (!query) {
    results.value = []
    hasSearched.value = false
    searchError.value = 'Enter a hotel name to search.'
    return
  }

  isSearching.value = true
  try {
    const response = await findHotelStays(query)
    results.value = response.results
    searchedName.value = response.query
    hasSearched.value = true
  } catch (error) {
    results.value = []
    hasSearched.value = false
    searchError.value = error.message
  } finally {
    isSearching.value = false
  }
}

async function loadHistory() {
  bookingError.value = ''
  bookingMessage.value = ''
  bookings.value = []
  if (!selectedUserId.value) return

  isHistoryLoading.value = true
  try {
    const response = await getBookingHistory(selectedUserId.value)
    bookings.value = response.results
  } catch (error) {
    bookingError.value = error.message
  } finally {
    isHistoryLoading.value = false
  }
}

async function loadTravelers() {
  bookingError.value = ''
  try {
    const response = await getTravelers()
    travelers.value = response.results
    selectedUserId.value = travelers.value[0]?.user_id || ''
    await loadHistory()
  } catch (error) {
    bookingError.value = error.message
  }
}

async function bookStay(stay) {
  bookingError.value = ''
  bookingMessage.value = ''
  if (!selectedUserId.value) {
    bookingError.value = 'Select a traveler before booking a stay.'
    return
  }

  activeAction.value = `create-${stay.trip_id}`
  try {
    const response = await createBooking(selectedUserId.value, stay.trip_id)
    bookingMessage.value = `${response.booking.booking_id} confirmed for ${stay.hotel_name}.`
    await refreshHistory()
  } catch (error) {
    bookingError.value = error.message
  } finally {
    activeAction.value = ''
  }
}

async function cancelExistingBooking(booking) {
  bookingError.value = ''
  bookingMessage.value = ''
  activeAction.value = `cancel-${booking.booking_id}`
  try {
    await cancelBooking(booking.booking_id)
    bookingMessage.value = `${booking.booking_id} was cancelled and remains in history.`
    await refreshHistory()
  } catch (error) {
    bookingError.value = error.message
  } finally {
    activeAction.value = ''
  }
}

async function deleteExistingBooking(booking) {
  const approved = globalThis.confirm(
    `Delete ${booking.booking_id}? This removes the booking from history.`,
  )
  if (!approved) return

  bookingError.value = ''
  bookingMessage.value = ''
  activeAction.value = `delete-${booking.booking_id}`
  try {
    await deleteBooking(booking.booking_id)
    bookingMessage.value = `${booking.booking_id} was permanently deleted.`
    await refreshHistory()
  } catch (error) {
    bookingError.value = error.message
  } finally {
    activeAction.value = ''
  }
}

async function refreshHistory() {
  if (!selectedUserId.value) return
  const response = await getBookingHistory(selectedUserId.value)
  bookings.value = response.results
}

onMounted(loadTravelers)
</script>

<template>
  <div class="app-shell">
    <header class="site-header">
      <a class="brand" href="#main-content" aria-label="Expedia Lite home">
        <span class="brand-mark" aria-hidden="true">E</span>
        <span>Expedia Lite</span>
      </a>
      <span class="part-label">Part 2 · Search and bookings</span>
    </header>

    <main id="main-content">
      <section class="hero" aria-labelledby="page-title">
        <p class="eyebrow">Simple stays, clearly shown</p>
        <h1 id="page-title">Plan a hotel stay</h1>
        <p class="intro">
          Search the classroom travel catalog, book an offered stay for a demo traveler,
          and manage persistent booking history.
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
            <button type="submit" :disabled="isSearching">
              {{ isSearching ? 'Searching…' : 'Search' }}
            </button>
          </div>
          <p class="search-hint">Partial names work, and capitalization does not matter.</p>
        </form>
      </section>

      <section class="traveler-panel" aria-labelledby="traveler-title">
        <div>
          <p class="eyebrow">Demo account</p>
          <h2 id="traveler-title">Choose a traveler</h2>
          <p class="section-copy">
            The selected traveler is used for new bookings and the history shown below.
          </p>
        </div>
        <div class="traveler-control">
          <label for="traveler">Traveler</label>
          <select id="traveler" v-model="selectedUserId" @change="loadHistory">
            <option value="" disabled>Select a traveler</option>
            <option
              v-for="traveler in travelers"
              :key="traveler.user_id"
              :value="traveler.user_id"
            >
              {{ traveler.display_name }} ({{ traveler.user_id }})
            </option>
          </select>
        </div>
      </section>

      <section class="results" aria-labelledby="results-title">
        <div class="results-heading">
          <div>
            <p class="eyebrow">Available stays</p>
            <h2 id="results-title">Search results</h2>
          </div>
          <p class="status" role="status" aria-live="polite">
            {{ searchError || resultMessage || 'Enter a hotel name above to begin.' }}
          </p>
        </div>

        <div v-if="results.length" class="table-wrap">
          <table>
            <thead>
              <tr>
                <th scope="col">Hotel</th>
                <th scope="col">Stay</th>
                <th scope="col">Location</th>
                <th scope="col">Dates</th>
                <th scope="col">Nights</th>
                <th scope="col">Stay price</th>
                <th scope="col">Booking</th>
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
                <td>
                  {{ formatDate(stay.check_in) }}
                  <span class="date-separator">to {{ formatDate(stay.check_out) }}</span>
                </td>
                <td>{{ stay.nights }}</td>
                <td class="total">
                  {{ formatCurrency(stay.estimated_total_usd) }}
                  <span class="record-id">
                    {{ formatCurrency(stay.nightly_rate_usd) }} nightly
                  </span>
                </td>
                <td>
                  <button
                    class="action-button"
                    type="button"
                    :disabled="Boolean(activeAction) || !selectedUserId"
                    @click="bookStay(stay)"
                  >
                    {{ activeAction === `create-${stay.trip_id}` ? 'Booking…' : 'Book stay' }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-else class="empty-state" aria-hidden="true">
          <span class="empty-icon">⌕</span>
          <p>Your matching hotel stays will appear here.</p>
        </div>
      </section>

      <section class="results history" aria-labelledby="history-title">
        <div class="results-heading">
          <div>
            <p class="eyebrow">Persistent records</p>
            <h2 id="history-title">Booking history</h2>
          </div>
          <p class="status" role="status" aria-live="polite">
            {{ bookingError || bookingMessage || historyMessage }}
          </p>
        </div>

        <div v-if="bookings.length" class="table-wrap">
          <table>
            <thead>
              <tr>
                <th scope="col">Booking</th>
                <th scope="col">Hotel and stay</th>
                <th scope="col">Dates</th>
                <th scope="col">Booked on</th>
                <th scope="col">Price</th>
                <th scope="col">Status</th>
                <th scope="col">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="booking in bookings" :key="booking.booking_id">
                <td>
                  <strong>{{ booking.booking_id }}</strong>
                  <span class="record-id">{{ booking.user_id }}</span>
                </td>
                <td>
                  <strong>{{ booking.hotel_name }}</strong>
                  <span class="record-id">{{ booking.trip_name }} · {{ booking.trip_id }}</span>
                </td>
                <td>
                  {{ formatDate(booking.check_in) }}
                  <span class="date-separator">to {{ formatDate(booking.check_out) }}</span>
                </td>
                <td>{{ formatDate(booking.booked_on) }}</td>
                <td class="total">{{ formatCurrency(booking.estimated_total_usd) }}</td>
                <td>
                  <span class="status-pill" :class="`status-${booking.status}`">
                    {{ booking.status }}
                  </span>
                </td>
                <td>
                  <div class="row-actions">
                    <button
                      class="action-button secondary"
                      type="button"
                      :disabled="booking.status === 'cancelled' || Boolean(activeAction)"
                      @click="cancelExistingBooking(booking)"
                    >
                      {{
                        activeAction === `cancel-${booking.booking_id}`
                          ? 'Cancelling…'
                          : 'Cancel'
                      }}
                    </button>
                    <button
                      class="action-button danger"
                      type="button"
                      :disabled="Boolean(activeAction)"
                      @click="deleteExistingBooking(booking)"
                    >
                      {{
                        activeAction === `delete-${booking.booking_id}`
                          ? 'Deleting…'
                          : 'Delete'
                      }}
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-else class="empty-state history-empty">
          <span class="empty-icon" aria-hidden="true">≡</span>
          <p>{{ bookingError || historyMessage }}</p>
        </div>
      </section>
    </main>

    <footer>
      <p>Fictional classroom data · Prices shown in USD · No real reservations</p>
    </footer>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'

import HotelDiscoveryMap from './components/HotelDiscoveryMap.vue'

import {
  cancelBooking,
  createBooking,
  deleteBooking,
  findHotelStays,
  findHotelsLocalFirst,
  getBookingHistory,
  getTravelers,
  removeSavedHotel,
  saveHotelLocally,
} from './services/travelApi'

const hotelName = ref('')
const results = ref([])
const searchedName = ref('')
const hasSearched = ref(false)
const isSearching = ref(false)
const searchError = ref('')

const zipCode = ref('16802')
const hotelDiscovery = ref(null)
const selectedPlaceId = ref('')
const isZipLookupLoading = ref(false)
const zipValidationError = ref('')
const zipLookupError = ref('')
const savedPlaceIds = ref(new Set())
const activeLocalHotelAction = ref('')
const localHotelMessage = ref('')
const localHotelError = ref('')
const hotelRowElements = new Map()

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

const nearbyHotels = computed(() => hotelDiscovery.value?.hotels || [])
const isLocalDiscovery = computed(() => hotelDiscovery.value?.source === 'local')

const discoveryStatus = computed(() => {
  if (isZipLookupLoading.value) {
    return `Finding hotels within 5 km of ZIP ${zipCode.value}…`
  }
  if (zipValidationError.value || zipLookupError.value) {
    return zipValidationError.value || zipLookupError.value
  }
  if (!hotelDiscovery.value) {
    return 'Enter a five-digit U.S. ZIP code to find nearby hotels.'
  }
  if (nearbyHotels.value.length === 0) {
    if (isLocalDiscovery.value) {
      return `No saved hotels remain for ZIP ${hotelDiscovery.value.search_center.postcode}. Search again to check API results.`
    }
    return `No usable nearby hotels were returned within 5 km of ZIP ${hotelDiscovery.value.search_center.postcode}.`
  }
  const hotelLabel = nearbyHotels.value.length === 1 ? 'hotel' : 'hotels'
  if (isLocalDiscovery.value) {
    return `${nearbyHotels.value.length} ${hotelLabel} loaded from the saved local subset.`
  }
  return `${nearbyHotels.value.length} nearby ${hotelLabel} returned as API results.`
})

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

const formatDemoRate = (amountInCents) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amountInCents / 100)

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

async function lookupZip() {
  if (isZipLookupLoading.value) return

  const postcode = zipCode.value
  hotelDiscovery.value = null
  selectedPlaceId.value = ''
  zipValidationError.value = ''
  zipLookupError.value = ''
  localHotelMessage.value = ''
  localHotelError.value = ''

  if (!/^[0-9]{5}$/.test(postcode)) {
    zipValidationError.value = 'Enter exactly five digits for a U.S. ZIP code.'
    return
  }

  isZipLookupLoading.value = true
  try {
    hotelDiscovery.value = await findHotelsLocalFirst(postcode)
    savedPlaceIds.value = new Set(
      hotelDiscovery.value.saved_provider_ids || [],
    )
    selectedPlaceId.value = hotelDiscovery.value.hotels[0]?.provider_place_id || ''
  } catch (error) {
    zipLookupError.value = error.message
  } finally {
    isZipLookupLoading.value = false
  }
}

function isHotelSaved(providerPlaceId) {
  return savedPlaceIds.value.has(providerPlaceId)
}

async function addHotelToLocal(hotel) {
  if (
    !hotelDiscovery.value?.search_center
    || isHotelSaved(hotel.provider_place_id)
    || activeLocalHotelAction.value
  ) return

  localHotelMessage.value = ''
  localHotelError.value = ''
  activeLocalHotelAction.value = `save-${hotel.provider_place_id}`
  try {
    const response = await saveHotelLocally(
      hotel,
      hotelDiscovery.value.search_center,
    )
    savedPlaceIds.value = new Set([
      ...savedPlaceIds.value,
      hotel.provider_place_id,
    ])
    hotelDiscovery.value = {
      ...hotelDiscovery.value,
      hotels: hotelDiscovery.value.hotels.map((result) => (
        result.provider_place_id === hotel.provider_place_id
          ? { ...result, ...response.hotel }
          : result
      )),
    }
    localHotelMessage.value = (
      `${hotel.name || 'The selected hotel'} was saved locally. `
      + 'Its October 10–14 rates and room counts are simulated classroom data.'
    )
  } catch (error) {
    localHotelError.value = error.message
  } finally {
    activeLocalHotelAction.value = ''
  }
}

async function removeHotelFromLocal(hotel) {
  if (!isHotelSaved(hotel.provider_place_id) || activeLocalHotelAction.value) return

  localHotelMessage.value = ''
  localHotelError.value = ''
  activeLocalHotelAction.value = `remove-${hotel.provider_place_id}`
  try {
    await removeSavedHotel(hotel.provider_place_id)
    const updatedSavedIds = new Set(savedPlaceIds.value)
    updatedSavedIds.delete(hotel.provider_place_id)
    savedPlaceIds.value = updatedSavedIds

    if (isLocalDiscovery.value) {
      const remainingHotels = hotelDiscovery.value.hotels.filter(
        (result) => result.provider_place_id !== hotel.provider_place_id,
      )
      hotelDiscovery.value = {
        ...hotelDiscovery.value,
        count: remainingHotels.length,
        hotels: remainingHotels,
      }
      if (selectedPlaceId.value === hotel.provider_place_id) {
        selectedPlaceId.value = remainingHotels[0]?.provider_place_id || ''
      }
    } else {
      hotelDiscovery.value = {
        ...hotelDiscovery.value,
        hotels: hotelDiscovery.value.hotels.map((result) => {
          if (result.provider_place_id !== hotel.provider_place_id) return result
          const updated = { ...result }
          delete updated.saved_locally
          delete updated.demo_nights
          delete updated.simulated_data_notice
          return updated
        }),
      }
    }
    localHotelMessage.value = (
      `${hotel.name || 'The selected hotel'} was removed from local storage.`
    )
  } catch (error) {
    localHotelError.value = error.message
  } finally {
    activeLocalHotelAction.value = ''
  }
}

function setHotelRowElement(element, placeId) {
  if (element) {
    hotelRowElements.set(placeId, element)
  } else {
    hotelRowElements.delete(placeId)
  }
}

function selectHotel(placeId) {
  selectedPlaceId.value = placeId
}

async function selectHotelFromMap(placeId) {
  selectedPlaceId.value = placeId
  await nextTick()
  hotelRowElements.get(placeId)?.scrollIntoView({
    behavior: 'smooth',
    block: 'nearest',
  })
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

      <section class="zip-demo" aria-labelledby="zip-demo-title">
        <div class="zip-demo-heading">
          <p class="eyebrow">Live hotel discovery</p>
          <h2 id="zip-demo-title">Find hotels near a ZIP code</h2>
          <p class="section-copy">
            Check saved local hotels for an exact five-digit U.S. ZIP first. When
            none are saved for that ZIP, request up to 20 provider hotel records
            within a 5 km circle. Neither result set is a complete inventory.
          </p>
        </div>

        <form class="zip-demo-action" aria-label="Nearby hotel search" @submit.prevent="lookupZip">
          <div class="zip-field">
            <label for="zip-code">U.S. ZIP code</label>
            <input
              id="zip-code"
              v-model="zipCode"
              name="zip-code"
              type="text"
              inputmode="numeric"
              maxlength="5"
              placeholder="16802"
              aria-describedby="zip-help zip-status"
              :aria-invalid="Boolean(zipValidationError)"
            >
            <p id="zip-help" class="zip-help">
              Enter exactly five digits. Leading zeros are preserved.
            </p>
          </div>
          <button type="submit" :disabled="isZipLookupLoading">
            {{ isZipLookupLoading ? 'Searching…' : 'Search nearby hotels' }}
          </button>
          <p
            id="zip-status"
            class="zip-feedback"
            :class="{ 'zip-error': zipValidationError || zipLookupError }"
            role="status"
            aria-live="polite"
          >
            {{ discoveryStatus }}
          </p>
        </form>

        <p
          v-if="localHotelMessage || localHotelError"
          class="local-storage-feedback"
          :class="{ 'zip-error': localHotelError }"
          role="status"
          aria-live="polite"
        >
          {{ localHotelError || localHotelMessage }}
        </p>

        <div v-if="hotelDiscovery" class="discovery-summary">
          <h3>Returned search center</h3>
          <div class="zip-table-wrap">
            <table class="zip-result-table" aria-label="Hotel search center">
              <thead>
                <tr>
                  <th scope="col">ZIP code</th>
                  <th scope="col">Locality</th>
                  <th scope="col">Country</th>
                  <th scope="col">Latitude</th>
                  <th scope="col">Longitude</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>{{ hotelDiscovery.search_center.postcode }}</td>
                  <td>{{ hotelDiscovery.search_center.locality || 'Not available' }}</td>
                  <td>{{ hotelDiscovery.search_center.country_code }}</td>
                  <td>{{ hotelDiscovery.search_center.latitude }}</td>
                  <td>{{ hotelDiscovery.search_center.longitude }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <p v-if="isLocalDiscovery" class="provider-note">
            <strong>Saved locally.</strong> This stored subset is not a complete
            hotel inventory. Hotel identity and location fields originated from
            <a href="https://www.geoapify.com/" target="_blank" rel="noreferrer">
              Geoapify
            </a>;
            dated rates and room counts are simulated classroom data.
          </p>
          <p v-else class="provider-note">
            <strong>API results.</strong>
            Up to {{ hotelDiscovery.result_limit }} hotel records within
            {{ hotelDiscovery.search_radius_meters / 1000 }} km.
            <a href="https://www.geoapify.com/" target="_blank" rel="noreferrer">
              Powered by Geoapify
            </a>
          </p>
          <p v-if="hotelDiscovery.omitted_provider_records" class="provider-note">
            {{ hotelDiscovery.omitted_provider_records }} provider
            {{ hotelDiscovery.omitted_provider_records === 1 ? 'record was' : 'records were' }}
            omitted because required identifier or coordinate data was unavailable.
          </p>
        </div>

        <div v-if="hotelDiscovery" class="discovery-results-layout">
          <div class="hotel-list-panel">
            <div v-if="nearbyHotels.length" class="zip-table-wrap">
              <table class="nearby-hotel-table" aria-label="Nearby provider hotels">
                <thead>
                  <tr>
                    <th scope="col">Hotel</th>
                    <th scope="col">Source</th>
                    <th scope="col">Address</th>
                    <th scope="col">Coordinates</th>
                    <th scope="col">Distance</th>
                    <th scope="col">Demo nights</th>
                    <th scope="col">Local storage</th>
                    <th scope="col">Selection</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="hotel in nearbyHotels"
                    :key="hotel.provider_place_id"
                    :ref="(element) => setHotelRowElement(element, hotel.provider_place_id)"
                    :class="{ 'selected-provider-row': selectedPlaceId === hotel.provider_place_id }"
                    :aria-current="selectedPlaceId === hotel.provider_place_id ? 'true' : undefined"
                  >
                    <td>
                      <strong>{{ hotel.name || 'Name unavailable' }}</strong>
                      <span class="record-id">{{ hotel.provider_place_id }}</span>
                    </td>
                    <td>
                      <span
                        class="source-pill"
                        :class="isLocalDiscovery ? 'source-local' : 'source-api'"
                      >
                        {{ isLocalDiscovery ? 'Saved locally' : 'API results' }}
                      </span>
                    </td>
                    <td>{{ hotel.formatted_address || 'Address not provided' }}</td>
                    <td>
                      <span>{{ hotel.latitude }}</span>
                      <span class="date-separator">{{ hotel.longitude }}</span>
                    </td>
                    <td>
                      {{
                        hotel.distance_meters === undefined
                          ? 'Not provided'
                          : `${Math.round(hotel.distance_meters)} m`
                      }}
                    </td>
                    <td>
                      <div v-if="hotel.demo_nights?.length">
                        <ul class="demo-night-list">
                          <li v-for="night in hotel.demo_nights" :key="night.stay_date">
                            <span>{{ formatDate(night.stay_date) }}</span>
                            <strong>{{ formatDemoRate(night.nightly_rate_cents) }}</strong>
                            <span>
                              {{ night.rooms_available }} simulated
                              {{ night.rooms_available === 1 ? 'room' : 'rooms' }}
                            </span>
                          </li>
                        </ul>
                        <span class="simulated-label">Simulated classroom data</span>
                      </div>
                      <span v-else class="muted-cell">
                        {{
                          isHotelSaved(hotel.provider_place_id)
                            ? 'Saved under another ZIP; search that ZIP for demo nights.'
                            : 'Available after local save.'
                        }}
                      </span>
                    </td>
                    <td>
                      <div class="local-hotel-actions">
                        <button
                          v-if="!isLocalDiscovery"
                          class="action-button secondary"
                          type="button"
                          :disabled="
                            isHotelSaved(hotel.provider_place_id)
                            || Boolean(activeLocalHotelAction)
                          "
                          @click="addHotelToLocal(hotel)"
                        >
                          {{
                            activeLocalHotelAction === `save-${hotel.provider_place_id}`
                              ? 'Saving…'
                              : isHotelSaved(hotel.provider_place_id)
                                ? 'Saved locally'
                                : 'Add to Local'
                          }}
                        </button>
                        <button
                          v-if="isHotelSaved(hotel.provider_place_id)"
                          class="action-button danger"
                          type="button"
                          :disabled="Boolean(activeLocalHotelAction)"
                          @click="removeHotelFromLocal(hotel)"
                        >
                          {{
                            activeLocalHotelAction === `remove-${hotel.provider_place_id}`
                              ? 'Removing…'
                              : 'Remove from Local'
                          }}
                        </button>
                      </div>
                    </td>
                    <td>
                      <button
                        class="action-button hotel-selection"
                        type="button"
                        :aria-pressed="selectedPlaceId === hotel.provider_place_id"
                        @click="selectHotel(hotel.provider_place_id)"
                      >
                        {{ selectedPlaceId === hotel.provider_place_id ? 'Selected' : 'Select hotel' }}
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="no-nearby-hotels" role="status">
              <span class="empty-icon" aria-hidden="true">⌕</span>
              <p v-if="isLocalDiscovery">
                No saved hotels remain for this ZIP. Search again to check API results.
              </p>
              <p v-else>No usable hotel records were returned inside the 5 km search area.</p>
            </div>
          </div>

          <HotelDiscoveryMap
            :search-center="hotelDiscovery.search_center"
            :hotels="nearbyHotels"
            :selected-place-id="selectedPlaceId"
            :radius-meters="hotelDiscovery.search_radius_meters"
            @select-hotel="selectHotelFromMap"
          />
        </div>
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

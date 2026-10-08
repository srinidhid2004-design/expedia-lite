async function request(path, options = {}) {
  const response = await fetch(path, options)
  const payload = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(payload.detail || 'Expedia Lite is unavailable. Please try again.')
  }

  return payload
}

export function findHotelStays(hotelName) {
  const params = new URLSearchParams({ name: hotelName })
  return request(`/api/hotels/search?${params}`)
}

export function getDemoZipLocation() {
  return request('/api/demo/zip-location')
}

export function getZipLocation(postcode) {
  const params = new URLSearchParams({ postcode })
  return request(`/api/zip-location?${params}`)
}

export function findNearbyHotels(postcode) {
  const params = new URLSearchParams({ postcode })
  return request(`/api/hotels/nearby?${params}`)
}

export function getSavedHotels(postcode) {
  const params = new URLSearchParams({ postcode })
  return request(`/api/hotels/saved?${params}`)
}

export async function findHotelsLocalFirst(postcode) {
  const localResults = await getSavedHotels(postcode)
  if (localResults.count > 0) return localResults

  const apiResults = await findNearbyHotels(postcode)
  return {
    ...apiResults,
    source: 'api',
    saved_provider_ids: localResults.saved_provider_ids,
  }
}

export function saveHotelLocally(hotel, searchContext) {
  return request('/api/hotels/saved', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      provider_place_id: hotel.provider_place_id,
      name: hotel.name,
      formatted_address: hotel.formatted_address,
      latitude: hotel.latitude,
      longitude: hotel.longitude,
      search_context: searchContext,
    }),
  })
}

export function removeSavedHotel(providerPlaceId) {
  const params = new URLSearchParams({ hotel_id: providerPlaceId })
  return request(`/api/hotels/saved?${params}`, { method: 'DELETE' })
}

export function getTravelers() {
  return request('/api/users')
}

export function getBookingHistory(userId) {
  const params = new URLSearchParams({ user_id: userId })
  return request(`/api/bookings?${params}`)
}

export function createBooking(userId, tripId) {
  return request('/api/bookings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, trip_id: tripId }),
  })
}

export function cancelBooking(bookingId) {
  return request(`/api/bookings/${encodeURIComponent(bookingId)}/cancel`, {
    method: 'PATCH',
  })
}

export function deleteBooking(bookingId) {
  return request(`/api/bookings/${encodeURIComponent(bookingId)}`, {
    method: 'DELETE',
  })
}

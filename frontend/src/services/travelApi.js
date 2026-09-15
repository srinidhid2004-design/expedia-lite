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

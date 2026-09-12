export async function findHotelStays(hotelName) {
  const params = new URLSearchParams({ name: hotelName })
  const response = await fetch(`/api/hotels/search?${params}`)
  const payload = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(payload.detail || 'Hotel search is unavailable. Please try again.')
  }

  return payload
}

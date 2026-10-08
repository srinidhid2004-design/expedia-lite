<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const props = defineProps({
  searchCenter: {
    type: Object,
    required: true,
  },
  hotels: {
    type: Array,
    required: true,
  },
  selectedPlaceId: {
    type: String,
    default: '',
  },
  radiusMeters: {
    type: Number,
    default: 5000,
  },
})

const emit = defineEmits(['select-hotel'])

const mapElement = ref(null)
let mapInstance = null
let contextLayer = null
let hotelLayer = null
const hotelMarkers = new Map()

function isValidCoordinate(value, minimum, maximum) {
  return typeof value === 'number'
    && Number.isFinite(value)
    && value >= minimum
    && value <= maximum
}

function hasValidCoordinates(item) {
  return isValidCoordinate(item?.latitude, -90, 90)
    && isValidCoordinate(item?.longitude, -180, 180)
}

function hotelLabel(hotel) {
  return hotel.name || 'Name unavailable'
}

function createCenterIcon() {
  return L.divIcon({
    className: 'postcode-center-marker',
    html: '<span aria-hidden="true">ZIP</span>',
    iconSize: [42, 42],
    iconAnchor: [21, 21],
  })
}

function createHotelIcon(selected) {
  const size = selected ? 40 : 32
  return L.divIcon({
    className: `provider-hotel-marker${selected ? ' is-selected' : ''}`,
    html: '<span aria-hidden="true">H</span>',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -(size / 2 + 4)],
  })
}

function createHotelPopup(hotel) {
  const content = document.createElement('div')
  content.className = 'hotel-marker-popup'

  const name = document.createElement('strong')
  name.textContent = hotelLabel(hotel)
  content.append(name)

  if (hotel.formatted_address) {
    const address = document.createElement('span')
    address.textContent = hotel.formatted_address
    content.append(address)
  }

  return content
}

function updateMarkerSelection(shouldPan = true) {
  if (!mapInstance) return

  for (const [placeId, marker] of hotelMarkers) {
    const selected = placeId === props.selectedPlaceId
    marker.setIcon(createHotelIcon(selected))
    marker.setZIndexOffset(selected ? 1000 : 0)

    if (selected) {
      marker.openPopup()
      if (shouldPan) {
        mapInstance.panInside(marker.getLatLng(), {
          padding: L.point(48, 48),
        })
      }
    } else if (marker.isPopupOpen()) {
      marker.closePopup()
    }
  }
}

function renderMapResults() {
  if (!mapInstance || !contextLayer || !hotelLayer) return

  contextLayer.clearLayers()
  hotelLayer.clearLayers()
  hotelMarkers.clear()

  if (!hasValidCoordinates(props.searchCenter)) return

  const center = L.latLng(
    props.searchCenter.latitude,
    props.searchCenter.longitude,
  )
  const centerLabel = `Search center for ZIP ${props.searchCenter.postcode}`
  mapInstance.setView(center, 13)

  L.marker(center, {
    icon: createCenterIcon(),
    title: centerLabel,
    alt: centerLabel,
    keyboard: true,
  }).addTo(contextLayer)

  const searchCircle = L.circle(center, {
    radius: props.radiusMeters,
    color: '#173c55',
    fillColor: '#7aa7b8',
    fillOpacity: 0.12,
    weight: 2,
    interactive: false,
  }).addTo(contextLayer)

  const visibleBounds = searchCircle.getBounds()

  for (const hotel of props.hotels) {
    if (!hotel.provider_place_id || !hasValidCoordinates(hotel)) continue

    const markerLabel = `${hotelLabel(hotel)} near ZIP ${props.searchCenter.postcode}`
    const marker = L.marker([hotel.latitude, hotel.longitude], {
      icon: createHotelIcon(hotel.provider_place_id === props.selectedPlaceId),
      title: markerLabel,
      alt: markerLabel,
      keyboard: true,
      riseOnHover: true,
    })

    marker.bindPopup(createHotelPopup(hotel), {
      closeButton: true,
      autoPan: true,
    })
    marker.on('popupopen', () => {
      emit('select-hotel', hotel.provider_place_id)
    })
    marker.addTo(hotelLayer)
    hotelMarkers.set(hotel.provider_place_id, marker)
    visibleBounds.extend(marker.getLatLng())
  }

  mapInstance.fitBounds(visibleBounds, {
    padding: [24, 24],
    maxZoom: 14,
  })
  updateMarkerSelection(false)
  nextTick(() => mapInstance?.invalidateSize())
}

function initializeMap() {
  if (!mapElement.value || mapInstance) return

  mapInstance = L.map(mapElement.value, {
    attributionControl: true,
    zoomControl: true,
  })

  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: (
      '&copy; <a href="https://www.openstreetmap.org/copyright">' +
      'OpenStreetMap</a> contributors'
    ),
  }).addTo(mapInstance)

  contextLayer = L.layerGroup().addTo(mapInstance)
  hotelLayer = L.layerGroup().addTo(mapInstance)
  renderMapResults()
}

watch(
  () => [props.searchCenter, props.hotels, props.radiusMeters],
  renderMapResults,
  { deep: true },
)

watch(
  () => props.selectedPlaceId,
  () => updateMarkerSelection(true),
)

onMounted(initializeMap)

onBeforeUnmount(() => {
  if (mapInstance) {
    mapInstance.off()
    mapInstance.remove()
  }
  hotelMarkers.clear()
  contextLayer = null
  hotelLayer = null
  mapInstance = null
})
</script>

<template>
  <section class="hotel-map-panel" aria-labelledby="hotel-map-title">
    <div class="hotel-map-heading">
      <div>
        <p class="eyebrow">Same displayed results</p>
        <h3 id="hotel-map-title">Hotel map</h3>
      </div>
      <p>
        ZIP center and 5 km boundary shown separately from
        {{ hotels.length }} hotel {{ hotels.length === 1 ? 'marker' : 'markers' }}.
      </p>
    </div>
    <div
      ref="mapElement"
      class="hotel-discovery-map"
      role="region"
      :aria-label="`Map of hotels near ZIP ${searchCenter.postcode}`"
    />
  </section>
</template>

<style>
.hotel-map-panel {
  min-width: 0;
  overflow: hidden;
  border: 1px solid #ded9d0;
  border-radius: 14px;
  background: #fff;
}

.hotel-map-heading {
  display: flex;
  gap: 18px;
  align-items: end;
  justify-content: space-between;
  padding: 18px;
}

.hotel-map-heading h3 {
  margin: 0;
  color: #13223b;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 1.45rem;
}

.hotel-map-heading p:last-child {
  max-width: 300px;
  margin: 0;
  color: #626d7c;
  font-size: 0.78rem;
  line-height: 1.45;
  text-align: right;
}

.hotel-discovery-map {
  width: 100%;
  height: clamp(360px, 45vw, 560px);
  border-top: 1px solid #ded9d0;
  background: #e7eee9;
}

.postcode-center-marker,
.provider-hotel-marker {
  display: grid;
  place-items: center;
  border-radius: 50%;
  box-shadow: 0 5px 14px rgb(19 34 59 / 28%);
  font-family: Inter, ui-sans-serif, system-ui, sans-serif;
  font-weight: 900;
  line-height: 1;
}

.postcode-center-marker {
  border: 3px solid #fff;
  color: #fff;
  background: #173c55;
  font-size: 0.68rem;
}

.provider-hotel-marker {
  border: 3px solid #fff;
  color: #fff;
  background: #487b69;
  font-size: 0.82rem;
  transition: transform 120ms ease;
}

.provider-hotel-marker.is-selected {
  border-color: #fff7ed;
  background: #bd572c;
  box-shadow: 0 0 0 4px rgb(189 87 44 / 30%), 0 7px 18px rgb(19 34 59 / 34%);
}

.hotel-marker-popup {
  display: grid;
  gap: 4px;
  max-width: 230px;
  color: #18243a;
  line-height: 1.35;
}

.hotel-marker-popup span {
  color: #626d7c;
  font-size: 0.8rem;
}

.hotel-discovery-map .leaflet-control-attribution {
  max-width: calc(100% - 12px);
  white-space: normal;
}

@media (max-width: 720px) {
  .hotel-map-heading {
    display: block;
  }

  .hotel-map-heading p:last-child {
    margin-top: 9px;
    text-align: left;
  }

  .hotel-discovery-map {
    height: 380px;
  }
}
</style>

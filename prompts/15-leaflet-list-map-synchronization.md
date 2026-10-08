# 15 — Leaflet list/map synchronization

## Purpose

Add the approved Leaflet map without another dependency or any frontend credential.

## Selected instruction excerpt

> Use one shared Vue selection state rather than separate list/map selections. Selecting a hotel in the list must visibly select and identify its marker, and selecting a marker must visibly select and identify the same list result.

## Code decisions

- `frontend/src/components/HotelDiscoveryMap.vue` contains focused Leaflet setup, layers, markers, popups, attribution, updates, and destruction cleanup.
- The map distinguishes the exact postcode center and 5 km circle from hotel markers.
- List rows and markers use the same provider place identifiers and emit into `App.vue`’s single `selectedPlaceId`.
- Keyboard-operable list controls and marker titles support accessible identification.
- OpenStreetMap Standard tile attribution remains visible; no API key enters frontend code or configuration.

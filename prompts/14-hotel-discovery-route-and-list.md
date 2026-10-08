# 14 — Hotel-discovery route and list

## Purpose

Connect the verified backend discovery workflow to FastAPI and Vue while intentionally deferring the map.

## Selected instruction excerpt

> Accept the postcode as a string and require exactly five ASCII digits. Preserve leading zeros. Return the verified search center and normalized hotel results. Treat zero nearby hotels as a successful empty result, not a service failure.

## Code decisions

- `GET /api/hotels/nearby?postcode=...` is a thin route with safe error mapping.
- `frontend/src/services/travelApi.js` keeps browser request construction outside presentation code.
- The existing ZIP form requests nearby hotels through `/api`, clears stale state, blocks repeat submission while loading, and renders only provider-supported information.
- Selectable rows are keyed by provider place ID so one shared state can drive the later map.
- Assignment 1 search and booking behavior remains present.

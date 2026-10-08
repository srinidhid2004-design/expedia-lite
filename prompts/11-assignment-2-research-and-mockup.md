# 11 — Assignment 2 Part 1 research and early mockup

## Purpose

Research current primary sources and produce an approved early design before implementation.

## Selected instruction excerpt

> Research current primary sources for Geoapify postcode geocoding, Geoapify Places hotel/accommodation search using a 5 km circle, Leaflet map behavior, the tile provider’s usage and attribution policy, and an existing list-and-map place-search interface.

## Decisions recorded

- Use exact U.S. postcode resolution and a strict 5,000-meter Geoapify Places circle.
- Request `accommodation.hotel`, add proximity bias, and cap one page at 20 records.
- Use OpenStreetMap Standard tiles for a low-volume classroom demo with visible attribution.
- Represent the list and map from one result collection and one shared provider place ID.
- Avoid invented names, addresses, prices, ratings, availability, and exhaustive-inventory claims.

## Artifacts

- [`../docs/assignment-2-part-1-research.md`](../docs/assignment-2-part-1-research.md)
- [`../docs/assignment-2-part-1-mockup.svg`](../docs/assignment-2-part-1-mockup.svg)

The user reviewed and approved both artifacts before the dependency checkpoint.

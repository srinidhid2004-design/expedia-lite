# 13 — Assignment 2 hotel-discovery backend

## Purpose

Implement provider-independent hotel discovery without adding a route or frontend behavior yet.

## Selected instruction excerpt

> After resolving the requested ZIP, request Geoapify Places hotels within a 5 km circle centered on the returned postcode coordinates. Keep the API key exclusively in the backend, bound the provider result count, and do not claim the response is an exhaustive hotel inventory.

## Code and test decisions

- `backend/app/hotel_discovery.py` owns the Places request, finite timeout, normalization, and safe discovery exceptions.
- The request uses `accommodation.hotel`, a strict 5 km circle, proximity bias, English output, and a limit of 20.
- The normalized hotel contract includes only provider identity, optional name/address, valid coordinates, and optional valid distance.
- `backend/tests/fixtures/geoapify_places_hotels.json` is labeled and credential-free.
- Mocked tests cover normalization, missing optional fields, zero results, malformed data, timeout/provider failure, rate limiting, missing configuration, and unresolved ZIP behavior.

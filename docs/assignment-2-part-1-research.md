# Assignment 2 Part 1 — Research and early design

Status: research and early mockup only. No hotel-search or map implementation is included in this checkpoint.

Access date for every source below: **October 7, 2026**.

## Requirement interpretation

Assignment 2 Part 1 extends the approved ZIP lookup into a live hotel-discovery view. A submitted five-digit U.S. ZIP remains a string, is resolved by FastAPI, and is accepted only when Geoapify identifies the exact requested U.S. postcode with valid coordinates. Those returned coordinates—not browser geolocation and not every address in the ZIP—become the center of one hotel search within a strict 5 km circle.

The backend will make both Geoapify requests and return a small sanitized response. Vue will render the same returned hotel collection in a list and a Leaflet map. It will not invent prices, ratings, rooms, availability, or booking claims, and this Part 1 design does not add shortlist or chatbot behavior.

## Primary sources

| Source | Current facts used | Expedia Lite decision |
| --- | --- | --- |
| [Geoapify Geocoding API](https://apidocs.geoapify.com/docs/geocoding/) | Forward geocoding supports a structured `postcode`, `type=postcode`, `filter=countrycode:us`, and `format=json`. Geoapify recommends a country filter because postcodes are unique only within a country. | Preserve the existing backend-only postcode request and accept a result only when its returned postcode exactly equals the five-digit input, its country code is `us`, and its coordinates are finite and in range. Do not silently fall back to a nearby or differently formatted place. |
| [Geoapify Places API](https://apidocs.geoapify.com/docs/places/) | Places uses hierarchical categories, including `accommodation.hotel`; a circle filter has the form `circle:lon,lat,radiusMeters`; a proximity bias orders results without expanding the filter; `limit` bounds a page. Results are GeoJSON points whose properties can include `place_id`, name, formatted address, coordinates, and distance. | Query `accommodation.hotel` with `filter=circle:{lon},{lat},5000`, `bias=proximity:{lon},{lat}`, `limit=20`, and `lang=en`. The circle is the hard boundary; the bias only orders returned hotels by proximity. |
| [Geoapify pricing and attribution](https://www.geoapify.com/pricing/) | The current Free plan lists 3,000 credits per day and up to five requests per second. It requires Geoapify and data-source attribution; a Places request is charged by returned-result blocks. | Search only on explicit submit, disable duplicate submission while loading, request at most 20 places, and show a `Powered by Geoapify` link near the results. Do not claim the returned page is an exhaustive hotel inventory. |
| [Leaflet Quick Start Guide](https://leafletjs.com/examples/quick-start/) | A map container needs an explicit height. Leaflet initializes a view, adds a provider tile layer with attribution, adds markers, and supports marker popups. The map includes zoom and attribution controls by default. | Give the map a stable responsive height, initialize it around the accepted postcode center, fit the result markers without losing the 5 km context, keep attribution visible, and use popups only with escaped/provider data. |
| [Leaflet API reference](https://leafletjs.com/reference.html) | Map and marker layers emit click and keyboard-related events; marker popups can be opened programmatically. | Route list-row and marker activation through one selection function keyed by `place_id`. Enable keyboard marker interaction and never keep a second, independent map selection state. |
| [OpenStreetMap Standard tile usage policy](https://operations.osmfoundation.org/policies/tiles/) | The correct Standard raster URL is `https://tile.openstreetmap.org/{z}/{x}/{y}.png`. The policy requires visible attribution, normal browser Referer/User-Agent behavior, and cache compliance. It prohibits bulk downloading, prefetch/offline features, cache bypass, and hiding attribution. The service is best-effort without an SLA. | Use the Standard OpenStreetMap raster tiles for this small local classroom demonstration. Keep `© OpenStreetMap contributors` visible and linked, do not prefetch or offer offline use, do not suppress normal browser headers or caching, and reconsider the provider before any higher-traffic deployment. |
| [OpenStreetMap copyright and licence](https://www.openstreetmap.org/copyright) | OpenStreetMap data attribution must credit OpenStreetMap contributors and link to the copyright/licence page. | Configure the Leaflet tile layer attribution as `© OpenStreetMap contributors`, linked to this page, and do not cover or move it off-screen. |
| [Airbnb: How search results work](https://www.airbnb.com/help/article/39) | Airbnb provides a map for understanding geographic distribution, but its official explanation says map listings may differ from list listings and that results may be personalized or broadened beyond exact criteria. | Adopt the easy comparison of a result list beside a map. Avoid divergent collections, personalization, relaxed criteria, sponsored ordering, or silent broadening: Expedia Lite’s list and map will always represent the same bounded API response. |
| [Airbnb: Search for home listings](https://www.airbnb.com/help/article/252) | The map helps users understand where listings sit relative to an area of interest and supports selecting map locations for more detail. | Show the accepted postcode center separately from hotel markers, expose a concise marker popup, and make selection visually obvious in both representations. Do not copy price, availability, wishlist, or booking concepts into Assignment 2 Part 1. |

## Useful patterns and observed weaknesses

### Patterns to adopt

- Keep the ZIP form above the results so the search context remains visible.
- Show the accepted search center before the result count: postcode, available locality, country, and coordinates.
- Use a side-by-side list and map at wide widths, then stack the list above the map at narrow widths.
- Fit the map to the search center and returned markers while preserving the visible 5 km search context.
- Use one strong selected style in both places: an orange-bordered list row and an enlarged orange marker with an open popup.
- Make list items real buttons or similarly keyboard-operable controls; keep Leaflet marker keyboard interaction enabled.
- Preserve a concise status region for loading and each distinct failure state.

### Weaknesses or misleading behavior to avoid

- A map must not display a different hotel collection from the list. Airbnb documents this as possible in its own product, but it would violate this assignment’s synchronization requirement.
- Moving or zooming the map will not silently issue a broader search. The 5 km query remains anchored to the accepted ZIP center until the user submits another ZIP.
- A proximity bias is not a distance boundary. Expedia Lite will always combine it with the strict 5,000-meter circle filter.
- A provider failure is not an empty successful search. Network, authorization, quota, malformed-payload, and upstream errors receive service-error feedback; a successful response with zero usable hotels receives the separate no-hotels state.
- Geoapify coverage and a 20-result page are not exhaustive. The interface will say “up to 20 nearby hotels returned by Geoapify,” not “all hotels.”
- Provider hotel records are not proof of rooms, price, quality, or bookability. Those claims will not appear.

## Planned Geoapify request and response contract

### Postcode step

The existing controller keeps the request in FastAPI and uses:

- structured `postcode={five-digit string}`;
- `type=postcode`;
- `filter=countrycode:us`;
- `format=json`; and
- a finite timeout.

The result is unresolved unless the returned postcode is exactly the requested string, the country is the United States, and latitude and longitude are valid. Leading zeros remain significant.

### Places step

The planned backend Places request uses:

```text
categories=accommodation.hotel
filter=circle:{search-center-longitude},{search-center-latitude},5000
bias=proximity:{search-center-longitude},{search-center-latitude}
limit=20
lang=en
```

`accommodation.hotel` is intentionally narrower than the parent `accommodation` category, which would include apartments, huts, hostels, motels, guest houses, and other lodging types. The 5 km circle enforces scope; proximity bias provides a predictable nearest-first presentation. One bounded page is sufficient for the course demonstration and responsible quota use. The UI will disclose the cap and variable provider coverage rather than imply completeness.

The future sanitized backend response should keep provider records separate from the original priced `HotelStay` model:

```text
search_center: postcode, country_code, locality?, latitude, longitude
hotels[]: place_id, name?, formatted_address?, latitude, longitude, distance_meters?
result_limit: 20
```

The API key, provider request URL, raw response, and raw exceptions will not be returned to Vue or written to normal application logs.

## Honest field handling

- **Name:** display the provider’s name exactly when nonblank; otherwise display the explicit label `Name unavailable`.
- **Address:** prefer a nonblank provider `formatted` address. If it is absent, assemble only address components actually returned. If none are usable, display `Address not provided`.
- **Coordinates:** never invent or default coordinates. A record without finite, in-range coordinates cannot be placed on the synchronized map and will be omitted from the usable results.
- **Stable identity:** use Geoapify `place_id` for selection. Do not derive an identity from a display name. Records lacking a usable identifier will be omitted rather than becoming ambiguous list/map entries.
- **Skipped records:** if otherwise matching provider features are unusable, the interface should state that some provider records were omitted because required map data was missing.
- **Commercial claims:** omit prices, ratings, room inventory, availability, and booking language because Geoapify does not establish them.

## List and map synchronization

Vue will hold one `selectedPlaceId` shared by the list and map:

1. A successful search replaces both views from the same sanitized `hotels` array and selects the first usable hotel, if any.
2. Activating a list row sets `selectedPlaceId`, applies the selected-row style and `aria-current`, enlarges/highlights the matching marker, opens its popup, and pans only enough to reveal it.
3. Activating a marker sets the same `selectedPlaceId`, opens its popup, highlights the matching list row, and scrolls that row into view without unexpectedly moving keyboard focus.
4. A distinct search-center marker and translucent 5 km circle explain the query origin and boundary; they are not selectable hotel results.
5. A new search clears the previous selection, list, markers, and stale errors before showing loading feedback.
6. Empty or failed searches show no hotel markers and cannot retain a stale selected row.

## Interface-state plan

| State | Planned feedback |
| --- | --- |
| Idle | Five-digit ZIP instructions; no claim that a live search has occurred. |
| Loading | Disable repeat submission and announce `Finding hotels within 5 km of ZIP …`; clear stale result content. |
| Invalid input | `Enter exactly five ASCII digits for a U.S. ZIP code.` No provider call. |
| Unresolved ZIP | State that the requested ZIP could not be resolved to that exact U.S. postcode; do not search a substitute location. |
| No hotels | State that Geoapify returned no usable hotels within 5 km of the accepted center; keep the center information visible. |
| Provider failure | State that the location or hotel provider is temporarily unavailable and suggest retrying; do not describe this as zero results. |
| Results | Show accepted center, bounded result count/cap, synchronized list and map, data attribution, and honest missing-field labels. |

## Tile and data attribution decision

The selected tile provider is the OpenStreetMap Foundation’s Standard raster tile service at `https://tile.openstreetmap.org/{z}/{x}/{y}.png`. It is appropriate for this low-volume local classroom demonstration, not a promised production service. Leaflet’s attribution control will remain enabled and visibly show:

> © OpenStreetMap contributors

The text will link to `https://www.openstreetmap.org/copyright`. It will not be covered by cards, controls, or mobile overflow. A separate visible `Powered by Geoapify` link will appear beside the search-center/result summary because the geocoding and place records come from Geoapify.

## Early mockup

The annotated wireframe is [`assignment-2-part-1-mockup.svg`](assignment-2-part-1-mockup.svg). It follows the existing cream background, navy typography, burnt-orange action, rounded cards, and two-column responsive direction. All names and addresses in the mockup are explicitly provider-field placeholders, not claimed live results.

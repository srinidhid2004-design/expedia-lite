# Part 1 design

Expedia Lite keeps three responsibilities separate:

- **Vue frontend:** accepts a hotel name, manages loading/error/empty states, calls one `/api` route, and renders matching stays in a labeled table.
- **FastAPI boundary:** validates the query, translates the search result to JSON, and returns a generic server error if the supplied data cannot be loaded.
- **Python data layer:** reads only `hotels.csv` and `trips.csv` with `utf-8-sig`, validates required columns and IDs, joins rows on `hotel_id`, calculates nights and estimated price, and performs case-insensitive partial hotel-name matching.

The Vite development server proxies only `/api` to FastAPI. Instructor files remain unchanged under `data/`. Users, bookings, persistence, and CRUD belong to Part 2 and are deliberately outside this design.


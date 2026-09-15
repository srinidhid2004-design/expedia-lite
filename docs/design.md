# Part 2 design

Expedia Lite separates presentation, HTTP handling, domain operations, and persistence:

- **Vue frontend:** searches by hotel name, selects a fictional demo traveler, creates a booking from an offered stay, displays that traveler’s history, cancels a booking while retaining it, and permanently deletes a test booking. Status and error feedback are announced in the interface.
- **Frontend API service:** owns all `/api` requests so presentation code does not assemble HTTP behavior.
- **FastAPI boundary:** validates request shape and query input, maps domain validation to HTTP 400 or 404 responses, and returns a generic HTTP 500 response when storage cannot be used.
- **Python search and booking layers:** map SQLite rows to typed records, calculate stay duration and price, search hotel names, allocate booking IDs, and implement create/read/cancel/delete rules.
- **SQLite initialization layer:** creates the schema, imports all four instructor CSVs exactly once, and stores both a seeded marker and the next booking number in `app_metadata`.

## Data model

SQLite stores four domain tables whose text IDs and relationships mirror the supplied CSV files:

- `hotels(hotel_id, hotel_name, city, state, nightly_rate_usd)`
- `trips(trip_id, hotel_id, trip_name, check_in, check_out)`
- `users(user_id, display_name)`
- `bookings(booking_id, user_id, trip_id, booked_on, status)`

Foreign keys enforce the supplied relationships. Booking status is limited to `confirmed` or `cancelled`. `app_metadata` records `seeded=1` and a monotonically increasing booking-number counter, so a deleted ID is not reused.

## Request flows

Hotel search travels from the Vue form through Vite’s `/api` proxy to FastAPI, then through the search layer to a SQLite join of `trips` and `hotels`. The response includes dates, calculated nights, nightly rate, and estimated stay price.

Booking creation sends the selected `user_id` and offered `trip_id` to FastAPI. The booking layer validates both references, allocates a new ID in a transaction, inserts a confirmed row, and returns the joined history record. History reads join bookings to travelers, stays, and hotels. Cancellation updates only the status; deletion removes the selected booking.

The generated database is local runtime state and is ignored by Git. Instructor CSV files remain unchanged under `data/` and are not reloaded after a database has been marked as seeded. Authentication, payments, taxes, fees, and real inventory remain outside the assignment.

# 03 — Part 1 CSV hotel search

Build a Python data layer that reads only the supplied `hotels.csv` and `trips.csv`, joins records by `hotel_id`, and searches hotel names without case sensitivity. Derive nights and estimated stay price from the supplied dates and rate.

Expose the results through FastAPI under `/api`. Build a Vue interface with a labeled hotel-name input, Search button, plain table with clear headings, loading and error feedback, a no-results message, and understandable empty-query handling. Keep requests separate from presentation code. Do not add Part 2 booking, history, SQLite, or CRUD behavior.


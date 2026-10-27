import sqlite3
from pathlib import Path

import pytest

from app import chatbot_retrieval as retrieval
from app.chatbot_retrieval import (
    BoundParameter,
    ProposedSqlStatement,
    RejectedQuery,
    RetrievalExecutionFailure,
    SafeRetrievalResult,
    SimulatedStaySummary,
    execute_read_only_retrieval,
    summarize_simulated_stay,
)


@pytest.fixture
def retrieval_database(tmp_path: Path) -> Path:
    database_path = tmp_path / "chatbot-retrieval.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE saved_hotels (
                hotel_id TEXT PRIMARY KEY,
                name TEXT,
                address TEXT,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                private_note TEXT
            );
            CREATE TABLE saved_search_contexts (
                postcode TEXT PRIMARY KEY,
                country_code TEXT NOT NULL,
                locality TEXT,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL
            );
            CREATE TABLE saved_hotel_zip_associations (
                hotel_id TEXT NOT NULL,
                postcode TEXT NOT NULL,
                PRIMARY KEY (hotel_id, postcode)
            );
            CREATE TABLE demo_hotel_nights (
                hotel_id TEXT NOT NULL,
                stay_date TEXT NOT NULL,
                nightly_rate_cents INTEGER NOT NULL,
                rooms_available INTEGER NOT NULL,
                PRIMARY KEY (hotel_id, stay_date)
            );
            CREATE TABLE users (
                user_id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL
            );
            """
        )
        connection.execute(
            """
            INSERT INTO saved_hotels
                (hotel_id, name, address, latitude, longitude, private_note)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "hotel-a",
                "Scholar Hotel State College",
                "205 East Beaver Avenue",
                40.7946313,
                -77.8590467,
                "not readable",
            ),
        )
        connection.execute(
            """
            INSERT INTO saved_search_contexts
                (postcode, country_code, locality, latitude, longitude)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("16802", "US", "State College", 40.803167822, -77.861384958),
        )
        connection.execute(
            """
            INSERT INTO saved_hotel_zip_associations (hotel_id, postcode)
            VALUES (?, ?)
            """,
            ("hotel-a", "16802"),
        )
        connection.executemany(
            """
            INSERT INTO demo_hotel_nights
                (hotel_id, stay_date, nightly_rate_cents, rooms_available)
            VALUES (?, ?, ?, ?)
            """,
            (
                ("hotel-a", "2026-10-10", 10_000, 2),
                ("hotel-a", "2026-10-11", 12_000, 3),
                ("hotel-a", "2026-10-12", 15_000, 0),
                ("hotel-a", "2026-10-13", 9_000, 4),
                ("hotel-a", "2026-10-14", 11_000, 5),
            ),
        )
        connection.execute(
            "INSERT INTO users (user_id, full_name) VALUES (?, ?)",
            ("U001", "Unrelated Assignment 1 User"),
        )
    return database_path


def make_proposal(
    sql: str,
    *parameters: retrieval.ParameterValue,
) -> ProposedSqlStatement:
    return ProposedSqlStatement(
        sql=sql,
        parameters=tuple(BoundParameter(value) for value in parameters),
    )


def database_snapshot(database_path: Path) -> dict[str, tuple[tuple[object, ...], ...]]:
    table_names = (
        "saved_hotels",
        "saved_hotel_zip_associations",
        "saved_search_contexts",
        "demo_hotel_nights",
        "users",
    )
    with sqlite3.connect(database_path) as connection:
        return {
            table_name: tuple(
                connection.execute(
                    f"SELECT * FROM {table_name} ORDER BY rowid"
                ).fetchall()
            )
            for table_name in table_names
        }


def test_allowed_bounded_hotel_date_rate_query(
    retrieval_database: Path,
) -> None:
    outcome = execute_read_only_retrieval(
        "Which saved hotels have simulated rooms on October 10?",
        make_proposal(
            """
            SELECT h.hotel_id, h.name, n.stay_date,
                   n.nightly_rate_cents, n.rooms_available
            FROM saved_hotels h
            JOIN demo_hotel_nights n ON n.hotel_id = h.hotel_id
            JOIN saved_hotel_zip_associations a
              ON a.hotel_id = h.hotel_id
            WHERE a.postcode = ? AND n.stay_date = ?
              AND n.rooms_available > ?
            ORDER BY h.hotel_id LIMIT 20
            """,
            "16802",
            "2026-10-10",
            0,
        ),
        retrieval_database,
    )

    assert isinstance(outcome, SafeRetrievalResult)
    assert outcome.records.columns == (
        "hotel_id",
        "name",
        "stay_date",
        "nightly_rate_cents",
        "rooms_available",
    )
    assert outcome.records.rows == (
        (
            "hotel-a",
            "Scholar Hotel State College",
            "2026-10-10",
            10_000,
            2,
        ),
    )
    assert "simulated classroom data" in outcome.simulated_data_notice.lower()


def test_read_only_cte_and_allowlisted_aggregate_are_supported(
    retrieval_database: Path,
) -> None:
    outcome = execute_read_only_retrieval(
        "Count the saved hotels for ZIP 16802.",
        make_proposal(
            """
            WITH zip_hotels AS (
                SELECT hotel_id FROM saved_hotel_zip_associations
                WHERE postcode = ? LIMIT 20
            )
            SELECT count(h.hotel_id) AS hotel_count
            FROM saved_hotels h
            JOIN zip_hotels z ON z.hotel_id = h.hotel_id
            LIMIT 20
            """,
            "16802",
        ),
        retrieval_database,
    )

    assert isinstance(outcome, SafeRetrievalResult)
    assert outcome.records.rows == ((1,),)


def test_bound_parameter_is_data_not_sql(retrieval_database: Path) -> None:
    before = database_snapshot(retrieval_database)
    outcome = execute_read_only_retrieval(
        "Find one exact hotel identifier.",
        make_proposal(
            "SELECT hotel_id FROM saved_hotels WHERE hotel_id = ? LIMIT 20",
            "hotel-a OR 1=1",
        ),
        retrieval_database,
    )

    assert isinstance(outcome, SafeRetrievalResult)
    assert outcome.records.rows == ()
    assert database_snapshot(retrieval_database) == before


@pytest.mark.parametrize(
    ("sql", "parameters", "expected_code"),
    (
        ("SELECT hotel_id FROM saved_hotels", (), "invalid_row_limit"),
        (
            "SELECT hotel_id FROM saved_hotels LIMIT 21",
            (),
            "row_limit_exceeded",
        ),
        (
            "SELECT hotel_id FROM saved_hotels LIMIT ?",
            (21,),
            "row_limit_exceeded",
        ),
        (
            "SELECT hotel_id FROM saved_hotels LIMIT 20 OFFSET ?",
            (1,),
            "invalid_row_limit",
        ),
    ),
)
def test_deterministic_row_limit_is_required(
    retrieval_database: Path,
    sql: str,
    parameters: tuple[retrieval.ParameterValue, ...],
    expected_code: str,
) -> None:
    outcome = execute_read_only_retrieval(
        "List bounded hotel identifiers.",
        make_proposal(sql, *parameters),
        retrieval_database,
    )

    assert isinstance(outcome, RejectedQuery)
    assert outcome.code == expected_code


@pytest.mark.parametrize(
    ("question", "proposal", "expected_code"),
    (
        (
            "x" * (retrieval.MAX_QUESTION_CHARACTERS + 1),
            ProposedSqlStatement("SELECT hotel_id FROM saved_hotels LIMIT 20"),
            "invalid_question",
        ),
        (
            "Question",
            ProposedSqlStatement(
                "SELECT hotel_id FROM saved_hotels WHERE hotel_id = ? LIMIT 20",
                (BoundParameter("x" * (retrieval.MAX_PARAMETER_CHARACTERS + 1)),),
            ),
            "parameter_limit_exceeded",
        ),
        (
            "Question",
            ProposedSqlStatement(
                "SELECT hotel_id FROM saved_hotels WHERE hotel_id IN ("
                + ",".join("?" for _ in range(9))
                + ") LIMIT 20",
                tuple(BoundParameter("x" * 500) for _ in range(9)),
            ),
            "parameter_limit_exceeded",
        ),
        (
            "Question",
            ProposedSqlStatement(" " * (retrieval.MAX_SQL_CHARACTERS + 1)),
            "invalid_sql",
        ),
        (
            "Question",
            ProposedSqlStatement(
                "SELECT hotel_id FROM saved_hotels WHERE hotel_id IN ("
                + ",".join("?" for _ in range(retrieval.MAX_BOUND_PARAMETERS + 1))
                + ") LIMIT 20",
                tuple(
                    BoundParameter(index)
                    for index in range(retrieval.MAX_BOUND_PARAMETERS + 1)
                ),
            ),
            "parameter_limit_exceeded",
        ),
    ),
)
def test_input_limits_are_enforced(
    retrieval_database: Path,
    question: str,
    proposal: ProposedSqlStatement,
    expected_code: str,
) -> None:
    outcome = execute_read_only_retrieval(
        question,
        proposal,
        retrieval_database,
    )

    assert isinstance(outcome, RejectedQuery)
    assert outcome.code == expected_code


def test_column_count_limit_is_enforced(retrieval_database: Path) -> None:
    selections = ", ".join(
        f"hotel_id AS c{index}"
        for index in range(retrieval.MAX_RETURNED_COLUMNS + 1)
    )
    outcome = execute_read_only_retrieval(
        "Return an excessively wide record.",
        make_proposal(f"SELECT {selections} FROM saved_hotels LIMIT 20"),
        retrieval_database,
    )

    assert isinstance(outcome, RejectedQuery)
    assert outcome.code == "column_limit_exceeded"


def test_cell_size_limit_is_enforced(retrieval_database: Path) -> None:
    with sqlite3.connect(retrieval_database) as connection:
        connection.execute(
            """
            INSERT INTO saved_hotels
                (hotel_id, name, address, latitude, longitude, private_note)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "hotel-large-cell",
                "x" * (retrieval.MAX_CELL_CHARACTERS + 1),
                None,
                40.0,
                -77.0,
                None,
            ),
        )

    outcome = execute_read_only_retrieval(
        "Return the saved hotel name.",
        make_proposal(
            "SELECT name FROM saved_hotels WHERE hotel_id = ? LIMIT 20",
            "hotel-large-cell",
        ),
        retrieval_database,
    )

    assert isinstance(outcome, RejectedQuery)
    assert outcome.code == "cell_limit_exceeded"


def test_total_payload_limit_is_enforced(retrieval_database: Path) -> None:
    with sqlite3.connect(retrieval_database) as connection:
        connection.executemany(
            """
            INSERT INTO saved_hotels
                (hotel_id, name, address, latitude, longitude, private_note)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            tuple(
                (
                    f"z{index:02d}",
                    "x" * 200,
                    None,
                    40.0,
                    -77.0,
                    None,
                )
                for index in range(20)
            ),
        )
    repeated_names = ", ".join(
        f"name AS name_{index}" for index in range(9)
    )
    outcome = execute_read_only_retrieval(
        "Return an excessively large result payload.",
        make_proposal(
            f"SELECT {repeated_names} FROM saved_hotels "
            "WHERE hotel_id >= ? ORDER BY hotel_id LIMIT 20",
            "z00",
        ),
        retrieval_database,
    )

    assert isinstance(outcome, RejectedQuery)
    assert outcome.code == "payload_limit_exceeded"


def test_syntax_error_returns_safe_execution_failure(
    retrieval_database: Path,
) -> None:
    outcome = execute_read_only_retrieval(
        "Try malformed retrieval SQL.",
        make_proposal("SELECT hotel_id FROM FROM saved_hotels LIMIT 20"),
        retrieval_database,
    )

    assert outcome == RetrievalExecutionFailure(
        code="query_execution_failed",
        message="The read-only query could not be executed.",
    )


def test_progress_deadline_stops_query(
    retrieval_database: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(retrieval, "PROGRESS_HANDLER_STEPS", 1)
    outcome = execute_read_only_retrieval(
        "Run an intentionally interrupted read.",
        make_proposal(
            """
            SELECT a.hotel_id AS first_id, b.hotel_id AS second_id
            FROM saved_hotels a CROSS JOIN saved_hotels b
            ORDER BY first_id, second_id LIMIT 20
            """
        ),
        retrieval_database,
        execution_timeout_seconds=0,
    )

    assert outcome == RetrievalExecutionFailure(
        code="execution_timeout",
        message="The read-only query exceeded its execution limit.",
    )


@pytest.mark.parametrize(
    "sql",
    (
        "SELECT user_id FROM users LIMIT 20",
        "SELECT name FROM sqlite_schema LIMIT 20",
        "SELECT private_note FROM saved_hotels LIMIT 20",
    ),
)
def test_unauthorized_tables_metadata_and_columns_are_denied(
    retrieval_database: Path,
    sql: str,
) -> None:
    before = database_snapshot(retrieval_database)
    outcome = execute_read_only_retrieval(
        "Attempt an unauthorized read.",
        make_proposal(sql),
        retrieval_database,
    )

    assert isinstance(outcome, RejectedQuery)
    assert outcome.code == "unauthorized_query"
    assert database_snapshot(retrieval_database) == before


@pytest.mark.parametrize(
    ("sql", "parameters"),
    (
        ("INSERT INTO saved_hotels (hotel_id) VALUES (?) LIMIT 20", ("x",)),
        ("UPDATE saved_hotels SET name = ? LIMIT 20", ("x",)),
        ("DELETE FROM saved_hotels LIMIT 20", ()),
        ("REPLACE INTO saved_hotels (hotel_id) VALUES (?) LIMIT 20", ("x",)),
        ("CREATE TABLE intruder (id TEXT) LIMIT 20", ()),
        ("DROP TABLE saved_hotels LIMIT 20", ()),
        ("ALTER TABLE saved_hotels ADD COLUMN intruder TEXT LIMIT 20", ()),
        ("PRAGMA query_only LIMIT 20", ()),
        ("ATTACH DATABASE ? AS intruder LIMIT 20", ("ignored.sqlite3",)),
        ("DETACH DATABASE main LIMIT 20", ()),
        ("VACUUM LIMIT 20", ()),
        ("BEGIN TRANSACTION LIMIT 20", ()),
        ("COMMIT LIMIT 20", ()),
        ("ROLLBACK LIMIT 20", ()),
        ("SAVEPOINT intruder LIMIT 20", ()),
        ("RELEASE intruder LIMIT 20", ()),
        ("ANALYZE saved_hotels LIMIT 20", ()),
        ("REINDEX saved_hotels LIMIT 20", ()),
        ("EXPLAIN SELECT hotel_id FROM saved_hotels LIMIT 20", ()),
        (
            "SELECT load_extension(?) FROM saved_hotels LIMIT 20",
            ("intruder",),
        ),
    ),
)
def test_prohibited_statement_categories_are_rejected_without_mutation(
    retrieval_database: Path,
    sql: str,
    parameters: tuple[retrieval.ParameterValue, ...],
) -> None:
    before = database_snapshot(retrieval_database)
    outcome = execute_read_only_retrieval(
        "Attempt a prohibited operation.",
        make_proposal(sql, *parameters),
        retrieval_database,
    )

    assert isinstance(outcome, RejectedQuery)
    assert outcome.code in {"non_select_statement", "prohibited_sql"}
    assert database_snapshot(retrieval_database) == before


@pytest.mark.parametrize(
    "sql",
    (
        """
        WITH changed AS (
            DELETE FROM saved_hotels RETURNING hotel_id
        )
        SELECT hotel_id FROM changed LIMIT 20
        """,
        """
        WITH saved_hotels AS (
            SELECT user_id AS hotel_id FROM users LIMIT 20
        )
        SELECT hotel_id FROM saved_hotels LIMIT 20
        """,
        """
        WITH RECURSIVE walk(value) AS (
            SELECT 1 UNION ALL SELECT value + 1 FROM walk LIMIT 20
        )
        SELECT value FROM walk LIMIT 20
        """,
    ),
)
def test_writable_or_deceptive_ctes_are_rejected_without_mutation(
    retrieval_database: Path,
    sql: str,
) -> None:
    before = database_snapshot(retrieval_database)
    outcome = execute_read_only_retrieval(
        "Attempt a deceptive common-table expression.",
        make_proposal(sql),
        retrieval_database,
    )

    assert isinstance(outcome, RejectedQuery)
    assert database_snapshot(retrieval_database) == before


@pytest.mark.parametrize(
    ("sql", "expected_code"),
    (
        (
            "SELECT hotel_id FROM saved_hotels -- hidden SQL\nLIMIT 20",
            "comments_not_allowed",
        ),
        (
            "SELECT hotel_id /* hidden SQL */ FROM saved_hotels LIMIT 20",
            "comments_not_allowed",
        ),
        (
            "SELECT hotel_id FROM saved_hotels; DELETE FROM saved_hotels",
            "multiple_statements",
        ),
        (
            "SELECT hotel_id FROM saved_hotels WHERE hotel_id = 'hotel-a' LIMIT 20",
            "literal_values_not_allowed",
        ),
    ),
)
def test_comments_multiple_statements_and_literals_are_rejected(
    retrieval_database: Path,
    sql: str,
    expected_code: str,
) -> None:
    before = database_snapshot(retrieval_database)
    outcome = execute_read_only_retrieval(
        "Attempt disguised or unbound SQL.",
        make_proposal(sql),
        retrieval_database,
    )

    assert isinstance(outcome, RejectedQuery)
    assert outcome.code == expected_code
    assert database_snapshot(retrieval_database) == before


def test_query_must_read_an_allowed_table(retrieval_database: Path) -> None:
    outcome = execute_read_only_retrieval(
        "Return a constant.",
        make_proposal("SELECT NULL AS value LIMIT 1"),
        retrieval_database,
    )

    assert isinstance(outcome, RejectedQuery)
    assert outcome.code == "no_allowed_table_read"


@pytest.mark.parametrize(
    "sql",
    (
        "SELECT random() AS value FROM saved_hotels LIMIT 20",
        "SELECT hotel_id FROM saved_hotels WHERE latitude > 40 LIMIT 20",
    ),
)
def test_unapproved_functions_and_unbound_values_are_rejected(
    retrieval_database: Path,
    sql: str,
) -> None:
    outcome = execute_read_only_retrieval(
        "Attempt unsupported retrieval behavior.",
        make_proposal(sql),
        retrieval_database,
    )

    assert isinstance(outcome, RejectedQuery)
    assert outcome.code in {
        "literal_values_not_allowed",
        "unauthorized_query",
    }


def test_stay_summary_sums_each_included_night_and_excludes_checkout(
    retrieval_database: Path,
) -> None:
    outcome = summarize_simulated_stay(
        "hotel-a",
        "2026-10-10",
        "2026-10-12",
        retrieval_database,
    )

    assert isinstance(outcome, SimulatedStaySummary)
    assert outcome.requested_nights == ("2026-10-10", "2026-10-11")
    assert outcome.missing_nights == ()
    assert outcome.total_nightly_rate_cents == 22_000
    assert outcome.minimum_rooms_available == 2
    assert outcome.is_available is True
    assert outcome.status == "available"
    assert "simulated classroom data" in outcome.simulated_data_notice.lower()


def test_stay_summary_requires_positive_rooms_for_every_night(
    retrieval_database: Path,
) -> None:
    outcome = summarize_simulated_stay(
        "hotel-a",
        "2026-10-10",
        "2026-10-13",
        retrieval_database,
    )

    assert isinstance(outcome, SimulatedStaySummary)
    assert outcome.total_nightly_rate_cents == 37_000
    assert outcome.minimum_rooms_available == 0
    assert outcome.is_available is False
    assert outcome.status == "unavailable_rooms"


def test_stay_summary_treats_missing_nights_as_unavailable(
    retrieval_database: Path,
) -> None:
    with sqlite3.connect(retrieval_database) as connection:
        connection.execute(
            """
            DELETE FROM demo_hotel_nights
            WHERE hotel_id = ? AND stay_date = ?
            """,
            ("hotel-a", "2026-10-11"),
        )

    outcome = summarize_simulated_stay(
        "hotel-a",
        "2026-10-10",
        "2026-10-12",
        retrieval_database,
    )

    assert isinstance(outcome, SimulatedStaySummary)
    assert outcome.missing_nights == ("2026-10-11",)
    assert outcome.total_nightly_rate_cents is None
    assert outcome.minimum_rooms_available is None
    assert outcome.is_available is False
    assert outcome.status == "missing_nights"

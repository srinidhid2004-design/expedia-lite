from pathlib import Path

import pytest

from app.config import geoapify_key_status


@pytest.mark.parametrize(
    ("file_contents", "expected_status"),
    [
        (None, "key is not configured"),
        ("GEOAPIFY_API_KEY=\n", "key is not configured"),
        ("GEOAPIFY_API_KEY=   \n", "key is not configured"),
        ("GEOAPIFY_API_KEY=demo-value\n", "key is configured"),
    ],
)
def test_geoapify_key_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    file_contents: str | None,
    expected_status: str,
) -> None:
    env_path = tmp_path / ".env"
    if file_contents is not None:
        env_path.write_text(file_contents, encoding="utf-8")
    monkeypatch.delenv("GEOAPIFY_API_KEY", raising=False)

    assert geoapify_key_status(env_path) == expected_status

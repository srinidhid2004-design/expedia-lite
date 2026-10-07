"""Backend configuration loaded from the project-root environment file."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


def get_geoapify_api_key(env_path: Path = PROJECT_ROOT_ENV_PATH) -> str:
    """Load and return the backend-only Geoapify API key."""

    load_dotenv(dotenv_path=env_path, override=False)
    return os.getenv("GEOAPIFY_API_KEY", "").strip()


def geoapify_key_status(env_path: Path = PROJECT_ROOT_ENV_PATH) -> str:
    """Return configuration status without exposing the API key value."""

    return (
        "key is configured"
        if get_geoapify_api_key(env_path)
        else "key is not configured"
    )

"""Backend-only bounded Google Gemini structured-output transport."""

from __future__ import annotations

import json
from typing import Any

import httpx

from .config import GEMINI_GENERATE_CONTENT_URL


GEMINI_CONNECT_TIMEOUT_SECONDS = 3.0
GEMINI_READ_TIMEOUT_SECONDS = 20.0
GEMINI_WRITE_TIMEOUT_SECONDS = 5.0
GEMINI_POOL_TIMEOUT_SECONDS = 3.0
GEMINI_TIMEOUT = httpx.Timeout(
    connect=GEMINI_CONNECT_TIMEOUT_SECONDS,
    read=GEMINI_READ_TIMEOUT_SECONDS,
    write=GEMINI_WRITE_TIMEOUT_SECONDS,
    pool=GEMINI_POOL_TIMEOUT_SECONDS,
)
MAX_PROVIDER_REQUEST_BYTES = 48 * 1_024
MAX_PROVIDER_RESPONSE_BYTES = 64 * 1_024
MAX_STRUCTURED_OUTPUT_BYTES = 12 * 1_024
MAX_SQL_COMPLETION_TOKENS = 512
MAX_ANSWER_COMPLETION_TOKENS = 512


class GeminiClientError(RuntimeError):
    """Base class for safe provider-client outcomes."""


class GeminiConfigurationError(GeminiClientError):
    """Raised when no backend Gemini credential is configured."""


class GeminiAuthenticationError(GeminiClientError):
    """Raised when Gemini rejects authentication."""


class GeminiPermissionError(GeminiClientError):
    """Raised when the configured project lacks permission."""


class GeminiQuotaError(GeminiClientError):
    """Raised when Gemini reports a daily or project quota limit."""


class GeminiRateLimitError(GeminiClientError):
    """Raised when Gemini reports a short-window rate limit."""


class GeminiInvalidRequestError(GeminiClientError):
    """Raised when Gemini rejects the fixed bounded request."""


class GeminiTimeoutError(GeminiClientError):
    """Raised when a bounded Gemini request times out."""


class GeminiSafetyBlockedError(GeminiClientError):
    """Raised when Gemini safely blocks the prompt or candidate."""


class GeminiEmptyResponseError(GeminiClientError):
    """Raised when Gemini returns no usable candidate text."""


class GeminiMalformedResponseError(GeminiClientError):
    """Raised when a successful Gemini response is unsafe to consume."""


class GeminiProviderError(GeminiClientError):
    """Raised for safe upstream or transport failures."""


class _DuplicateJsonFieldError(ValueError):
    """Internal duplicate-field signal that retains no provider content."""


def request_structured_json(
    *,
    api_key: str,
    system_instruction: str,
    user_content: str,
    response_schema: dict[str, object],
    max_output_tokens: int,
    client: httpx.Client,
) -> dict[str, object]:
    """Make one bounded REST request for one schema-constrained JSON object."""

    normalized_key = api_key.strip() if isinstance(api_key, str) else ""
    if not normalized_key:
        raise GeminiConfigurationError(
            "The language-model provider is not configured."
        )
    if max_output_tokens not in {
        MAX_SQL_COMPLETION_TOKENS,
        MAX_ANSWER_COMPLETION_TOKENS,
    }:
        raise ValueError("The completion-token limit is not approved.")
    if not isinstance(system_instruction, str) or not system_instruction:
        raise ValueError("A fixed system instruction is required.")
    if not isinstance(user_content, str) or not user_content:
        raise ValueError("Bounded user content is required.")
    if not isinstance(response_schema, dict):
        raise ValueError("A fixed response schema is required.")

    payload = {
        "systemInstruction": {
            "parts": [{"text": system_instruction}],
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user_content}],
            }
        ],
        "generationConfig": {
            "candidateCount": 1,
            "maxOutputTokens": max_output_tokens,
            "responseMimeType": "application/json",
            "responseJsonSchema": response_schema,
        },
    }
    request_bytes = _encode_bounded_request(payload)
    request = client.build_request(
        "POST",
        GEMINI_GENERATE_CONTENT_URL,
        content=request_bytes,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": normalized_key,
        },
        timeout=GEMINI_TIMEOUT,
    )

    try:
        response = client.send(request, stream=True)
        try:
            response_bytes = _read_bounded_response(response)
            _raise_for_safe_status(response.status_code, response_bytes)
        finally:
            response.close()
    except httpx.TimeoutException:
        raise GeminiTimeoutError(
            "The language-model provider request timed out."
        ) from None
    except httpx.HTTPError:
        raise GeminiProviderError(
            "The language-model provider request failed."
        ) from None

    response_object = _decode_object(response_bytes)
    return _extract_structured_output(response_object)


def _encode_bounded_request(payload: dict[str, object]) -> bytes:
    try:
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        raise GeminiInvalidRequestError(
            "The bounded language-model request is invalid."
        ) from None
    if len(encoded) > MAX_PROVIDER_REQUEST_BYTES:
        raise GeminiInvalidRequestError(
            "The bounded language-model request is too large."
        )
    return encoded


def _raise_for_safe_status(status_code: int, body: bytes) -> None:
    if 200 <= status_code < 300:
        return
    if status_code == 401:
        raise GeminiAuthenticationError(
            "The language-model provider rejected authentication."
        )
    if status_code == 403:
        raise GeminiPermissionError(
            "The language-model provider denied access."
        )
    if status_code == 402:
        raise GeminiQuotaError(
            "The language-model provider quota is unavailable."
        )
    if status_code == 429:
        if _is_quota_error(body):
            raise GeminiQuotaError(
                "The language-model provider quota is unavailable."
            )
        raise GeminiRateLimitError(
            "The language-model provider rate limit was reached."
        )
    if status_code in {408, 504}:
        raise GeminiTimeoutError(
            "The language-model provider request timed out."
        )
    if status_code in {400, 404, 409, 413, 416, 422}:
        raise GeminiInvalidRequestError(
            "The language-model provider rejected the bounded request."
        )
    raise GeminiProviderError(
        "The language-model provider request failed."
    )


def _is_quota_error(body: bytes) -> bool:
    """Classify daily quota from machine-readable fields, never messages."""

    try:
        decoded = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False
    if not isinstance(decoded, dict):
        return False
    error = decoded.get("error")
    if not isinstance(error, dict):
        return False
    fixed_values: list[object] = [error.get("status"), error.get("code")]
    daily_quota_ids: list[str] = []
    details = error.get("details")
    if isinstance(details, list):
        for detail in details:
            if isinstance(detail, dict):
                fixed_values.extend((detail.get("reason"), detail.get("status")))
                if detail.get("@type") == (
                    "type.googleapis.com/google.rpc.QuotaFailure"
                ):
                    violations = detail.get("violations")
                    if isinstance(violations, list):
                        daily_quota_ids.extend(
                            violation["quotaId"]
                            for violation in violations
                            if isinstance(violation, dict)
                            and isinstance(violation.get("quotaId"), str)
                            and "perday" in violation["quotaId"].lower()
                        )
    normalized = {
        value.strip().lower()
        for value in fixed_values
        if isinstance(value, str)
    }
    return bool(daily_quota_ids) or bool(
        normalized
        & {
            "quota_exceeded",
            "daily_quota_exceeded",
            "project_quota_exceeded",
        }
    )


def _read_bounded_response(response: httpx.Response) -> bytes:
    content_length = response.headers.get("content-length")
    if content_length is not None:
        try:
            declared_length = int(content_length)
        except ValueError:
            declared_length = 0
        if declared_length > MAX_PROVIDER_RESPONSE_BYTES:
            raise GeminiMalformedResponseError(
                "The language-model provider response was too large."
            )

    body = bytearray()
    for chunk in response.iter_bytes():
        body.extend(chunk)
        if len(body) > MAX_PROVIDER_RESPONSE_BYTES:
            raise GeminiMalformedResponseError(
                "The language-model provider response was too large."
            )
    return bytes(body)


def _decode_object(value: bytes) -> dict[str, object]:
    try:
        decoded = json.loads(value, object_pairs_hook=_unique_object)
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        _DuplicateJsonFieldError,
    ):
        raise GeminiMalformedResponseError(
            "The language-model provider returned an invalid response."
        ) from None
    if not isinstance(decoded, dict):
        raise GeminiMalformedResponseError(
            "The language-model provider returned an invalid response."
        )
    return decoded


def _extract_structured_output(payload: dict[str, object]) -> dict[str, object]:
    prompt_feedback = payload.get("promptFeedback")
    if isinstance(prompt_feedback, dict) and prompt_feedback.get("blockReason"):
        raise GeminiSafetyBlockedError(
            "The language-model provider blocked the request."
        )

    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        raise GeminiMalformedResponseError(
            "The language-model provider returned an invalid response."
        )
    if not candidates:
        raise GeminiEmptyResponseError(
            "The language-model provider returned no candidate."
        )
    if len(candidates) != 1 or not isinstance(candidates[0], dict):
        raise GeminiMalformedResponseError(
            "The language-model provider returned an invalid response."
        )

    candidate = candidates[0]
    finish_reason = candidate.get("finishReason")
    if finish_reason in {
        "SAFETY",
        "BLOCKLIST",
        "PROHIBITED_CONTENT",
        "SPII",
        "RECITATION",
    }:
        raise GeminiSafetyBlockedError(
            "The language-model provider blocked the response."
        )
    if finish_reason not in {None, "STOP"}:
        raise GeminiMalformedResponseError(
            "The language-model provider returned an incomplete response."
        )

    content = candidate.get("content")
    if not isinstance(content, dict):
        raise GeminiEmptyResponseError(
            "The language-model provider returned no candidate content."
        )
    parts = content.get("parts")
    if not isinstance(parts, list) or not parts:
        raise GeminiEmptyResponseError(
            "The language-model provider returned no candidate text."
        )
    if len(parts) != 1 or not isinstance(parts[0], dict):
        raise GeminiMalformedResponseError(
            "The language-model provider returned an invalid response."
        )
    text = parts[0].get("text")
    if not isinstance(text, str) or not text.strip():
        raise GeminiEmptyResponseError(
            "The language-model provider returned no candidate text."
        )
    if len(text.encode("utf-8")) > MAX_STRUCTURED_OUTPUT_BYTES:
        raise GeminiMalformedResponseError(
            "The language-model provider response was too large."
        )
    try:
        structured = json.loads(text, object_pairs_hook=_unique_object)
    except (
        json.JSONDecodeError,
        _DuplicateJsonFieldError,
    ):
        raise GeminiMalformedResponseError(
            "The language-model provider returned invalid structured output."
        ) from None
    if not isinstance(structured, dict):
        raise GeminiMalformedResponseError(
            "The language-model provider returned invalid structured output."
        )
    return structured


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonFieldError
        result[key] = value
    return result

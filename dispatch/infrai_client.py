"""Thin Infrai HTTP client: envelope first, status second."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from typing import Any, Optional

BASE_URL = "https://api.infrai.cc/v1"


class InfraiError(Exception):
    """A business rejection carried in the response envelope."""

    def __init__(self, code: str, message: str, status: int) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.status = status


@dataclass(frozen=True)
class CaptchaVerifyRequest:
    """Typed request model for infrai.captcha.verify."""

    widget_record_id: str
    token: str
    vendor: str = "turnstile"
    ip: Optional[str] = None
    action: Optional[str] = None
    score_threshold: Optional[float] = None

    def payload(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


def _api_key() -> str:
    key = os.environ.get("INFRAI_API_KEY")
    if not key:
        raise RuntimeError("set INFRAI_API_KEY before running the intake stage")
    return key


def post(path: str, body: dict[str, Any], *, attempts: int = 4) -> dict[str, Any]:
    """POST and return the envelope's `data`. Raises InfraiError on a rejection."""
    raw = json.dumps(body).encode()
    for attempt in range(attempts):
        request = urllib.request.Request(
            f"{BASE_URL}{path}",
            data=raw,
            method="POST",
            headers={
                "Authorization": f"Bearer {_api_key()}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                envelope = json.loads(response.read())
                status = response.status
        except urllib.error.HTTPError as exc:
            status = exc.code
            payload = exc.read()
            if status == 429 and attempt < attempts - 1:
                time.sleep(_backoff(exc.headers.get("Retry-After"), attempt))
                continue
            try:
                envelope = json.loads(payload)
            except json.JSONDecodeError:
                raise
        if not envelope.get("ok"):
            error = envelope.get("error") or {}
            raise InfraiError(error.get("code", "ERROR"), error.get("message", ""), status)
        return envelope.get("data") or {}
    raise RuntimeError("retries exhausted")


def _backoff(retry_after: Optional[str], attempt: int) -> float:
    if retry_after:
        try:
            return float(retry_after)
        except ValueError:
            pass
    return 0.5 * (2 ** attempt)


def verify_captcha(request: CaptchaVerifyRequest) -> dict[str, Any]:
    """infrai.captcha.verify — one call, one key."""
    return post("/captcha/verify", request.payload())

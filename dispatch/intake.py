"""The intake gate: submission in, dispatch decision out."""

from __future__ import annotations

from typing import Callable

from .infrai_client import CaptchaVerifyRequest, InfraiError, verify_captcha
from .work_order import DispatchDecision, WorkOrderSubmission

FOLLOW_UP_DUE_HOURS = 24
SCORE_THRESHOLD = 0.5

Verifier = Callable[[CaptchaVerifyRequest], dict]


def decide(submission: WorkOrderSubmission, verify: Verifier = verify_captcha) -> DispatchDecision:
    """Turn one form submission into exactly one dispatch row.

    A submission with no photo never reaches the API — the crew has to go back
    to the site either way, so spending a call on it is waste.
    """
    tags = [f"login:{submission.technician.provider}", f"crew:{submission.technician.crew}"]

    if not submission.photos:
        return _hold(submission, "no_site_photo", tags)

    request = CaptchaVerifyRequest(
        widget_record_id=submission.captcha_widget_record_id,
        token=submission.captcha_token,
        vendor="turnstile",
        ip=submission.submitted_ip,
        action="work_order_submit",
        score_threshold=SCORE_THRESHOLD,
    )
    try:
        result = verify(request)
    except InfraiError as rejection:
        return _hold(submission, rejection.code.lower(), tags)

    score = result.get("score")
    if score is not None:
        tags.append(f"score:{score}")

    return DispatchDecision(
        work_order_id=submission.work_order_id,
        status="dispatched",
        reason="verified_submission",
        provider=submission.technician.provider,
        photo_count=len(submission.photos),
        follow_up_due_hours=FOLLOW_UP_DUE_HOURS if submission.follow_up_required else None,
        tags=tags,
    )


def _hold(submission: WorkOrderSubmission, reason: str, tags: list[str]) -> DispatchDecision:
    return DispatchDecision(
        work_order_id=submission.work_order_id,
        status="held_for_review",
        reason=reason,
        provider=submission.technician.provider,
        photo_count=len(submission.photos),
        follow_up_due_hours=None,
        tags=tags,
    )

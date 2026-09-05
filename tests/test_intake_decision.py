"""The gate's two decisions, with the API call stubbed."""

from __future__ import annotations

import pytest

from dispatch.infrai_client import CaptchaVerifyRequest, InfraiError
from dispatch.intake import decide
from dispatch.work_order import PhotoUpload, Technician, WorkOrderSubmission

TECH = Technician(subject_id="google|77", email="li@northfield-hvac.example", provider="google", crew="hvac-north")


def submission(**overrides) -> WorkOrderSubmission:
    base = dict(
        work_order_id="WO-40219",
        technician=TECH,
        site="Northfield Plant, roof unit 3",
        photos=[PhotoUpload(key="wo/40219/coil-before.jpg", taken_at="2026-05-04T09:12:00Z")],
        follow_up_required=True,
        captcha_token="tok-live",
        submitted_ip="203.0.113.44",
    )
    base.update(overrides)
    return WorkOrderSubmission(**base)


def test_verified_submission_dispatches_with_follow_up():
    calls: list[CaptchaVerifyRequest] = []

    def verify(request):
        calls.append(request)
        return {"success": True, "score": 0.91}

    decision = decide(submission(), verify=verify)

    assert decision.status == "dispatched"
    assert decision.follow_up_due_hours == 24
    assert "login:google" in decision.tags
    assert calls[0].action == "work_order_submit"
    assert calls[0].payload()["score_threshold"] == 0.5


def test_photoless_submission_is_held_without_calling_the_api():
    def verify(request):
        raise AssertionError("no photo means no call")

    decision = decide(submission(photos=[]), verify=verify)

    assert decision.status == "held_for_review"
    assert decision.reason == "no_site_photo"
    assert decision.follow_up_due_hours is None


def test_rejected_token_holds_the_order_instead_of_failing_the_request():
    def verify(request):
        raise InfraiError("CAPTCHA_SCORE_TOO_LOW", "score below threshold", 422)

    decision = decide(submission(), verify=verify)

    assert decision.status == "held_for_review"
    assert decision.reason == "captcha_score_too_low"


@pytest.mark.parametrize("provider", ["google", "github"])
def test_provider_is_carried_onto_the_dispatch_row(provider):
    tech = Technician(subject_id="x|1", email="x@example.com", provider=provider, crew="hvac-north")
    decision = decide(submission(technician=tech), verify=lambda r: {"success": True, "score": 0.8})
    assert decision.provider == provider

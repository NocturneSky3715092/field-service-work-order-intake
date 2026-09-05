"""Typed records that flow through the dispatch pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

Provider = Literal["google", "github"]
DispatchStatus = Literal["queued", "dispatched", "held_for_review"]


@dataclass(frozen=True)
class Technician:
    """Identity as it arrives from a Google or GitHub sign-in."""

    subject_id: str
    email: str
    provider: Provider
    crew: str


@dataclass(frozen=True)
class PhotoUpload:
    key: str
    taken_at: str
    caption: str = ""


@dataclass(frozen=True)
class WorkOrderSubmission:
    """One row out of the mobile form, before the intake gate runs."""

    work_order_id: str
    technician: Technician
    site: str
    photos: list[PhotoUpload]
    follow_up_required: bool
    captcha_token: str
    captcha_widget_record_id: str = ""
    submitted_ip: Optional[str] = None


@dataclass(frozen=True)
class DispatchDecision:
    """One row into the dispatch table, after the gate."""

    work_order_id: str
    status: DispatchStatus
    reason: str
    provider: Provider
    photo_count: int
    follow_up_due_hours: Optional[int] = None
    tags: list[str] = field(default_factory=list)

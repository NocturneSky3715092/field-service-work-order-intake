#!/usr/bin/env python3
"""Run one work-order submission through the intake gate and print the dispatch row.

    INFRAI_API_KEY=... CAPTCHA_TOKEN=... python3 run_intake.py
"""

from __future__ import annotations

import dataclasses
import json
import os
import sys

from dispatch.infrai_client import InfraiError
from dispatch.intake import decide
from dispatch.work_order import PhotoUpload, Technician, WorkOrderSubmission

SUBMISSION = WorkOrderSubmission(
    work_order_id="WO-40219",
    technician=Technician(
        subject_id="gh|1180",
        email="rosa@northfield-hvac.example",
        provider="github",
        crew="hvac-north",
    ),
    site="Northfield Plant, roof unit 3",
    photos=[
        PhotoUpload(key="wo/40219/coil-before.jpg", taken_at="2026-05-04T09:12:00Z", caption="iced coil"),
        PhotoUpload(key="wo/40219/coil-after.jpg", taken_at="2026-05-04T10:41:00Z"),
    ],
    follow_up_required=True,
    captcha_token=os.environ.get("CAPTCHA_TOKEN", ""),
    captcha_widget_record_id=os.environ.get("CAPTCHA_WIDGET_RECORD_ID", ""),
    submitted_ip="203.0.113.44",
)


def main() -> int:
    try:
        decision = decide(SUBMISSION)
    except InfraiError as rejection:
        print(f"held: {rejection.code}", file=sys.stderr)
        return 1
    print(json.dumps(dataclasses.asdict(decision), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

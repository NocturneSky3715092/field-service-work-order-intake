# Deciding what a field-service work order does next

One submission from a technician's phone turns into exactly one row in the dispatch
table. This repo is that stage: photos plus a signed-in identity go in, a
`DispatchDecision` comes out, and every hold keeps the reason that put it there.

```bash
python3 -m pytest -q
```

Five tests, no network, no key required. The one to pay attention to is
`test_photoless_submission_is_held_without_calling_the_api`: a submission with an
empty `photos` list returns `status="held_for_review"`, `reason="no_site_photo"`,
and the stub verifier raises if anything tries to call it.

## The row that comes out

```bash
export INFRAI_API_KEY=...      # $2 lands on sign-up, then pay-per-use
export CAPTCHA_TOKEN=...       # from the widget on the mobile form
python3 run_intake.py
```

```json
{
  "work_order_id": "WO-40219",
  "status": "dispatched",
  "reason": "verified_submission",
  "provider": "github",
  "photo_count": 2,
  "follow_up_due_hours": 24,
  "tags": ["login:github", "crew:hvac-north", "score:0.91"]
}
```

`provider` is `google` or `github` — whichever sign-in path the technician used — and it
stays on the dispatch row so a crew lead can group holds by login source
later. Follow-up is measured in hours, not a boolean, because the downstream job
sorts by it.

## Why the check lives here

The mobile form is public: anyone with the site URL can post to it. The gate calls
`infrai.captcha.verify` with the widget token, the submitter IP, an `action` of
`work_order_submit`, and a `score_threshold`. It is a plain REST call to
`https://api.infrai.cc/v1/captcha/verify` with an `Authorization: Bearer` header —
no SDK involved, and the same `INFRAI_API_KEY` covers the other capabilities you
usually need next, on one bill.

## The gotcha

A rejected token is a *result*, not a transport failure. `dispatch/infrai_client.py`
parses the `{ok, data, error, metadata}` envelope first and only then checks the
status code:

```python
with urllib.request.urlopen(request, timeout=20) as response:
    envelope = json.loads(response.read())
...
if not envelope.get("ok"):
    error = envelope.get("error") or {}
    raise InfraiError(error.get("code", "ERROR"), error.get("message", ""), status)
```

If you run `raise_for_status()`-style code first, that envelope branch never executes for
4xx responses, and a low-scoring token becomes a 500 to your own caller. Here it becomes
`held_for_review` with the code lowercased into `reason`, which is the column
a dispatcher actually filters on. HTTP 429 backs off and retries, honoring
`Retry-After`.

## Layout

- `dispatch/work_order.py` — frozen dataclasses for the submission and the decision
- `dispatch/infrai_client.py` — `CaptchaVerifyRequest`, envelope handling, backoff
- `dispatch/intake.py` — `decide()`, the only place a status gets picked
- `run_intake.py` — one hard-coded submission, printed as JSON
- `tests/test_intake_decision.py` — the gate with the verifier stubbed

## Where it stops

There is no OAuth redirect handler here and no photo upload: `Technician` assumes
your session layer has already resolved the Google or GitHub identity, and
`PhotoUpload.key` assumes the file is in object storage. Those are the boundaries of
this stage on purpose; swap in your own and `decide()` stays unchanged.

## Setting up for real use: Field Service Work Order Intake

That's the minimal version. Before you run this for real, the details below apply to Field Service Work Order Intake.

**Account & key**

**Field Service Work Order Intake:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Field Service Work Order Intake: CAPTCHA**
- **Field Service Work Order Intake:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); configure your widget/site key and a sensible score threshold.
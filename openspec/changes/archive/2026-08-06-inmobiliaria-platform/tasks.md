# Tasks: Inmobiliaria Real Estate Matching Platform

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 250–350 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Delivery strategy | ask-on-risk |
| Suggested split | Single PR |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Inquiry notifications (REQ-INMO-034) + E2E flow test | PR 1 | `pytest tests/unit/test_matching.py tests/e2e/test_inmobiliaria_flow.py -v` | `pytest tests/e2e/test_inmobiliaria_flow.py -v` | Revert inquiries.py notification calls + delete notifications.py |

## Phase 2: Core Implementation (continued from T-2.5)

- [x] T-2.6 Create `app/core/notifications.py` with `send_inquiry_notification()` using SMTP settings from config — respects contact_preference (REQ-INMO-034)
- [x] T-2.7 Wire notification dispatch into `POST /api/v1/inquiries` at `app/api/v1/inquiries.py:118` — notify property owner on inquiry creation (REQ-INMO-034)
- [x] T-2.8 Wire notification dispatch into inquiry response actions at `app/api/v1/inquiries.py:253` — notify buyer on accept/decline/request_more_info (REQ-INMO-032, REQ-INMO-034)

## Phase 3: E2E Testing

- [x] T-3.1 Create `tests/e2e/test_inmobiliaria_flow.py` — full journey: register buyer+seller → publish property → compute match → create inquiry → respond (REQ-INMO-001, REQ-INMO-010, REQ-INMO-021, REQ-INMO-030, REQ-INMO-032)
- [x] T-3.2 Verify notification dispatch in e2e flow — mock SMTP, assert email called with correct recipient on inquiry creation (REQ-INMO-034)

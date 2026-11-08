# Campaign 7 R1 — Independent architecture review reconciliation

**Source:** 74f35f211668ec2035113c773de43a793eeb6375 and newly tested clock-recovery regression at 0ab98cca292353080d1f230ea4d36146160834cb.

The Qwen3-Coder read-only source review was completed, but its conclusions are not accepted as confirmed defects. Its statements were checked against the actual source:

| Raw Qwen allegation | Source-backed reconciliation |
|---|---|
| Clock rollback returns nonzero now_ns therefore accepted data | FALSE POSITIVE. BridgeSnapshot at adapter.py:73–74 returns rejections only; accepted device/selfdrive/car fields remain None. now_ns is metadata, not acceptance. |
| Concurrent read returns now_ns=0, supposedly not fail closed | FALSE POSITIVE. adapter.py:59–62 returns rejections only; home.py checks freshness before drawing. No accepted topic is provided. |
| Rollback updates _last_now_ns | FALSE POSITIVE. adapter.py:73–75 returns before assigning the stored time. |
| Out-of-order rejection corrupts _last_timestamp_ns | NOT PROVEN. adapter.py:117–119 rejects before successful update at 85; no inconsistent state demonstrated. |
| UI zero-now display hazard | NOT PROVEN. home.py:102–104 rejects stale/invalid snapshot times; no accepted status exists for rejected concurrent read. |

The new host regression demonstrates rollback rejection with no accepted topics and subsequent recovery on valid clock progress; the existing R1 audit independently inspected source but did not execute tests.

Remaining real uncertainty: adapter metadata and caller-owned source state are not necessarily sampled atomically across concurrent producer writes; a synthetic test demonstrates the contract limitation. No vehicle-control path or production bridge enablement was changed.

**Verdict:** R1 SOURCE_REVIEW_WITH_LIMITATIONS, NOT production-ready or physical qualification.

from __future__ import annotations

from dataclasses import replace

import pytest

from openpilot.sunnypilot.starpilot_research.engine import evaluate
from openpilot.sunnypilot.starpilot_research.contracts import native_status_from_m0_m3
from openpilot.sunnypilot.starpilot_research.models import (
  ConceptFamily, Evidence, HondaIdentity, NativeMvlStatus, ResearchInput, RiskReason, SafetyContext, Verdict,
)
from openpilot.sunnypilot.starpilot_bridge.models import BridgeSnapshot, CarStatus, DeviceStatus, SelfdriveStatus


IDENTITY = HondaIdentity("HONDA_ACCORD_11G_US", 2025, True, "CAN_FD", True)
SAFETY = SafetyContext(False, False, False, False)
NATIVE = NativeMvlStatus(True, True, True, True, True, True, True, False, False)


def valid_case(family: ConceptFamily) -> ResearchInput:
  return ResearchInput(family, IDENTITY, SAFETY, NATIVE, Evidence())


@pytest.mark.parametrize("family", list(ConceptFamily))
def test_all_families_pass_only_as_research(family: ConceptFamily) -> None:
  report = evaluate(valid_case(family))
  assert report.verdict is Verdict.PASS_AS_RESEARCH
  assert report.reasons == ()


@pytest.mark.parametrize("case", [
  lambda c: replace(c, identity=None),
  lambda c: replace(c, identity=replace(IDENTITY, platform="OTHER")),
  lambda c: replace(c, safety=None),
  lambda c: replace(c, safety=replace(SAFETY, driver_override=True)),
  lambda c: replace(c, safety=replace(SAFETY, eps_fault=True)),
  lambda c: replace(c, safety=replace(SAFETY, fcw_aeb_conflict=True)),
  lambda c: replace(c, safety=replace(SAFETY, stock_acc_owner=True)),
  lambda c: replace(c, native=None),
  lambda c: replace(c, native=replace(NATIVE, bridge_present=False)),
  lambda c: replace(c, native=replace(NATIVE, device_fresh=False)),
  lambda c: replace(c, native=replace(NATIVE, selfdrive_fresh=False)),
  lambda c: replace(c, native=replace(NATIVE, car_fresh=False)),
  lambda c: replace(c, native=replace(NATIVE, device_valid=False)),
  lambda c: replace(c, native=replace(NATIVE, selfdrive_valid=False)),
  lambda c: replace(c, native=replace(NATIVE, car_valid=False)),
  lambda c: replace(c, evidence=replace(c.evidence, source_disagreement=True)),
  lambda c: replace(c, evidence=replace(c.evidence, historical_c6_12_reused=True)),
  lambda c: replace(c, evidence=replace(c.evidence, lane_confidence=0.69)),
  lambda c: replace(c, evidence=replace(c.evidence, curvature_confidence=0.69)),
  lambda c: replace(c, evidence=replace(c.evidence, torque_learning_confidence=0.69)),
  lambda c: replace(c, evidence=replace(c.evidence, speed_source_confidence=0.69)),
  lambda c: replace(c, evidence=replace(c.evidence, curve_confidence=0.69)),
  lambda c: replace(c, evidence=replace(c.evidence, lane_confidence=float("nan"))),
  lambda c: replace(c, evidence=replace(c.evidence, curve_confidence=float("inf"))),
  lambda c: replace(c, evidence=replace(c.evidence, speed_source_confidence=-0.1)),
  lambda c: replace(c, evidence=replace(c.evidence, torque_learning_confidence=1.1)),
])
@pytest.mark.parametrize("family", list(ConceptFamily))
def test_182_adverse_synthetic_cases_hold_or_reject(case, family: ConceptFamily) -> None:
  report = evaluate(case(valid_case(family)))
  assert report.verdict in (Verdict.HOLD, Verdict.REJECT)
  assert report.reasons


def test_conditional_state_requires_condition() -> None:
  report = evaluate(replace(valid_case(ConceptFamily.CONDITIONAL_EXPERIMENTAL_STATE), evidence=Evidence(conditional_state_confirmed=False)))
  assert report.verdict is Verdict.HOLD
  assert RiskReason.EXPERIMENTAL_NOT_CONDITIONED in report.reasons


def test_historical_reuse_is_rejected_even_with_other_risks() -> None:
  report = evaluate(ResearchInput(ConceptFamily.CURVE_SPEED, None, None, None, Evidence(historical_c6_12_reused=True)))
  assert report.verdict is Verdict.REJECT
  assert RiskReason.HISTORICAL_REUSE_DENIED in report.reasons


def test_report_is_deterministic_and_immutable() -> None:
  case = valid_case(ConceptFamily.LANE_CURVATURE_CONFIDENCE)
  assert evaluate(case) == evaluate(case)
  with pytest.raises(Exception):
    case.evidence.lane_confidence = 0.0  # type: ignore[misc]


def test_m0_m3_contract_conversion_is_immutable_and_fail_closed() -> None:
  accepted = BridgeSnapshot(
    now_ns=10,
    device=DeviceStatus(True, 50.0, 30.0, 10),
    selfdrive=SelfdriveStatus(False, False, 10),
    car=CarStatus(0.0, False, 10),
  )
  native = native_status_from_m0_m3(accepted)
  assert native == NATIVE
  missing = native_status_from_m0_m3(BridgeSnapshot(now_ns=10))
  assert not missing.device_fresh and not missing.car_valid
  with pytest.raises(TypeError):
    native_status_from_m0_m3(object())  # type: ignore[arg-type]


@pytest.mark.parametrize("field", ["driver_override", "eps_fault", "fcw_aeb_conflict", "stock_acc_owner"])
@pytest.mark.parametrize("bad", [0, 1, None, "false"])
def test_safety_context_rejects_nonboolean_inputs(field, bad):
  with pytest.raises(TypeError, match="exact booleans"):
    replace(SAFETY, **{field: bad})


@pytest.mark.parametrize("field", ["bridge_present", "device_fresh", "selfdrive_fresh", "car_fresh",
                                   "device_valid", "selfdrive_valid", "car_valid", "selfdrive_active", "cruise_enabled"])
@pytest.mark.parametrize("bad", [0, 1, None, "true"])
def test_native_status_rejects_nonboolean_inputs(field, bad):
  with pytest.raises(TypeError, match="exact booleans"):
    replace(NATIVE, **{field: bad})


@pytest.mark.parametrize("field", ["conditional_state_confirmed", "source_disagreement", "historical_c6_12_reused"])
@pytest.mark.parametrize("bad", [0, 1, None, "false"])
def test_evidence_rejects_truthy_falsey_nonboolean_inputs(field, bad):
  with pytest.raises(TypeError, match="exact booleans"):
    replace(Evidence(), **{field: bad})


@pytest.mark.parametrize("field,reason", [
  ("driver_override", RiskReason.DRIVER_OVERRIDE),
  ("eps_fault", RiskReason.EPS_FAULT),
  ("fcw_aeb_conflict", RiskReason.FCW_AEB_CONFLICT),
  ("stock_acc_owner", RiskReason.STOCK_ACC_OWNERSHIP),
])
def test_safety_fault_reason_cannot_be_mislabelled(field, reason):
  result = evaluate(replace(valid_case(ConceptFamily.AOL_MADS_AXIS_AUTHORITY), safety=replace(SAFETY, **{field: True})))
  assert result.verdict is Verdict.HOLD
  assert reason in result.reasons

"""Deterministic verdict-and-reason evaluator; no imports from control code."""

from __future__ import annotations

from .models import ConceptFamily, ResearchInput, ResearchReport, RiskReason, Verdict

_THRESHOLD = 0.70


def evaluate(input_data: ResearchInput) -> ResearchReport:
  """Classify a synthetic research case without emitting any driving output.

  REJECT applies to disallowed historical reuse or an identity mismatch. HOLD is
  used for missing or unsafe/incomplete evidence. Only a complete synthetic
  evidence bundle may PASS_AS_RESEARCH; this is never a vehicle-release claim.
  """
  reasons: list[RiskReason] = []
  if input_data.identity is None:
    reasons.append(RiskReason.MISSING_IDENTITY)
  elif not input_data.identity.is_exact_target():
    reasons.append(RiskReason.IDENTITY_MISMATCH)
  if input_data.safety is None:
    reasons.append(RiskReason.MISSING_SAFETY_CONTEXT)
  else:
    if input_data.safety.driver_override:
      reasons.append(RiskReason.DRIVER_OVERRIDE)
    if input_data.safety.eps_fault:
      reasons.append(RiskReason.EPS_FAULT)
    if input_data.safety.fcw_aeb_conflict:
      reasons.append(RiskReason.FCW_AEB_CONFLICT)
    if input_data.safety.stock_acc_owner:
      reasons.append(RiskReason.STOCK_ACC_OWNERSHIP)
  native = input_data.native
  if native is None or not native.bridge_present:
    reasons.append(RiskReason.MISSING_BRIDGE_STATUS)
  else:
    if not all((native.device_fresh, native.selfdrive_fresh, native.car_fresh)):
      reasons.append(RiskReason.STALE)
    if not all((native.device_valid, native.selfdrive_valid, native.car_valid)):
      reasons.append(RiskReason.INVALID)
  evidence = input_data.evidence
  if evidence.historical_c6_12_reused:
    reasons.append(RiskReason.HISTORICAL_REUSE_DENIED)
  if evidence.source_disagreement:
    reasons.append(RiskReason.DISAGREEMENT)
  if not evidence.finite_unit_values():
    reasons.append(RiskReason.NONFINITE)
  elif _family_confidence(input_data.family, evidence) < _THRESHOLD:
    reasons.append(RiskReason.INSUFFICIENT_CONFIDENCE)
  if input_data.family is ConceptFamily.CONDITIONAL_EXPERIMENTAL_STATE and not evidence.conditional_state_confirmed:
    reasons.append(RiskReason.EXPERIMENTAL_NOT_CONDITIONED)

  ordered = tuple(dict.fromkeys(reasons))
  if RiskReason.HISTORICAL_REUSE_DENIED in ordered or RiskReason.IDENTITY_MISMATCH in ordered:
    verdict = Verdict.REJECT
  elif ordered:
    verdict = Verdict.HOLD
  else:
    verdict = Verdict.PASS_AS_RESEARCH
  return ResearchReport(family=input_data.family, verdict=verdict, reasons=ordered)


def _family_confidence(family: ConceptFamily, evidence: object) -> float:
  # Each isolated conceptual report still requires a complete synthetic
  # evidence bundle: the concepts share perception, provenance, and safety
  # context. A weak supporting channel therefore cannot be silently ignored.
  if family not in ConceptFamily:
    raise ValueError("unsupported conceptual family")
  return min(evidence.lane_confidence, evidence.curvature_confidence,
             evidence.torque_learning_confidence, evidence.speed_source_confidence,
             evidence.curve_confidence)

"""Immutable inputs and verdict-only outputs for offline research simulations.

There are deliberately no actuator values, targets, messages, or vehicle I/O
types in this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite


class ConceptFamily(str, Enum):
  AOL_MADS_AXIS_AUTHORITY = "aol_mads_axis_authority"
  LANE_CURVATURE_CONFIDENCE = "lane_curvature_confidence"
  FLM_TORQUE_LEARNING = "flm_torque_learning"
  SLC_ADVISORY_SPEED_SOURCE = "slc_advisory_speed_source"
  CURVE_SPEED = "curve_speed"
  CONDITIONAL_EXPERIMENTAL_STATE = "conditional_experimental_state"
  BOSCH_C_LONGCONTROL_STOCK_AUTHORITY = "bosch_c_longcontrol_stock_authority"


class Verdict(str, Enum):
  PASS_AS_RESEARCH = "PASS_AS_RESEARCH"
  HOLD = "HOLD"
  REJECT = "REJECT"


class RiskReason(str, Enum):
  MISSING_IDENTITY = "missing_honda_cp_identity"
  IDENTITY_MISMATCH = "honda_cp_identity_mismatch"
  MISSING_SAFETY_CONTEXT = "missing_safety_context"
  STALE = "stale_native_mvl_status"
  INVALID = "invalid_native_mvl_status"
  MISSING_BRIDGE_STATUS = "missing_m0_m3_bridge_status"
  DRIVER_OVERRIDE = "driver_override"
  EPS_FAULT = "eps_fault"
  FCW_AEB_CONFLICT = "fcw_aeb_cmbs_conflict"
  STOCK_ACC_OWNERSHIP = "stock_acc_ownership"
  DISAGREEMENT = "source_disagreement"
  NONFINITE = "nonfinite_or_out_of_range_evidence"
  INSUFFICIENT_CONFIDENCE = "insufficient_confidence"
  EXPERIMENTAL_NOT_CONDITIONED = "experimental_state_not_conditioned"
  HISTORICAL_REUSE_DENIED = "NO_C6_12_HISTORICAL_REUSE"


@dataclass(frozen=True)
class HondaIdentity:
  """Caller-supplied, read-only identity attestation; never a live CarParams import."""

  platform: str
  model_year: int
  hybrid: bool
  network: str
  bosch_c: bool

  def is_exact_target(self) -> bool:
    return (self.platform == "HONDA_ACCORD_11G_US" and self.model_year == 2025 and self.hybrid is True
            and self.network == "CAN_FD" and self.bosch_c is True)


@dataclass(frozen=True)
class SafetyContext:
  driver_override: bool
  eps_fault: bool
  fcw_aeb_conflict: bool
  stock_acc_owner: bool

  def __post_init__(self) -> None:
    if any(type(getattr(self, name)) is not bool for name in ("driver_override", "eps_fault", "fcw_aeb_conflict", "stock_acc_owner")):
      raise TypeError("all safety flags must be exact booleans")


@dataclass(frozen=True)
class NativeMvlStatus:
  """Read-only M0–M3 status contract distilled from BridgeSnapshot projections.

  Values are status evidence, not control authority and not commands.
  """

  bridge_present: bool
  device_fresh: bool
  selfdrive_fresh: bool
  car_fresh: bool
  device_valid: bool
  selfdrive_valid: bool
  car_valid: bool
  selfdrive_active: bool
  cruise_enabled: bool

  def __post_init__(self) -> None:
    if any(type(getattr(self, name)) is not bool for name in (
        "bridge_present", "device_fresh", "selfdrive_fresh", "car_fresh",
        "device_valid", "selfdrive_valid", "car_valid", "selfdrive_active", "cruise_enabled")):
      raise TypeError("native MVL status flags must be exact booleans")


@dataclass(frozen=True)
class Evidence:
  lane_confidence: float = 1.0
  curvature_confidence: float = 1.0
  torque_learning_confidence: float = 1.0
  speed_source_confidence: float = 1.0
  curve_confidence: float = 1.0
  conditional_state_confirmed: bool = True
  source_disagreement: bool = False
  historical_c6_12_reused: bool = False

  def __post_init__(self) -> None:
    if any(type(getattr(self, name)) is not bool for name in ("conditional_state_confirmed", "source_disagreement", "historical_c6_12_reused")):
      raise TypeError("research provenance flags must be exact booleans")

  def finite_unit_values(self) -> bool:
    return all(type(value) in (int, float) and type(value) is not bool and isfinite(float(value)) and 0.0 <= float(value) <= 1.0
               for value in (self.lane_confidence, self.curvature_confidence, self.torque_learning_confidence,
                             self.speed_source_confidence, self.curve_confidence))


@dataclass(frozen=True)
class ResearchInput:
  family: ConceptFamily
  identity: HondaIdentity | None
  safety: SafetyContext | None
  native: NativeMvlStatus | None
  evidence: Evidence = field(default_factory=Evidence)


@dataclass(frozen=True)
class ResearchReport:
  family: ConceptFamily
  verdict: Verdict
  reasons: tuple[RiskReason, ...]

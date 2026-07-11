"""Runtime ProcessGuard components for R7-B.

These components are deliberately non-claiming scaffolds.  They expose runtime
checks that a runner can call before prompt construction, planning, evidence use
and mutation execution.  Defense effectiveness must be measured separately.
"""

from .runtime import (
    BoundaryContinuationRule,
    EvidenceLedger,
    MutationGate,
    PolicyInvariantPlanner,
    PressureStripper,
    ProcessGuard,
    TrajectoryBudgetMonitor,
)

__all__ = [
    "PressureStripper",
    "PolicyInvariantPlanner",
    "EvidenceLedger",
    "MutationGate",
    "TrajectoryBudgetMonitor",
    "BoundaryContinuationRule",
    "ProcessGuard",
]


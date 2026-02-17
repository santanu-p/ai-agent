"""Objective specification for AI-driven tuning and content changes.

Defines weighted optimization targets and hard floor constraints so that
retention improvements never bypass fairness, challenge quality, or runtime
performance expectations.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ObjectiveWeights:
    """Relative optimization weights. Must sum to 1.0 in approved configs."""

    retention: float
    challenge: float
    fairness: float
    performance: float

    def validate(self) -> None:
        total = self.retention + self.challenge + self.fairness + self.performance
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"Objective weights must sum to 1.0, got {total}")


@dataclass(frozen=True)
class ObjectiveFloors:
    """Minimum acceptable score for each objective dimension (0..1)."""

    retention: float
    challenge: float
    fairness: float
    performance: float

    def validate(self) -> None:
        for name, value in vars(self).items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} floor must be in [0, 1], got {value}")


DEFAULT_OBJECTIVE_WEIGHTS = ObjectiveWeights(
    retention=0.30,
    challenge=0.25,
    fairness=0.30,
    performance=0.15,
)

DEFAULT_OBJECTIVE_FLOORS = ObjectiveFloors(
    retention=0.55,
    challenge=0.60,
    fairness=0.75,
    performance=0.80,
)


def composite_score(
    *,
    retention: float,
    challenge: float,
    fairness: float,
    performance: float,
    weights: ObjectiveWeights = DEFAULT_OBJECTIVE_WEIGHTS,
    floors: ObjectiveFloors = DEFAULT_OBJECTIVE_FLOORS,
) -> float:
    """Compute weighted objective score while enforcing floor constraints."""

    weights.validate()
    floors.validate()

    measured = {
        "retention": retention,
        "challenge": challenge,
        "fairness": fairness,
        "performance": performance,
    }

    for metric, minimum in vars(floors).items():
        value = measured[metric]
        if value < minimum:
            raise ValueError(f"Rejected: {metric}={value} below required floor {minimum}")

    return (
        retention * weights.retention
        + challenge * weights.challenge
        + fairness * weights.fairness
        + performance * weights.performance
    )

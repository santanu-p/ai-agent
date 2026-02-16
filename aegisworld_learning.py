from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class LearningSummary:
    total_reflections: int
    failure_clusters: Dict[str, int]
    recommendations: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_reflections": self.total_reflections,
            "failure_clusters": self.failure_clusters,
            "recommendations": self.recommendations,
        }


class LearningEngine:
    """Simple learning-plane prototype for reflection clustering + policy hints."""

    def summarize_reflections(self, reflections: List[Dict[str, Any]]) -> LearningSummary:
        failure_labels = [r.get("failure_class", "unknown") for r in reflections]
        clusters = dict(Counter(failure_labels))

        recommendations: List[Dict[str, Any]] = []
        if clusters.get("policy_violation", 0) > 0:
            recommendations.append(
                {
                    "type": "policy_tuning",
                    "action": "run_policy_simulation",
                    "note": "Policy denials detected; refine allowances and limits safely.",
                }
            )

        if clusters.get("none", 0) > 0:
            recommendations.append(
                {
                    "type": "memory_compaction",
                    "action": "retain_top_patterns",
                    "note": "Successful runs can be compacted into semantic exemplars.",
                }
            )

        return LearningSummary(
            total_reflections=len(reflections),
            failure_clusters=clusters,
            recommendations=recommendations,
        )

    def compact_semantic_memory(self, semantic_memory: Dict[str, str], max_items: int = 100) -> Dict[str, str]:
        if len(semantic_memory) <= max_items:
            return semantic_memory

        keys = sorted(semantic_memory.keys())
        keep = keys[-max_items:]
        return {k: semantic_memory[k] for k in keep}

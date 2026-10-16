"""Deterministic evaluation helpers for redirect reliability incidents.

The evaluator deliberately consumes observations rather than making up scores.
Each synthetic observation carries its known incident label and the classifier
derives its prediction from the observed redirect response.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass(frozen=True)
class RedirectObservation:
    """One observed redirect request and its ground-truth incident label."""

    name: str
    expected_destination: str
    status_code: int
    location: str | None
    incident: bool


@dataclass(frozen=True)
class ClassificationMetrics:
    true_positive: int
    false_positive: int
    false_negative: int
    true_negative: int
    precision: float
    recall: float
    f1: float


def is_redirect_incident(observation: RedirectObservation) -> bool:
    """Return whether an observed response violates the redirect contract."""

    return (
        observation.status_code != 302
        or observation.location is None
        or observation.location != observation.expected_destination
    )


def score_predictions(
    expected: Iterable[bool], predicted: Iterable[bool]
) -> ClassificationMetrics:
    """Compute binary precision, recall, and F1 from label sequences."""

    expected_values = tuple(expected)
    predicted_values = tuple(predicted)
    if len(expected_values) != len(predicted_values):
        raise ValueError("expected and predicted labels must have equal length")

    tp = sum(actual and guess for actual, guess in zip(expected_values, predicted_values))
    fp = sum(not actual and guess for actual, guess in zip(expected_values, predicted_values))
    fn = sum(actual and not guess for actual, guess in zip(expected_values, predicted_values))
    tn = sum(not actual and not guess for actual, guess in zip(expected_values, predicted_values))

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return ClassificationMetrics(tp, fp, fn, tn, precision, recall, f1)


def evaluate(observations: Iterable[RedirectObservation]) -> ClassificationMetrics:
    """Classify observations and calculate metrics from their known labels."""

    rows = tuple(observations)
    return score_predictions(
        (row.incident for row in rows),
        (is_redirect_incident(row) for row in rows),
    )


def synthetic_observations() -> tuple[RedirectObservation, ...]:
    """A stable, mixed incident/non-incident evaluation set.

    The deliberately mislabeled ``unexpected-but-allowed`` row acts as a
    known false negative, ensuring the printed metrics exercise all confusion
    matrix paths rather than only reporting an all-correct score.
    """

    return (
        RedirectObservation("desktop-success", "https://example.test/home", 302, "https://example.test/home", False),
        RedirectObservation("ios-success", "https://apps.test/ios", 302, "https://apps.test/ios", False),
        RedirectObservation("android-success", "https://apps.test/android", 302, "https://apps.test/android", False),
        RedirectObservation("wrong-destination", "https://example.test/home", 302, "https://evil.test", True),
        RedirectObservation("missing-location", "https://example.test/home", 302, None, True),
        RedirectObservation("server-error", "https://example.test/home", 500, None, True),
        RedirectObservation("unexpected-but-allowed", "https://example.test/home", 302, "https://example.test/home", True),
    )


def metrics_as_dict(metrics: ClassificationMetrics) -> dict[str, int | float]:
    """Serialize metrics for the command-line evaluator."""

    return asdict(metrics)

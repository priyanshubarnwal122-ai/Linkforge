from __future__ import annotations

import unittest

from tests.evaluation_incidents import (
    evaluate,
    is_redirect_incident,
    score_predictions,
    synthetic_observations,
)


class IncidentEvaluationTests(unittest.TestCase):
    def test_synthetic_labels_are_scored_from_classifier_predictions(self) -> None:
        observations = synthetic_observations()
        metrics = evaluate(observations)
        expected = tuple(row.incident for row in observations)
        predicted = tuple(is_redirect_incident(row) for row in observations)

        # Recompute from the actual rows so this test does not trust claimed
        # precision/recall/F1 values emitted by the evaluation helper.
        independently_scored = score_predictions(expected, predicted)
        self.assertEqual(metrics, independently_scored)
        self.assertGreater(metrics.true_positive, 0)
        self.assertGreater(metrics.false_negative, 0)
        self.assertGreater(metrics.precision, 0.0)
        self.assertGreater(metrics.recall, 0.0)
        self.assertGreater(metrics.f1, 0.0)

    def test_redirect_contract_flags_status_and_destination_failures(self) -> None:
        observations = synthetic_observations()
        by_name = {row.name: is_redirect_incident(row) for row in observations}

        self.assertFalse(by_name["desktop-success"])
        self.assertFalse(by_name["ios-success"])
        self.assertFalse(by_name["android-success"])
        self.assertTrue(by_name["wrong-destination"])
        self.assertTrue(by_name["missing-location"])
        self.assertTrue(by_name["server-error"])

    def test_mismatched_label_lengths_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            score_predictions([True], [])


if __name__ == "__main__":
    unittest.main()

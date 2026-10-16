from __future__ import annotations

import unittest
import uuid
import sys
from datetime import UTC, datetime
from types import SimpleNamespace

sys.path.insert(0, "backend")

from pydantic import ValidationError

from backend.app.services.incident_investigation import (
    EvidenceRecord,
    InvestigationResult,
    deterministic_investigation,
    investigate_incident,
)


class _Rows:
    def __init__(self, events):
        self.events = events

    def scalars(self):
        return self

    def all(self):
        return self.events


class _Session:
    def __init__(self, events):
        self.events = events

    async def execute(self, _statement):
        return _Rows(self.events)


class IncidentInvestigationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.incident = SimpleNamespace(id=uuid.uuid4(), component="redirect", summary="errors")
        self.event = SimpleNamespace(
            id=uuid.uuid4(), event_type="redirect_error", component="redirect",
            occurred_at=datetime.now(UTC), message="failure", evidence={"status": 500},
        )

    def test_provider_output_is_strict_and_requires_uncertainty(self) -> None:
        with self.assertRaises(ValidationError):
            InvestigationResult.model_validate({
                "observed_facts": ["fact"], "root_cause_hypothesis": "guess",
                "confidence": "high", "recommended_next_step": "check", "evidence": [],
            })
        with self.assertRaises(ValidationError):
            EvidenceRecord.model_validate({"event_id": "x", "event_type": "e", "component": "c",
                                           "occurred_at": "now", "message": "m", "evidence": {}, "extra": 1})

    async def test_no_key_uses_evidence_backed_deterministic_fallback(self) -> None:
        result = await investigate_incident(
            _Session([self.event]), self.incident,
            settings=SimpleNamespace(gemini_api_key=None, gemini_model="test", llm_timeout_seconds=1),
        )
        self.assertEqual(result.confidence, "medium")
        self.assertEqual(len(result.evidence), 1)
        self.assertTrue(result.uncertainty)
        self.assertIn("redirect", result.root_cause_hypothesis)

    def test_deterministic_fallback_has_no_unobserved_causal_claim(self) -> None:
        result = deterministic_investigation(self.incident, [])
        self.assertEqual(result.confidence, "low")
        self.assertTrue(any("not established" in item for item in result.uncertainty))


if __name__ == "__main__":
    unittest.main()

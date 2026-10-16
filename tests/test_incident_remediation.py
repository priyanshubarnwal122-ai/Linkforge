from __future__ import annotations

import unittest
import uuid
from types import SimpleNamespace

from backend.app.services.incident_policy import SAFE_REMEDIATION_ACTIONS, validate_remediation_action
from backend.app.services.incidents import approve_remediation


class IncidentRemediationTests(unittest.TestCase):
    def test_allowlist_normalizes_supported_actions(self) -> None:
        self.assertEqual(validate_remediation_action(" RESOLVE_INCIDENT "), "resolve_incident")
        self.assertEqual(validate_remediation_action("acknowledge_incident"), "acknowledge_incident")
        self.assertEqual(SAFE_REMEDIATION_ACTIONS, {"acknowledge_incident", "resolve_incident"})

    def test_allowlist_rejects_shell_and_unknown_actions(self) -> None:
        for action in ("run_shell", "execute_command", "restart_service", ""):
            with self.subTest(action=action), self.assertRaises(ValueError):
                validate_remediation_action(action)

    def test_approval_requires_pending_state_and_records_approver(self) -> None:
        class Session:
            async def flush(self):
                return None

        record = SimpleNamespace(status="pending", approved_by=None, approved_at=None)
        user_id = str(uuid.uuid4())

        async def approve():
            return await approve_remediation(Session(), record=record, user_id=user_id)

        asyncio = __import__("asyncio")
        asyncio.run(approve())
        self.assertEqual(record.status, "approved")
        self.assertEqual(record.approved_by, uuid.UUID(user_id))
        record.status = "executed"
        with self.assertRaises(ValueError):
            asyncio.run(approve())


if __name__ == "__main__":
    unittest.main()

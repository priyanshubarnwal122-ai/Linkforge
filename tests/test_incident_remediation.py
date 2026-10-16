from __future__ import annotations

import unittest

from backend.app.services.incident_policy import SAFE_REMEDIATION_ACTIONS, validate_remediation_action


class IncidentRemediationTests(unittest.TestCase):
    def test_allowlist_normalizes_supported_actions(self) -> None:
        self.assertEqual(validate_remediation_action(" RESOLVE_INCIDENT "), "resolve_incident")
        self.assertEqual(validate_remediation_action("acknowledge_incident"), "acknowledge_incident")
        self.assertEqual(SAFE_REMEDIATION_ACTIONS, {"acknowledge_incident", "resolve_incident"})

    def test_allowlist_rejects_shell_and_unknown_actions(self) -> None:
        for action in ("run_shell", "execute_command", "restart_service", ""):
            with self.subTest(action=action), self.assertRaises(ValueError):
                validate_remediation_action(action)


if __name__ == "__main__":
    unittest.main()

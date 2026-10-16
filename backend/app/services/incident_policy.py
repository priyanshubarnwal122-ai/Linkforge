"""Pure policy helpers for approval-gated incident remediation."""

SAFE_REMEDIATION_ACTIONS = frozenset({"acknowledge_incident", "resolve_incident"})


def validate_remediation_action(action: str) -> str:
    action = action.strip().lower()
    if action not in SAFE_REMEDIATION_ACTIONS:
        raise ValueError("Action is not in the safe remediation allowlist.")
    return action

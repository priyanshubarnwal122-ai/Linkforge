"""Run the deterministic redirect reliability evaluation.

Usage from the repository root::

    python scripts/evaluate_redirect_reliability.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from tests.evaluation_incidents import evaluate, metrics_as_dict, synthetic_observations  # noqa: E402


def main() -> int:
    observations = synthetic_observations()
    metrics = evaluate(observations)
    print(json.dumps({"cases": len(observations), "metrics": metrics_as_dict(metrics)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

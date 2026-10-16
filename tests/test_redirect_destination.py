from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))

try:
    from app.services.links import pick_destination  # noqa: E402
except ModuleNotFoundError as exc:  # pragma: no cover - environment-dependent
    pick_destination = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


@unittest.skipIf(
    pick_destination is None,
    f"backend runtime dependencies unavailable: {_IMPORT_ERROR}",
)
class RedirectDestinationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.link = SimpleNamespace(
            original_url="https://example.test/home",
            ios_url="https://apps.test/ios",
            android_url="https://apps.test/android",
        )

    def test_device_destinations_and_fallback_are_deterministic(self) -> None:
        assert pick_destination is not None
        self.assertEqual(
            pick_destination(self.link, "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"),
            self.link.ios_url,
        )
        self.assertEqual(
            pick_destination(self.link, "Mozilla/5.0 (Linux; Android 14; Pixel 8)"),
            self.link.android_url,
        )
        self.assertEqual(
            pick_destination(self.link, "Mozilla/5.0 (X11; Linux x86_64)"),
            self.link.original_url,
        )


if __name__ == "__main__":
    unittest.main()

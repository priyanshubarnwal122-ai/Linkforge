from __future__ import annotations

import unittest

from pydantic import ValidationError

from backend.app.schemas import LinkCreate


class UrlValidationTests(unittest.TestCase):
    def test_accepts_public_http_destination(self) -> None:
        link = LinkCreate(original_url="https://example.com/path")
        self.assertEqual(link.original_url, "https://example.com/path")

    def test_rejects_local_and_credentialed_destinations(self) -> None:
        for url in (
            "http://localhost:8080/admin",
            "http://127.0.0.1/internal",
            "http://10.0.0.5/private",
            "https://user:password@example.com/",
            "javascript:alert(1)",
        ):
            with self.subTest(url=url), self.assertRaises(ValidationError):
                LinkCreate(original_url=url)


if __name__ == "__main__":
    unittest.main()

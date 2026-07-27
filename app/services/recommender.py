"""
app/services/recommender.py — Smart Alias Recommender & Domain Vibe Analyzer.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.url import URL
from app.schemas import AliasOption, AliasRecommendResponse


class AliasRecommenderService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def recommend(self, raw_url: str) -> AliasRecommendResponse:
        url = raw_url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]

        # Extract brand/main domain name (e.g. github from github.com, amazon from amazon.co.uk)
        parts = domain.split(".")
        brand = parts[0] if len(parts) > 1 else domain

        path_tokens = [
            t.lower() for t in re.split(r"[/\-_.]", parsed.path)
            if t and len(t) > 2 and t.lower() not in {"index", "html", "php", "watch", "view", "item", "id", "dp", "app"}
        ]

        raw_candidates: list[str] = []

        # Strategy 1: Path tokens + Brand
        if path_tokens:
            if len(path_tokens) >= 2:
                raw_candidates.append(f"{path_tokens[0]}-{path_tokens[1]}")
                raw_candidates.append(f"{brand}-{path_tokens[0]}")
                raw_candidates.append(f"{path_tokens[-1]}-{brand}")
            else:
                raw_candidates.append(f"{brand}-{path_tokens[0]}")
                raw_candidates.append(f"{path_tokens[0]}-link")
                raw_candidates.append(f"{path_tokens[0]}-hub")

        # Strategy 2: Brand + action/descriptor
        raw_candidates.append(f"{brand}-direct")
        raw_candidates.append(f"go-{brand}")
        raw_candidates.append(f"{brand}-vip")

        # Clean and sanitize candidates (must match pattern ^[a-zA-Z0-9_-]+$)
        cleaned_candidates: list[str] = []
        for cand in raw_candidates:
            clean = re.sub(r"[^a-zA-Z0-9_-]", "", cand).strip("-_")
            if 3 <= len(clean) <= 40 and clean not in cleaned_candidates:
                cleaned_candidates.append(clean)

        # Select top 4 candidate aliases
        selected_candidates = cleaned_candidates[:4]

        # Check database availability for each candidate
        recommendations: list[AliasOption] = []
        for candidate in selected_candidates:
            stmt = select(URL).where(
                (URL.custom_alias == candidate) | (URL.short_code == candidate),
                URL.deleted_at.is_(None)
            )
            existing = (await self.session.execute(stmt)).scalars().first()
            recommendations.append(AliasOption(alias=candidate, available=existing is None))

        # Domain category and trust score analysis
        category = self._detect_category(domain, path_tokens)
        trust_score = self._calculate_trust_score(domain, parsed.scheme)

        return AliasRecommendResponse(
            domain=domain,
            category=category,
            trust_score=trust_score,
            recommendations=recommendations
        )

    def _detect_category(self, domain: str, path_tokens: list[str]) -> str:
        d = domain.lower()
        if any(k in d for k in ["github", "gitlab", "bitbucket", "stackoverflow", "npm", "pypi"]):
            return "Developer Tools & Code"
        if any(k in d for k in ["youtube", "vimeo", "twitch", "netflix", "spotify"]):
            return "Video & Audio Streaming"
        if any(k in d for k in ["amazon", "ebay", "shopify", "store", "shop"]):
            return "E-Commerce & Shopping"
        if any(k in d for k in ["twitter", "x.com", "facebook", "instagram", "linkedin", "reddit"]):
            return "Social Media & Community"
        if any(k in d for k in ["medium", "substack", "blog", "news", "nytimes", "forbes"]):
            return "Article & Publications"
        if any(k in d for k in ["docs", "notion", "figma", "trello", "google", "drive"]):
            return "Productivity & Workspace"
        return "Web Resource"

    def _calculate_trust_score(self, domain: str, scheme: str) -> int:
        score = 90 if scheme == "https" else 75
        popular_domains = {
            "github.com", "google.com", "youtube.com", "wikipedia.org",
            "twitter.com", "x.com", "linkedin.com", "microsoft.com",
            "amazon.com", "apple.com", "medium.com", "reddit.com"
        }
        if domain.lower() in popular_domains:
            score += 9
        return min(score, 99)

"""
app/services/recommender.py — Intelligent Semantic AI & GenAI Alias Recommender.
"""
from __future__ import annotations

import json
import re
from urllib.parse import urlparse

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.url import URL
from app.schemas import AliasOption, AliasRecommendResponse

log = structlog.get_logger(__name__)


class AliasRecommenderService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()

    async def recommend(self, raw_url: str) -> AliasRecommendResponse:
        url = raw_url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]

        parts = domain.split(".")
        brand = parts[0] if len(parts) > 1 else domain

        # Stopwords to filter out meaningless web noise
        stop_words = {
            "index", "html", "php", "watch", "view", "item", "id", "dp", "app",
            "www", "com", "org", "net", "io", "dev", "co", "uk", "in", "the",
            "and", "for", "with", "main", "master", "blob", "tree", "status", "page"
        }

        path_tokens = [
            t.lower() for t in re.split(r"[/\-_.]", parsed.path)
            if t and len(t) >= 2 and t.lower() not in stop_words
        ]

        raw_candidates: list[str] = []

        # 1. Try GenAI LLM API if key is configured (Gemini / OpenAI / Groq)
        llm_candidates = await self._generate_llm_aliases(url, brand, path_tokens)
        if llm_candidates:
            raw_candidates.extend(llm_candidates)

        # 2. Semantic Local NLP Entity Extraction (High-performance fallback & enhancement)
        if len(raw_candidates) < 4:
            local_candidates = self._generate_semantic_aliases(brand, path_tokens)
            for cand in local_candidates:
                if cand not in raw_candidates:
                    raw_candidates.append(cand)

        # Clean and sanitize candidates (must match pattern ^[a-zA-Z0-9_-]+$)
        cleaned_candidates: list[str] = []
        for cand in raw_candidates:
            clean = re.sub(r"[^a-zA-Z0-9_-]", "", cand).strip("-_")
            if 3 <= len(clean) <= 35 and clean not in cleaned_candidates:
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

        category = self._detect_category(domain, path_tokens)
        trust_score = self._calculate_trust_score(domain, parsed.scheme)

        return AliasRecommendResponse(
            domain=domain,
            category=category,
            trust_score=trust_score,
            recommendations=recommendations
        )

    async def _generate_llm_aliases(self, url: str, brand: str, path_tokens: list[str]) -> list[str]:
        """Calls Google Gemini API or OpenAI API if API key is provided in .env."""
        # 1. Google Gemini API
        if self.settings.gemini_api_key:
            try:
                prompt = (
                    f"Analyze this URL: '{url}'. Generate 4 short, catchy, hyphenated custom vanity alias suggestions "
                    "for a URL shortener (e.g. 'react-framework', 'fastapi-guide', 'iphone15-deal'). "
                    "Do NOT use gimmicky filler words like 'vip', 'direct', or 'go'. "
                    "Return ONLY a JSON array of 4 string aliases, for example: [\"alias-1\", \"alias-2\", \"alias-3\", \"alias-4\"]"
                )
                async with httpx.AsyncClient(timeout=3.0) as client:
                    resp = await client.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.settings.gemini_api_key}",
                        json={"contents": [{"parts": [{"text": prompt}]}]}
                    )
                    if resp.status_code == 200:
                        res_json = resp.json()
                        text = res_json["candidates"][0]["content"]["parts"][0]["text"]
                        match = re.search(r"\[.*\]", text, re.DOTALL)
                        if match:
                            return json.loads(match.group(0))
            except Exception as e:
                log.warning("Gemini API alias generation failed", error=str(e))

        # 2. OpenAI / Groq API
        api_key = self.settings.groq_api_key or self.settings.openai_api_key
        api_url = "https://api.groq.com/openai/v1/chat/completions" if self.settings.groq_api_key else "https://api.openai.com/v1/chat/completions"
        model_name = "llama3-8b-8192" if self.settings.groq_api_key else "gpt-4o-mini"

        if api_key:
            try:
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                payload = {
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": "You generate concise URL vanity aliases. Output JSON array of 4 hyphenated strings only."},
                        {"role": "user", "content": f"Generate 4 short semantic aliases for URL: {url}"}
                    ],
                    "temperature": 0.5
                }
                async with httpx.AsyncClient(timeout=3.0) as client:
                    resp = await client.post(api_url, json=payload, headers=headers)
                    if resp.status_code == 200:
                        content = resp.json()["choices"][0]["message"]["content"]
                        match = re.search(r"\[.*\]", content, re.DOTALL)
                        if match:
                            return json.loads(match.group(0))
            except Exception as e:
                log.warning("LLM API alias generation failed", error=str(e))

        return []

    def _generate_semantic_aliases(self, brand: str, path_tokens: list[str]) -> list[str]:
        """Generates clean, semantic local NLP alias candidates without tacky filler words."""
        candidates: list[str] = []

        if path_tokens:
            # Topic + Brand or Brand + Topic
            if len(path_tokens) >= 2:
                candidates.append(f"{path_tokens[0]}-{path_tokens[1]}")
                candidates.append(f"{brand}-{path_tokens[0]}")
                candidates.append(f"{path_tokens[0]}-{path_tokens[-1]}")
                candidates.append(f"{brand}-{path_tokens[1]}")
            else:
                candidates.append(f"{brand}-{path_tokens[0]}")
                candidates.append(f"{path_tokens[0]}-{brand}")
                candidates.append(f"{path_tokens[0]}-docs" if "doc" in path_tokens[0] else f"{path_tokens[0]}-guide")
        else:
            candidates.append(f"{brand}-official")
            candidates.append(f"{brand}-hub")
            candidates.append(f"{brand}-app")

        return candidates

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

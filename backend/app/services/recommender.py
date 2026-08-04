"""
app/services/recommender.py — 100% Pure GenAI LLM Alias Recommender.
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

        # Call GenAI LLM API (Google Gemini / Groq / OpenAI)
        raw_candidates = await self._generate_llm_aliases(url)

        # Fallback to smart semantic generator if LLM candidates are fewer than 4
        fallback_candidates = self._generate_fallback_aliases(url, domain, parsed.path)
        for fb in fallback_candidates:
            if fb not in raw_candidates:
                raw_candidates.append(fb)

        # Clean and sanitize candidates (must match pattern ^[a-zA-Z0-9_-]+$)
        cleaned_candidates: list[str] = []
        for cand in raw_candidates:
            clean = re.sub(r"[^a-zA-Z0-9_-]", "", cand).strip("-_")
            if 3 <= len(clean) <= 35 and clean not in cleaned_candidates:
                cleaned_candidates.append(clean)

        selected_candidates = cleaned_candidates[:4]

        # Check database availability for each candidate alias
        recommendations: list[AliasOption] = []
        for candidate in selected_candidates:
            stmt = select(URL).where(
                (URL.custom_alias == candidate) | (URL.short_code == candidate),
                URL.deleted_at.is_(None)
            )
            existing = (await self.session.execute(stmt)).scalars().first()
            recommendations.append(AliasOption(alias=candidate, available=existing is None))

        category = self._detect_category(domain)

        return AliasRecommendResponse(
            domain=domain,
            category=category,
            trust_score=95,
            recommendations=recommendations
        )

    async def _generate_llm_aliases(self, url: str) -> list[str]:
        """Queries GenAI LLM API (Google Gemini / Groq / OpenAI) for custom vanity aliases."""
        api_key = (self.settings.gemini_api_key or "").strip("\"' \t\r\n")

        # 1. Google Gemini API
        if api_key:
            models_to_try = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro", "gemini-pro"]
            prompt = (
                f"Analyze this URL: '{url}'. Generate 4 short, catchy, hyphenated custom vanity alias suggestions "
                "for a URL shortener (e.g. 'react-framework', 'fastapi-guide', 'iphone15-deal'). "
                "Return ONLY a JSON array of 4 string aliases, for example: [\"alias-1\", \"alias-2\", \"alias-3\", \"alias-4\"]"
            )
            for model in models_to_try:
                try:
                    async with httpx.AsyncClient(timeout=3.5) as client:
                        resp = await client.post(
                            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
                            json={"contents": [{"parts": [{"text": prompt}]}]}
                        )
                        if resp.status_code == 200:
                            res_json = resp.json()
                            text = res_json["candidates"][0]["content"]["parts"][0]["text"]
                            match = re.search(r"\[.*\]", text, re.DOTALL)
                            if match:
                                res = json.loads(match.group(0))
                                if isinstance(res, list) and len(res) > 0:
                                    return [str(x) for x in res]
                except Exception as e:
                    log.warning("Gemini LLM API call failed", model=model, error=str(e))

        # 2. OpenAI / Groq API
        groq_or_openai_key = (self.settings.groq_api_key or self.settings.openai_api_key or "").strip("\"' \t\r\n")
        api_url = "https://api.groq.com/openai/v1/chat/completions" if self.settings.groq_api_key else "https://api.openai.com/v1/chat/completions"
        model_name = "llama3-8b-8192" if self.settings.groq_api_key else "gpt-4o-mini"

        if groq_or_openai_key:
            try:
                headers = {"Authorization": f"Bearer {groq_or_openai_key}", "Content-Type": "application/json"}
                payload = {
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": "You generate concise URL vanity aliases. Output JSON array of 4 hyphenated strings only."},
                        {"role": "user", "content": f"Generate 4 short semantic aliases for URL: {url}"}
                    ],
                    "temperature": 0.5
                }
                async with httpx.AsyncClient(timeout=3.5) as client:
                    resp = await client.post(api_url, json=payload, headers=headers)
                    if resp.status_code == 200:
                        content = resp.json()["choices"][0]["message"]["content"]
                        match = re.search(r"\[.*\]", content, re.DOTALL)
                        if match:
                            res = json.loads(match.group(0))
                            if isinstance(res, list) and len(res) > 0:
                                return [str(x) for x in res]
            except Exception as e:
                log.warning("LLM API call failed", error=str(e))

        return []

    def _generate_fallback_aliases(self, url: str, domain: str, path: str) -> list[str]:
        """Generates smart, relevant semantic aliases from domain & path keywords."""
        domain_name = domain.split(".")[0] if "." in domain else domain
        path_segments = [seg for seg in re.split(r"[/\-_.]+", path) if len(seg) > 2]

        slugs = []
        if path_segments:
            main_path = path_segments[-1]
            slugs.append(f"{domain_name}-{main_path}")
            if len(path_segments) > 1:
                slugs.append(f"{path_segments[0]}-{main_path}")
            slugs.append(f"{main_path}-link")
            slugs.append(f"{domain_name}-{path_segments[0]}")
        
        # Default fallbacks
        slugs.extend([
            f"{domain_name}-link",
            f"{domain_name}-quick",
            f"{domain_name}-share",
            f"{domain_name}-hub",
            "smart-alias",
            "quick-redirect"
        ])

        return slugs

    def _detect_category(self, domain: str) -> str:
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


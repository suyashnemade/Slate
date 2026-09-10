import json
import re
from enum import Enum
from typing import List, Optional
import httpx
from pydantic import BaseModel, Field

from ..config import settings


class QueryType(str, Enum):
    SIMPLE = "simple"
    COMPLEX = "complex"


class RoutingDecision(BaseModel):
    query_type: QueryType
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    subqueries: List[str] = Field(default_factory=list)


ROUTER_PROMPT = """You are an expert query analysis router for a document retrieval system.
Analyze the user's question and decide if it is SIMPLE or COMPLEX/MULTI-HOP.

Definitions:
- "simple": Can be answered by directly retrieving one specific topic or passage (e.g. "What is the policy on sick leave?", "When was the company founded?").
- "complex": Requires multi-hop reasoning, comparison across multiple entities, or synthesizes multiple distinct topics (e.g. "Compare the revenue in 2022 vs 2023 and explain how profit margins changed", "What are the advantages and disadvantages of option A compared to option B?").

Respond ONLY with valid JSON matching this schema:
{{
  "query_type": "simple" | "complex",
  "confidence": <float between 0.0 and 1.0>,
  "reasoning": "<brief 1-sentence reason>",
  "subqueries": ["<subquery 1>", "<subquery 2>"]  // if complex, 2-3 focused subqueries; if simple, just the original query
}}

User Query: {query}
"""


class QueryRouter:
    """Classifies user queries into SIMPLE or COMPLEX/MULTI-HOP with confidence scoring."""

    def __init__(self):
        self.groq_key = settings.GROQ_API_KEY
        self.gemini_key = settings.GEMINI_API_KEY
        self.openai_key = settings.OPENAI_API_KEY

    def route(self, query: str) -> RoutingDecision:
        query_clean = query.strip()

        # 1. Try LLM routing if any API key is configured
        if self.groq_key:
            llm_result = self._route_with_groq(query_clean)
            if llm_result:
                return llm_result

        if self.gemini_key:
            llm_result = self._route_with_gemini(query_clean)
            if llm_result:
                return llm_result

        if self.openai_key:
            llm_result = self._route_with_openai(query_clean)
            if llm_result:
                return llm_result

        # 2. Heuristic fallback for offline/local execution
        return self._route_heuristic(query_clean)

    def _route_with_groq(self, query: str) -> Optional[RoutingDecision]:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {self.groq_key}", "Content-Type": "application/json"}
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": ROUTER_PROMPT.format(query=query)}],
                "response_format": {"type": "json_object"},
                "temperature": 0.0,
            }
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()["choices"][0]["message"]["content"]
                    parsed = json.loads(data)
                    return RoutingDecision(**parsed)
        except Exception:
            pass
        return None

    def _route_with_gemini(self, query: str) -> Optional[RoutingDecision]:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
            headers = {"Content-Type": "application/json"}
            prompt = ROUTER_PROMPT.format(query=query) + "\nOutput strictly raw JSON."
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.0, "response_mime_type": "application/json"},
            }
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                    parsed = json.loads(text)
                    return RoutingDecision(**parsed)
        except Exception:
            pass
        return None

    def _route_with_openai(self, query: str) -> Optional[RoutingDecision]:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {self.openai_key}", "Content-Type": "application/json"}
            payload = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": ROUTER_PROMPT.format(query=query)}],
                "response_format": {"type": "json_object"},
                "temperature": 0.0,
            }
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()["choices"][0]["message"]["content"]
                    parsed = json.loads(data)
                    return RoutingDecision(**parsed)
        except Exception:
            pass
        return None

    def _route_heuristic(self, query: str) -> RoutingDecision:
        """Deterministic local classifier based on linguistic complexity and comparative markers."""
        lowered = query.lower()

        # Comparative and multi-hop indicators
        comparison_patterns = [
            r"\b(compare|contrast|difference between|versus|vs\.?)\b",
            r"\b(both|and also|as well as|in addition to)\b",
            r"\b(how did .* change from .* to .*)\b",
            r"\b(pros and cons|advantages and disadvantages)\b",
            r"\b(why did .* and what were .*)\b",
        ]

        is_complex = any(re.search(pat, lowered) for pat in comparison_patterns)
        has_multiple_questions = query.count("?") > 1 or " and what " in lowered or " and how " in lowered

        if is_complex or has_multiple_questions:
            # Generate subqueries deterministically
            subqueries = self._heuristic_subqueries(query)
            return RoutingDecision(
                query_type=QueryType.COMPLEX,
                confidence=0.85,
                reasoning="Query contains comparative phrasing or multiple query targets.",
                subqueries=subqueries,
            )

        return RoutingDecision(
            query_type=QueryType.SIMPLE,
            confidence=0.92,
            reasoning="Query is focused on a single topic suitable for direct semantic retrieval.",
            subqueries=[query],
        )

    def _heuristic_subqueries(self, query: str) -> List[str]:
        lowered = query.lower()
        # Look for "vs" or "versus" or "difference between X and Y"
        if " vs " in lowered or " versus " in lowered:
            parts = re.split(r"\s+(?:vs\.?|versus)\s+", query, flags=re.IGNORECASE)
            if len(parts) == 2:
                return [parts[0].strip(), parts[1].strip()]

        if "difference between" in lowered:
            match = re.search(r"difference between (.*?) and (.*)", query, re.IGNORECASE)
            if match:
                return [match.group(1).strip(), match.group(2).strip()]

        # If multiple question clauses exist, split by 'and' or '?'
        clauses = [c.strip() for c in re.split(r"\band\b|\?", query, flags=re.IGNORECASE) if len(c.strip()) > 8]
        if len(clauses) >= 2:
            return clauses[:3]

        return [query]

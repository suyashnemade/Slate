import json
from typing import Dict, Optional
import httpx
from pydantic import BaseModel, Field

from ..config import settings


class GradeResult(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    passed: bool
    feedback: str
    criteria: Dict[str, float] = Field(default_factory=dict)


GRADER_PROMPT = """You are an impartial judge evaluating the quality and faithfulness of a RAG answer.
Question: {question}
Context Provided:
{context}

Generated Answer:
{answer}

Evaluate the answer on a scale from 0.0 to 1.0 based on:
1. Faithfulness: Is the answer grounded ONLY in the provided context without hallucinations?
2. Completeness: Does it answer the user's specific question?
3. Clarity: Is the response concise and well-structured?

Threshold for passing is 0.5.
Output strictly JSON matching this format:
{{
  "score": <float between 0.0 and 1.0>,
  "passed": <true if score >= 0.5 else false>,
  "feedback": "<concise evaluation critique>",
  "criteria": {{
    "faithfulness": <float between 0.0 and 1.0>,
    "completeness": <float between 0.0 and 1.0>,
    "clarity": <float between 0.0 and 1.0>
  }}
}}
"""


class LLMGrader:
    """LLM-as-judge grader with 0.5 threshold for answer quality assessment."""

    THRESHOLD: float = 0.5

    def __init__(self):
        self.groq_key = settings.GROQ_API_KEY
        self.gemini_key = settings.GEMINI_API_KEY
        self.openai_key = settings.OPENAI_API_KEY

    def grade(self, question: str, context: str, answer: str) -> GradeResult:
        # 1. Try LLM judging if configured
        if self.groq_key:
            res = self._grade_with_groq(question, context, answer)
            if res:
                return res

        if self.gemini_key:
            res = self._grade_with_gemini(question, context, answer)
            if res:
                return res

        if self.openai_key:
            res = self._grade_with_openai(question, context, answer)
            if res:
                return res

        # 2. Local deterministic grader fallback (offline / test-suite ready)
        return self._grade_local(question, context, answer)

    def _grade_with_groq(self, question: str, context: str, answer: str) -> Optional[GradeResult]:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {self.groq_key}", "Content-Type": "application/json"}
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": GRADER_PROMPT.format(question=question, context=context, answer=answer)}],
                "response_format": {"type": "json_object"},
                "temperature": 0.0,
            }
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = json.loads(res.json()["choices"][0]["message"]["content"])
                    data["passed"] = data.get("score", 0.0) >= self.THRESHOLD
                    return GradeResult(**data)
        except Exception:
            pass
        return None

    def _grade_with_gemini(self, question: str, context: str, answer: str) -> Optional[GradeResult]:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
            headers = {"Content-Type": "application/json"}
            prompt = GRADER_PROMPT.format(question=question, context=context, answer=answer)
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.0, "response_mime_type": "application/json"},
            }
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                    data = json.loads(text)
                    data["passed"] = data.get("score", 0.0) >= self.THRESHOLD
                    return GradeResult(**data)
        except Exception:
            pass
        return None

    def _grade_with_openai(self, question: str, context: str, answer: str) -> Optional[GradeResult]:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {self.openai_key}", "Content-Type": "application/json"}
            payload = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": GRADER_PROMPT.format(question=question, context=context, answer=answer)}],
                "response_format": {"type": "json_object"},
                "temperature": 0.0,
            }
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = json.loads(res.json()["choices"][0]["message"]["content"])
                    data["passed"] = data.get("score", 0.0) >= self.THRESHOLD
                    return GradeResult(**data)
        except Exception:
            pass
        return None

    def _grade_local(self, question: str, context: str, answer: str) -> GradeResult:
        """Deterministic judge measuring semantic overlap and grounding."""
        if not answer.strip() or answer.lower().startswith("no relevant"):
            return GradeResult(
                score=0.0,
                passed=False,
                feedback="Answer is empty or failed to retrieve context.",
                criteria={"faithfulness": 0.0, "completeness": 0.0, "clarity": 0.0},
            )

        import re
        q_words = set(w for w in re.findall(r"\b\w+\b", question.lower()) if len(w) > 2)
        c_words = set(w for w in re.findall(r"\b\w+\b", context.lower()) if len(w) > 2)
        a_words = set(w for w in re.findall(r"\b\w+\b", answer.lower()) if len(w) > 2)

        # Faithfulness: fraction of significant words in answer that appear in context
        grounded = len(a_words.intersection(c_words))
        faithfulness = round(grounded / max(1, len(a_words)), 2)

        # Completeness: fraction of question keywords addressed in answer
        addressed = len(q_words.intersection(a_words))
        completeness = round(addressed / max(1, len(q_words)), 2)

        # Clarity: structural heuristic
        clarity = 0.9 if len(a_words) >= 5 else 0.7

        final_score = round(0.5 * faithfulness + 0.3 * completeness + 0.2 * clarity, 2)
        passed = final_score >= self.THRESHOLD

        feedback = "Passed quality threshold." if passed else "Score fell below 0.5 threshold; answer may lack context grounding."

        return GradeResult(
            score=final_score,
            passed=passed,
            feedback=feedback,
            criteria={
                "faithfulness": min(1.0, faithfulness),
                "completeness": min(1.0, completeness),
                "clarity": min(1.0, clarity),
            },
        )

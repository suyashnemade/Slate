from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MetricScore(BaseModel):
    name: str
    score: float = Field(ge=0.0, le=1.0)
    description: str


class EvaluationItemResult(BaseModel):
    query: str
    answer: str
    ground_truth: Optional[str] = None
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float
    average_score: float


class EvaluationReport(BaseModel):
    total_queries: int
    mean_faithfulness: float
    mean_answer_relevancy: float
    mean_context_precision: float
    mean_context_recall: float
    overall_score: float
    item_results: List[EvaluationItemResult]


class RagasEvaluator:
    """Calculates the 4 core RAGAS metrics locally without external cloud dependencies:

    1. Faithfulness: Answer groundedness against retrieved context
    2. Answer Relevancy: How directly answer addresses question
    3. Context Precision: Signal-to-noise ratio and rank of relevant chunks
    4. Context Recall: Extent to which ground truth is present in retrieved chunks
    """

    @classmethod
    def compute_faithfulness(cls, answer: str, context: str) -> float:
        import re
        if not answer.strip() or not context.strip():
            return 0.0

        ans_tokens = [t for t in re.findall(r"\b\w+\b", answer.lower()) if len(t) > 2]
        if not ans_tokens:
            return 1.0

        ctx_words = set(re.findall(r"\b\w+\b", context.lower()))
        supported = sum(1 for t in ans_tokens if t in ctx_words)
        return round(min(1.0, supported / len(ans_tokens)), 3)

    @classmethod
    def compute_answer_relevancy(cls, query: str, answer: str) -> float:
        import re
        if not answer.strip() or not query.strip():
            return 0.0

        # Stopwords to ignore in relevancy scoring
        stopwords = {
            "the", "is", "are", "was", "were", "for", "in", "of", "to", "a", "an",
            "what", "when", "where", "which", "who", "whom", "this", "that", "these",
            "those", "have", "has", "had", "been", "with", "does", "do", "did"
        }
        q_tokens = [t for t in re.findall(r"\b\w+\b", query.lower()) if len(t) > 1 and t not in stopwords]
        if not q_tokens:
            return 1.0

        ans_words = set(re.findall(r"\b\w+\b", answer.lower()))
        matched = 0
        for q in q_tokens:
            # Match exact or stem/prefix (e.g. return/returned, purchase/purchased)
            stem = q[:4] if len(q) >= 4 else q
            if any(w == q or w.startswith(stem) or (len(w) >= 4 and q.startswith(w[:4])) for w in ans_words):
                matched += 1

        token_ratio = matched / len(q_tokens)

        # Penalize answers that are evasive
        ans_lower = answer.lower()
        evasive_markers = ["i don't know", "no information", "cannot answer"]
        is_evasive = any(m in ans_lower for m in evasive_markers)
        if is_evasive:
            return round(token_ratio * 0.3, 3)

        return round(min(1.0, token_ratio), 3)

    @classmethod
    def compute_context_precision(cls, retrieved_chunks: List[str], ground_truth: str) -> float:
        import re
        if not retrieved_chunks:
            return 0.0
        if not ground_truth.strip():
            return 1.0

        gt_words = set(w for w in re.findall(r"\b\w+\b", ground_truth.lower()) if len(w) > 2)
        if not gt_words:
            return 1.0

        # Calculate precision at k with rank weighting
        relevant_flags = []
        for chunk in retrieved_chunks:
            chunk_words = set(re.findall(r"\b\w+\b", chunk.lower()))
            overlap = len(chunk_words.intersection(gt_words))
            relevant_flags.append(overlap >= max(1, len(gt_words) // 3))

        if not any(relevant_flags):
            return 0.0

        # Mean average precision style formula
        precisions = []
        running_rel = 0
        for i, is_rel in enumerate(relevant_flags, 1):
            if is_rel:
                running_rel += 1
                precisions.append(running_rel / i)

        return round(sum(precisions) / len(precisions), 3) if precisions else 0.0

    @classmethod
    def compute_context_recall(cls, retrieved_context: str, ground_truth: str) -> float:
        import re
        if not ground_truth.strip():
            return 1.0
        if not retrieved_context.strip():
            return 0.0

        stopwords = {"the", "is", "are", "was", "were", "for", "in", "of", "to", "a", "an", "have", "has", "had"}
        gt_tokens = [t for t in re.findall(r"\b\w+\b", ground_truth.lower()) if len(t) > 1 and t not in stopwords]
        if not gt_tokens:
            return 1.0

        ctx_words = set(re.findall(r"\b\w+\b", retrieved_context.lower()))
        recalled = 0
        for g in gt_tokens:
            stem = g[:4] if len(g) >= 4 else g
            if any(w == g or w.startswith(stem) or (len(w) >= 4 and g.startswith(w[:4])) for w in ctx_words):
                recalled += 1

        return round(min(1.0, recalled / len(gt_tokens)), 3)

    def evaluate_sample(
        self,
        query: str,
        answer: str,
        retrieved_chunks: List[str],
        ground_truth: Optional[str] = None,
    ) -> EvaluationItemResult:
        full_context = "\n".join(retrieved_chunks)
        gt = ground_truth or ""

        faithfulness = self.compute_faithfulness(answer, full_context)
        answer_relevancy = self.compute_answer_relevancy(query, answer)
        context_precision = self.compute_context_precision(retrieved_chunks, gt)
        context_recall = self.compute_context_recall(full_context, gt)

        avg = round((faithfulness + answer_relevancy + context_precision + context_recall) / 4, 3)

        return EvaluationItemResult(
            query=query,
            answer=answer,
            ground_truth=ground_truth,
            faithfulness=faithfulness,
            answer_relevancy=answer_relevancy,
            context_precision=context_precision,
            context_recall=context_recall,
            average_score=avg,
        )

    def evaluate_dataset(self, samples: List[Dict[str, Any]]) -> EvaluationReport:
        items = []
        for s in samples:
            item_res = self.evaluate_sample(
                query=s.get("query", ""),
                answer=s.get("answer", ""),
                retrieved_chunks=s.get("retrieved_chunks", []),
                ground_truth=s.get("ground_truth"),
            )
            items.append(item_res)

        n = len(items)
        if n == 0:
            return EvaluationReport(
                total_queries=0,
                mean_faithfulness=0.0,
                mean_answer_relevancy=0.0,
                mean_context_precision=0.0,
                mean_context_recall=0.0,
                overall_score=0.0,
                item_results=[],
            )

        mean_faith = round(sum(i.faithfulness for i in items) / n, 3)
        mean_rel = round(sum(i.answer_relevancy for i in items) / n, 3)
        mean_prec = round(sum(i.context_precision for i in items) / n, 3)
        mean_rec = round(sum(i.context_recall for i in items) / n, 3)
        overall = round((mean_faith + mean_rel + mean_prec + mean_rec) / 4, 3)

        return EvaluationReport(
            total_queries=n,
            mean_faithfulness=mean_faith,
            mean_answer_relevancy=mean_rel,
            mean_context_precision=mean_prec,
            mean_context_recall=mean_rec,
            overall_score=overall,
            item_results=items,
        )

import pytest
from src.evaluation.grader import LLMGrader
from src.evaluation.ragas_metrics import RagasEvaluator


def test_grader_threshold():
    grader = LLMGrader()

    # Good grounded answer
    question = "What is the capital of France?"
    context = "Paris is the capital and most populous city of France."
    good_answer = "The capital of France is Paris."

    res_good = grader.grade(question=question, context=context, answer=good_answer)
    assert res_good.score >= 0.5
    assert res_good.passed is True
    assert "faithfulness" in res_good.criteria

    # Bad / irrelevant / empty answer
    bad_answer = "No relevant information found."
    res_bad = grader.grade(question=question, context=context, answer=bad_answer)
    assert res_bad.score < 0.5
    assert res_bad.passed is False


def test_ragas_metrics_computation():
    evaluator = RagasEvaluator()

    query = "What is the return window for purchased laptops?"
    context = "Purchased laptops may be returned within 30 days of receipt in original packaging."
    answer = "Laptops can be returned within 30 days of purchase in original packaging."
    ground_truth = "Customers have 30 days to return purchased laptops."

    result = evaluator.evaluate_sample(
        query=query,
        answer=answer,
        retrieved_chunks=[context],
        ground_truth=ground_truth,
    )

    assert result.faithfulness > 0.5
    assert result.answer_relevancy > 0.5
    assert result.context_precision > 0.0
    assert result.context_recall > 0.5
    assert result.average_score >= 0.5


def test_ragas_dataset_report():
    evaluator = RagasEvaluator()

    samples = [
        {
            "query": "What is Python?",
            "answer": "Python is a high-level programming language.",
            "retrieved_chunks": ["Python is a high-level, general-purpose programming language."],
            "ground_truth": "Python is a programming language.",
        }
    ]

    report = evaluator.evaluate_dataset(samples)
    assert report.total_queries == 1
    assert report.overall_score > 0.0
    assert report.mean_faithfulness > 0.0

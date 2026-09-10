"""
CLI tool to evaluate Slate RAG pipeline using RAGAS metrics on custom or benchmark evaluation datasets.
"""
import argparse
import json
import os
import sys
from pathlib import Path
from tabulate import tabulate

from src.graphs.query.graph import QueryGraph
from src.evaluation.ragas_metrics import RagasEvaluator


def load_dataset(dataset_path: str):
    p = Path(dataset_path)
    if not p.exists():
        raise FileNotFoundError(f"Dataset not found at {dataset_path}")
    
    if p.suffix.lower() == ".json":
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    elif p.suffix.lower() == ".csv":
        import csv
        with open(p, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)
    else:
        raise ValueError(f"Unsupported format: {p.suffix}")


def run_evaluation(dataset_path: str, project_id: str = "default", output_path: str = None, top_k: int = 4):
    print(f"\n=======================================================")
    print(f"   SLATE — RAGAS BENCHMARK EVALUATION ENGINE")
    print(f"=======================================================")
    print(f"Target Dataset: {dataset_path}")
    print(f"Project Scope:  {project_id}\n")

    dataset = load_dataset(dataset_path)
    # Support list of items or dictionary wrapper
    samples = dataset.get("test_cases", dataset) if isinstance(dataset, dict) else dataset

    print(f"Loaded {len(samples)} evaluation test cases. Running through QueryGraph pipeline...")
    
    query_graph = QueryGraph()
    results = []

    table_data = []

    for idx, sample in enumerate(samples, 1):
        item_id = sample.get("id", f"tc_{idx:03d}")
        query = sample.get("query") or sample.get("question") or ""
        ground_truth = sample.get("ground_truth") or sample.get("expected_answer") or ""

        # Run Slate Query Graph
        response = query_graph.answer_query(
            project_id=project_id,
            query=query,
            top_k=top_k,
            grade_response=False
        )

        answer = response.get("answer", "")
        context = response.get("context", "")

        # Compute 4 Core RAGAS Metrics
        faithfulness = RagasEvaluator.compute_faithfulness(answer=answer, context=context)
        relevancy = RagasEvaluator.compute_answer_relevancy(query=query, answer=answer)
        precision = RagasEvaluator.compute_context_precision(ground_truth=ground_truth, context=context)
        recall = RagasEvaluator.compute_context_recall(ground_truth=ground_truth, context=context)
        avg_score = round((faithfulness + relevancy + precision + recall) / 4.0, 3)

        results.append({
            "id": item_id,
            "query": query,
            "answer": answer,
            "ground_truth": ground_truth,
            "faithfulness": faithfulness,
            "answer_relevancy": relevancy,
            "context_precision": precision,
            "context_recall": recall,
            "average_score": avg_score
        })

        table_data.append([
            item_id,
            f"{faithfulness:.2f}",
            f"{relevancy:.2f}",
            f"{precision:.2f}",
            f"{recall:.2f}",
            f"{avg_score:.2f}"
        ])

    # Summary
    n = max(1, len(results))
    mean_f = sum(r["faithfulness"] for r in results) / n
    mean_rel = sum(r["answer_relevancy"] for r in results) / n
    mean_prec = sum(r["context_precision"] for r in results) / n
    mean_rec = sum(r["context_recall"] for r in results) / n
    overall_avg = (mean_f + mean_rel + mean_prec + mean_rec) / 4.0

    table_data.append(["="*10, "="*10, "="*10, "="*10, "="*10, "="*10])
    table_data.append([
        "OVERALL",
        f"{mean_f:.2f}",
        f"{mean_rel:.2f}",
        f"{mean_prec:.2f}",
        f"{mean_rec:.2f}",
        f"{overall_avg:.2f}"
    ])

    headers = ["ID", "Faithful", "Relevancy", "Precision", "Recall", "Avg"]
    print(tabulate(table_data, headers=headers, tablefmt="simple"))

    if output_path:
        out = {
            "dataset": dataset_path,
            "total_samples": len(samples),
            "overall_summary": {
                "faithfulness": round(mean_f, 3),
                "answer_relevancy": round(mean_rel, 3),
                "context_precision": round(mean_prec, 3),
                "context_recall": round(mean_rec, 3),
                "overall_score": round(overall_avg, 3)
            },
            "item_results": results
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
        print(f"\nSaved evaluation report to: {output_path}")

    return overall_avg


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Slate RAGAS Evaluation Engine")
    parser.add_argument("--dataset", type=str, default="data/evaluation_dataset.json", help="Path to evaluation dataset")
    parser.add_argument("--project-id", type=str, default="default", help="Project ID to evaluate against")
    parser.add_argument("--output", type=str, default="data/evaluation_report.json", help="Path to write report JSON")
    parser.add_argument("--top-k", type=int, default=4, help="Retriever top_k")
    args = parser.parse_args()

    run_evaluation(
        dataset_path=args.dataset,
        project_id=args.project_id,
        output_path=args.output,
        top_k=args.top_k
    )

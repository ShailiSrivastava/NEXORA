from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any

import numpy as np

from app.evaluation.dataset import get_evaluation_dataset, validate_dataset
from app.evaluation.metrics import aggregate_metrics, evaluate_query
from app.retrieval.reranker import CrossEncoderReranker
from app.retrieval.vector_store import VectorStore
from app.services.personalization_service import PersonalizationService


def _job_text(job: dict[str, Any]) -> str:
    parts = [
        job.get("title", ""),
        job.get("company", ""),
        job.get("description", ""),
        " ".join(job.get("required_skills", [])),
        job.get("role", ""),
        job.get("location", ""),
    ]
    return " ".join(part for part in parts if part)


def _get_embedding_model() -> Any:
    return VectorStore.get_embedding_model()


def _semantic_search(job_corpus: list[dict[str, Any]], query: str, top_k: int = 5) -> list[str]:
    model = _get_embedding_model()
    job_texts = [_job_text(job) for job in job_corpus]
    query_embedding = model.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]
    job_embeddings = model.encode(job_texts, convert_to_numpy=True, normalize_embeddings=True)
    similarities = np.dot(job_embeddings, query_embedding)
    ranked_indices = np.argsort(similarities)[::-1][:top_k]
    return [job_corpus[int(idx)]["job_id"] for idx in ranked_indices]


def _rerank_results(query: str, job_ids: list[str], job_lookup: dict[str, dict[str, Any]], top_k: int = 5) -> list[str]:
    reranker = CrossEncoderReranker()
    jobs = [job_lookup[job_id] for job_id in job_ids]
    reranked = reranker.rerank(query, jobs)
    return [job["job_id"] for job in reranked[:top_k]]


def _personalize_results(query: str, job_ids: list[str], job_lookup: dict[str, dict[str, Any]], candidate_profile: dict[str, Any], top_k: int = 5) -> list[str]:
    service = PersonalizationService()
    candidate_jobs = []
    for job_id in job_ids:
        job = dict(job_lookup[job_id])
        job["score"] = float(job.get("score", 0.0))
        candidate_jobs.append(job)
    personalized = service.personalize(candidate_profile, candidate_jobs)
    return [job["job_id"] for job in personalized[:top_k]]


def _evaluate_strategy(strategy_name: str, query: dict[str, Any], job_corpus: list[dict[str, Any]], top_k: int = 5) -> dict[str, Any]:
    query_text = query["query"]
    relevant = set(query["relevant_job_ids"])
    job_lookup = {job["job_id"]: job for job in job_corpus}

    if strategy_name == "baseline":
        retrieved = _semantic_search(job_corpus, query_text, top_k=top_k)
    elif strategy_name == "reranked":
        baseline = _semantic_search(job_corpus, query_text, top_k=max(top_k * 3, top_k))
        retrieved = _rerank_results(query_text, baseline, job_lookup, top_k=top_k)
    elif strategy_name == "personalized":
        baseline = _semantic_search(job_corpus, query_text, top_k=max(top_k * 3, top_k))
        reranked = _rerank_results(query_text, baseline, job_lookup, top_k=max(top_k * 3, top_k))
        retrieved = _personalize_results(query_text, reranked, job_lookup, query["candidate_profile"], top_k=top_k)
    else:
        raise ValueError(f"Unknown strategy: {strategy_name}")

    return {
        "query_id": query["query_id"],
        "query": query_text,
        "strategy": strategy_name,
        "retrieved": retrieved,
        "relevant": sorted(relevant),
        **evaluate_query(retrieved, relevant, k=top_k),
    }


def _summarize_results(results: list[dict[str, Any]]) -> dict[str, float]:
    metrics = [
        "precision@5",
        "recall@5",
        "mrr",
        "ndcg@5",
    ]
    summary = {metric: 0.0 for metric in metrics}
    for metric in metrics:
        summary[metric] = sum(float(item[metric]) for item in results) / len(results) if results else 0.0
    return summary


def run_evaluation(top_k: int = 5, include_ragas: bool = False) -> dict[str, Any]:
    dataset = get_evaluation_dataset()
    if not validate_dataset(dataset):
        raise ValueError("Evaluation dataset validation failed: job corpus and ground-truth queries are invalid.")

    job_corpus = dataset["jobs"]
    query_rows = dataset["queries"]

    strategies = {
        "baseline": [
            _evaluate_strategy("baseline", query, job_corpus, top_k=top_k) for query in query_rows
        ],
        "reranked": [
            _evaluate_strategy("reranked", query, job_corpus, top_k=top_k) for query in query_rows
        ],
        "personalized": [
            _evaluate_strategy("personalized", query, job_corpus, top_k=top_k) for query in query_rows
        ],
    }

    summary = {
        strategy_name: _summarize_results(rows)
        for strategy_name, rows in strategies.items()
    }

    output = {
        "top_k": top_k,
        "dataset_size": len(query_rows),
        "summary": summary,
        "strategy_results": strategies,
    }

    if include_ragas:
        output["ragas"] = run_ragas_evaluation(query_rows)

    artifact_dir = Path(__file__).resolve().parents[2] / "artifacts" / "evaluation"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    json_path = artifact_dir / "evaluation_summary.json"
    csv_path = artifact_dir / "evaluation_summary.csv"

    json_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["strategy", "precision@5", "recall@5", "mrr", "ndcg@5"])
        for strategy_name, metrics in summary.items():
            writer.writerow([strategy_name, metrics["precision@5"], metrics["recall@5"], metrics["mrr"], metrics["ndcg@5"]])

    return output


def run_ragas_evaluation(queries: list[dict[str, Any]]) -> dict[str, Any]:
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not gemini_key:
        return {
            "status": "skipped",
            "reason": "Ragas evaluation requires a configured GEMINI_API_KEY or GOOGLE_API_KEY environment variable.",
        }

    try:
        from ragas import evaluate
        from ragas.metrics import answer_relevancy, faithfulness
    except ImportError:
        return {
            "status": "skipped",
            "reason": "Ragas is not installed. Install it with: pip install ragas",
        }

    rows = []
    for query in queries[:5]:
        relevant_jobs = [
            job for job in get_evaluation_dataset()["jobs"] if job["job_id"] in set(query["relevant_job_ids"])
        ]
        answer = (
            f"For the query '{query['query']}', the most relevant jobs are: "
            + ", ".join(job["title"] for job in relevant_jobs)
            + ". This answer is grounded in the manually defined evaluation data only."
        )
        rows.append(
            {
                "user_input": query["query"],
                "response": answer,
                "retrieved_contexts": [job["description"] for job in relevant_jobs],
                "ground_truth": " ".join(job["title"] for job in relevant_jobs),
            }
        )

    evaluation = evaluate(rows, metrics=[faithfulness, answer_relevancy])
    return {
        "status": "executed",
        "result": evaluation,
    }


def _print_comparison_table(summary: dict[str, dict[str, float]]) -> None:
    headers = ["strategy", "precision@5", "recall@5", "mrr", "ndcg@5"]
    rows = [
        [
            strategy,
            f"{values['precision@5']:.4f}",
            f"{values['recall@5']:.4f}",
            f"{values['mrr']:.4f}",
            f"{values['ndcg@5']:.4f}",
        ]
        for strategy, values in summary.items()
    ]
    widths = [max(len(str(header)), max(len(str(row[idx])) for row in [*rows])) for idx, header in enumerate(headers)]
    header_line = "  ".join(str(header).ljust(widths[idx]) for idx, header in enumerate(headers))
    print(header_line)
    print("-" * len(header_line))
    for row in rows:
        print("  ".join(str(value).ljust(widths[idx]) for idx, value in enumerate(row)))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run NEXORA retrieval and ranking evaluation.")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to evaluate per query.")
    parser.add_argument("--include-ragas", action="store_true", help="Execute Ragas metrics when API credentials are configured.")
    args = parser.parse_args()

    output = run_evaluation(top_k=args.top_k, include_ragas=args.include_ragas)
    summary = output["summary"]
    print("NEXORA evaluation summary")
    _print_comparison_table(summary)
    if "ragas" in output:
        ragas_status = output["ragas"].get("status")
        print(f"\nRagas status: {ragas_status}")
        if output["ragas"].get("reason"):
            print(output["ragas"]["reason"])
    print("\nArtifacts saved to:")
    artifact_dir = Path(__file__).resolve().parents[2] / "artifacts" / "evaluation"
    print(artifact_dir)


if __name__ == "__main__":
    main()

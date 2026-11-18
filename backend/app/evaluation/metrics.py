from __future__ import annotations

from math import log2
from typing import Any


def _normalize_k(k: int) -> int:
    return max(1, int(k))


def precision_at_k(retrieved: list[str], relevant: set[str], k: int = 5) -> float:
    if not retrieved or k <= 0:
        return 0.0
    top_k = retrieved[: _normalize_k(k)]
    hits = sum(1 for item in top_k if item in relevant)
    return hits / len(top_k)


def recall_at_k(retrieved: list[str], relevant: set[str], k: int = 5) -> float:
    if not relevant:
        return 0.0
    if not retrieved:
        return 0.0
    top_k = retrieved[: _normalize_k(k)]
    hits = sum(1 for item in top_k if item in relevant)
    return hits / len(relevant)


def mrr(retrieved: list[str], relevant: set[str]) -> float:
    if not retrieved:
        return 0.0
    for idx, item in enumerate(retrieved, start=1):
        if item in relevant:
            return 1.0 / idx
    return 0.0


def ndcg_at_k(retrieved: list[str], relevant: set[str], k: int = 5) -> float:
    if not relevant or not retrieved:
        return 0.0
    top_k = retrieved[: _normalize_k(k)]
    dcg = 0.0
    for rank, item in enumerate(top_k, start=1):
        if item in relevant:
            dcg += 1.0 / log2(rank + 1)
    ideal_count = min(len(relevant), _normalize_k(k))
    idcg = 0.0
    for rank in range(1, ideal_count + 1):
        idcg += 1.0 / log2(rank + 1)
    if idcg == 0:
        return 0.0
    return dcg / idcg


def evaluate_query(retrieved: list[str], relevant: set[str], k: int = 5) -> dict[str, float]:
    return {
        "precision@5": precision_at_k(retrieved, relevant, k=k),
        "recall@5": recall_at_k(retrieved, relevant, k=k),
        "mrr": mrr(retrieved, relevant),
        "ndcg@5": ndcg_at_k(retrieved, relevant, k=k),
    }


def aggregate_metrics(results: list[dict[str, Any]]) -> dict[str, float]:
    if not results:
        return {"precision@5": 0.0, "recall@5": 0.0, "mrr": 0.0, "ndcg@5": 0.0}
    keys = ["precision@5", "recall@5", "mrr", "ndcg@5"]
    averages = {}
    for key in keys:
        averages[key] = sum(float(result[key]) for result in results) / len(results)
    return averages

from app.evaluation.dataset import get_evaluation_dataset
from app.evaluation.metrics import (
    aggregate_metrics,
    evaluate_query,
    mrr,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)


def test_precision_at_5_correctness() -> None:
    retrieved = ["job-1", "job-2", "job-3", "job-4", "job-5"]
    relevant = {"job-2", "job-5"}
    assert precision_at_k(retrieved, relevant, k=5) == 0.4


def test_recall_at_5_correctness() -> None:
    retrieved = ["job-1", "job-2", "job-3", "job-4", "job-5"]
    relevant = {"job-2", "job-5", "job-9"}
    assert recall_at_k(retrieved, relevant, k=5) == 2 / 3


def test_mrr_correctness() -> None:
    retrieved = ["job-9", "job-2", "job-3", "job-4"]
    relevant = {"job-2", "job-7"}
    assert mrr(retrieved, relevant) == 0.5


def test_ndcg_at_5_correctness() -> None:
    retrieved = ["job-3", "job-1", "job-9"]
    relevant = {"job-1", "job-9"}
    assert abs(ndcg_at_k(retrieved, relevant, k=5) - 0.6934264036172708) < 1e-9


def test_evaluation_aggregation() -> None:
    results = [
        evaluate_query(["job-1", "job-2", "job-3", "job-4", "job-5"], {"job-2", "job-5"}),
        evaluate_query(["job-2", "job-1"], {"job-4"}),
    ]
    summary = aggregate_metrics(results)

    assert summary["precision@5"] == 0.2
    assert summary["recall@5"] == 0.5
    assert summary["mrr"] == 0.25
    assert abs(summary["ndcg@5"] - 0.31202526000191894) < 1e-9


def test_empty_result_handling() -> None:
    assert precision_at_k([], set(), k=5) == 0.0
    assert recall_at_k([], set(), k=5) == 0.0
    assert mrr([], set()) == 0.0
    assert ndcg_at_k([], set(), k=5) == 0.0


def test_dataset_validation() -> None:
    dataset = get_evaluation_dataset()
    job_ids = {job["job_id"] for job in dataset["jobs"]}
    assert len(dataset["queries"]) == 30
    assert all(query["relevant_job_ids"] for query in dataset["queries"])
    assert all(set(query["relevant_job_ids"]).issubset(job_ids) for query in dataset["queries"])
    assert len({query["query_id"] for query in dataset["queries"]}) == 30

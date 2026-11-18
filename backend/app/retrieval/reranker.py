from __future__ import annotations

from typing import Any

from sentence_transformers import CrossEncoder


class CrossEncoderReranker:
    _model: CrossEncoder | None = None

    def __init__(self, model_name: str = "cross-encoder/stsb-roberta-base") -> None:
        self.model_name = model_name
        self.model = self.get_model()

    @classmethod
    def get_model(cls) -> CrossEncoder:
        if cls._model is None:
            cls._model = CrossEncoder("cross-encoder/stsb-roberta-base")
        return cls._model

    def rerank(self, query: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not candidates:
            return []

        pairs = [(query, self._candidate_text(candidate)) for candidate in candidates]
        scores = self.model.predict(pairs)
        ranked: list[dict[str, Any]] = []
        for candidate, score in zip(candidates, scores):
            item = dict(candidate)
            item["rerank_score"] = float(score)
            ranked.append(item)
        return sorted(ranked, key=lambda item: float(item["rerank_score"]), reverse=True)

    @staticmethod
    def _candidate_text(candidate: dict[str, Any]) -> str:
        return " ".join(
            [
                candidate.get("title", ""),
                candidate.get("company", ""),
                candidate.get("description", ""),
                " ".join(candidate.get("required_skills", [])),
            ]
        )

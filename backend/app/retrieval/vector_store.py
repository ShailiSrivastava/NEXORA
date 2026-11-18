from __future__ import annotations

import json
import os
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer


class VectorStore:
    _embedding_model: SentenceTransformer | None = None

    def __init__(self, collection_name: str = "jobs", persist_directory: str | None = None) -> None:
        self.collection_name = collection_name
        self.persist_directory = persist_directory or os.path.join(os.getcwd(), ".chroma")
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        self.collection = self.client.get_or_create_collection(name=self.collection_name)

    @classmethod
    def get_embedding_model(cls) -> SentenceTransformer:
        if cls._embedding_model is None:
            cls._embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        return cls._embedding_model

    @staticmethod
    def _normalize_embedding(value: Any) -> list[float]:
        if hasattr(value, "tolist"):
            return value.tolist()
        if isinstance(value, list):
            return [float(item) for item in value]
        return [float(value)]

    @staticmethod
    def _serialize_required_skills(skills: Any) -> str:
        if isinstance(skills, list):
            return json.dumps(skills)
        if isinstance(skills, str):
            try:
                parsed = json.loads(skills)
                if isinstance(parsed, list):
                    return json.dumps(parsed)
            except json.JSONDecodeError:
                pass
            return json.dumps([item.strip() for item in skills.split(",") if item.strip()])
        return "[]"

    @staticmethod
    def _deserialize_required_skills(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            except json.JSONDecodeError:
                pass
            return [item.strip() for item in value.split(",") if item.strip()] if value else []
        return []

    def upsert_job(self, job: dict[str, Any]) -> None:
        job_id = str(job["job_id"])
        required_skills = self._deserialize_required_skills(job.get("required_skills", []))
        payload = {
            "job_id": job_id,
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "description": job.get("description", ""),
            "location": job.get("location", ""),
            "remote": bool(job.get("remote", False)),
            "experience_level": job.get("experience_level", ""),
            "required_skills": self._serialize_required_skills(required_skills),
            "salary": job.get("salary", ""),
            "role": job.get("role", ""),
        }

        embedding_input = f"{payload['title']} {payload['company']} {payload['description']} {' '.join(required_skills)}"
        embedding = self._normalize_embedding(self.get_embedding_model().encode([embedding_input], convert_to_numpy=True)[0])
        self.collection.upsert(
            ids=[job_id],
            embeddings=[embedding],
            metadatas=[payload],
            documents=[embedding_input],
        )

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        result = self.collection.get(ids=[job_id], include=["metadatas", "documents", "embeddings"])
        if not result["ids"]:
            return None

        metadata = result["metadatas"][0]
        return {
            "job_id": metadata.get("job_id"),
            "title": metadata.get("title"),
            "company": metadata.get("company"),
            "description": metadata.get("description"),
            "location": metadata.get("location"),
            "remote": metadata.get("remote"),
            "experience_level": metadata.get("experience_level"),
            "required_skills": self._deserialize_required_skills(metadata.get("required_skills", [])),
            "salary": metadata.get("salary", ""),
            "role": metadata.get("role"),
        }

    def search(self, query: str, top_k: int = 20) -> list[dict[str, Any]]:
        if not query or not query.strip():
            return []

        embedding = self._normalize_embedding(self.get_embedding_model().encode([query], convert_to_numpy=True)[0])
        result = self.collection.query(
            query_embeddings=[embedding],
            n_results=min(top_k, 20),
            include=["documents", "metadatas", "distances"],
        )

        items: list[dict[str, Any]] = []
        for idx, doc_id in enumerate(result["ids"][0]):
            metadata = result["metadatas"][0][idx]
            score = 1.0 / (1.0 + result["distances"][0][idx]) if result["distances"][0][idx] is not None else 1.0
            items.append({
                "job_id": doc_id,
                "title": metadata.get("title"),
                "company": metadata.get("company"),
                "description": metadata.get("description"),
                "location": metadata.get("location"),
                "remote": metadata.get("remote"),
                "experience_level": metadata.get("experience_level"),
                "required_skills": self._deserialize_required_skills(metadata.get("required_skills", [])),
                "role": metadata.get("role"),
                "salary": metadata.get("salary", ""),
                "score": score,
            })
        return items

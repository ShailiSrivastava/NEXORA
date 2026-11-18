from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from app.retrieval.reranker import CrossEncoderReranker
from app.retrieval.vector_store import VectorStore
from app.services.personalization_service import PersonalizationService


def test_vector_upsert_and_retrieval() -> None:
    mock_collection = Mock()
    mock_client = Mock()
    mock_client.get_or_create_collection.return_value = mock_collection
    mock_collection.query.return_value = {
        "ids": [["job-1", "job-2"]],
        "metadatas": [[{"title": "Python Engineer", "company": "Acme", "description": "Python backend role", "location": "remote", "remote": True, "experience_level": "mid", "required_skills": ["python", "sql"], "role": "backend"}, {"title": "Data Analyst", "company": "Beta", "description": "SQL reporting role", "location": "nyc", "remote": False, "experience_level": "junior", "required_skills": ["sql"], "role": "data"}]],
        "distances": [[0.2, 0.7]],
    }

    with patch("app.retrieval.vector_store.chromadb.PersistentClient", return_value=mock_client):
        with patch.object(VectorStore, "get_embedding_model") as embed_mock:
            embed_mock.return_value.encode.return_value = [Mock().tolist.return_value for _ in range(2)]
            embed_mock.return_value.encode.return_value = [[0.1, 0.2], [0.3, 0.4]]
            store = VectorStore()
            store.upsert_job({"job_id": "job-1", "title": "Python Engineer", "company": "Acme", "description": "Python backend role", "required_skills": ["python", "sql"], "location": "remote", "remote": True, "experience_level": "mid", "role": "backend"})
            results = store.search("python backend", top_k=2)

    assert results[0]["job_id"] == "job-1"
    assert len(results) == 2


def test_reranking_order() -> None:
    reranker = CrossEncoderReranker.__new__(CrossEncoderReranker)
    reranker.model = Mock()
    reranker.model.predict.side_effect = [
        [0.95, 0.4],
    ]

    jobs = [
        {"job_id": "job-1", "title": "Senior Python Engineer", "company": "A", "description": "Python backend role", "required_skills": ["python"]},
        {"job_id": "job-2", "title": "UI Engineer", "company": "B", "description": "CSS frontend work", "required_skills": ["css"]},
    ]

    ranked = reranker.rerank("python backend developer", jobs)
    assert ranked[0]["job_id"] == "job-1"
    assert float(ranked[0]["rerank_score"]) >= float(ranked[1]["rerank_score"])


def test_personalization_boosts() -> None:
    service = PersonalizationService()
    candidate = {"skills": ["python", "sql"], "preferences": {"remote": True}, "location": "remote", "experience_level": "mid", "preferred_role": "backend"}
    jobs = [
        {"job_id": "job-1", "required_skills": ["python", "sql"], "remote": True, "location": "remote", "experience_level": "mid", "role": "backend", "rerank_score": 0.8},
        {"job_id": "job-2", "required_skills": ["java"], "remote": False, "location": "nyc", "experience_level": "senior", "role": "frontend", "rerank_score": 0.9},
    ]

    personalized = service.personalize(candidate, jobs)
    assert personalized[0]["job_id"] == "job-1"
    assert personalized[0]["personalization_boost"] > personalized[1]["personalization_boost"]


def test_preference_handling() -> None:
    service = PersonalizationService()
    candidate = {"skills": ["python"], "preferences": {"remote": True}, "location": "remote"}
    jobs = [
        {"job_id": "job-1", "required_skills": ["python"], "remote": True, "location": "remote", "rerank_score": 0.5},
        {"job_id": "job-2", "required_skills": ["python"], "remote": False, "location": "nyc", "rerank_score": 0.5},
    ]

    personalized = service.personalize(candidate, jobs)
    assert personalized[0]["job_id"] == "job-1"


def test_job_updates_without_duplication() -> None:
    mock_collection = Mock()
    mock_client = Mock()
    mock_client.get_or_create_collection.return_value = mock_collection

    with patch("app.retrieval.vector_store.chromadb.PersistentClient", return_value=mock_client):
        with patch.object(VectorStore, "get_embedding_model") as embed_mock:
            embed_mock.return_value.encode.return_value = [[0.1, 0.2]]
            store = VectorStore()
            store.upsert_job({"job_id": "job-42", "title": "Python Engineer", "company": "A", "description": "Python role", "required_skills": ["python"], "location": "remote", "remote": True, "experience_level": "mid", "role": "backend"})
            store.upsert_job({"job_id": "job-42", "title": "Senior Python Engineer", "company": "A", "description": "Python role", "required_skills": ["python", "fastapi"], "location": "remote", "remote": True, "experience_level": "senior", "role": "backend"})

    assert mock_collection.upsert.call_count == 2


def test_real_chroma_upsert_get_and_search_preserve_required_skills() -> None:
    class FakeEmbeddingModel:
        def encode(self, texts, convert_to_numpy=True):
            del convert_to_numpy
            return [[0.1, 0.2, 0.3] for _ in texts]

    job = {
        "job_id": "nexora-sde-001",
        "title": "Software Development Engineer Intern",
        "company": "NEXORA DemoTech",
        "description": "Entry-level software engineering internship involving backend development and REST API design.",
        "location": "Bengaluru, India",
        "remote": True,
        "experience_level": "Entry-level",
        "required_skills": ["Java", "Python", "JavaScript", "React.js", "Node.js", "REST APIs", "SQL", "Git", "Problem Solving"],
        "salary": "₹20,000 - ₹30,000/month",
        "role": "Software Engineer",
    }

    with TemporaryDirectory(ignore_cleanup_errors=True) as temp_directory:
        with patch.object(VectorStore, "get_embedding_model", return_value=FakeEmbeddingModel()):
            store = VectorStore(collection_name="jobs-regression", persist_directory=temp_directory)
            store.upsert_job(job)

            retrieved = store.get_job("nexora-sde-001")
            search_results = store.search("software engineer python java", top_k=5)

    assert retrieved is not None
    assert retrieved["job_id"] == "nexora-sde-001"
    assert retrieved["required_skills"] == job["required_skills"]
    assert retrieved["salary"] == job["salary"]
    assert search_results
    assert search_results[0]["job_id"] == "nexora-sde-001"
    assert search_results[0]["required_skills"] == job["required_skills"]

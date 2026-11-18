import type {
  AgentChatResponse,
  AgentHistoryResponse,
  CandidateProfile,
  EvaluationResponse,
  JobRecommendationsResponse,
  MatchResult,
} from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) detail = payload.detail;
    } catch {
      // Keep the status-based error when the response is not JSON.
    }
    throw new Error(detail);
  }

  return (await response.json()) as T;
}

export function saveProfile(sessionId: string, profile: CandidateProfile) {
  return apiRequest<{ session_id: string; profile: CandidateProfile }>("/api/agent/profile", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, profile }),
  });
}

export function getHistory(sessionId: string) {
  return apiRequest<AgentHistoryResponse>(`/api/agent/history/${encodeURIComponent(sessionId)}`);
}

export function chatWithAgent(sessionId: string, message: string) {
  return apiRequest<AgentChatResponse>("/api/agent/chat", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, message }),
  });
}

export function getRecommendations(sessionId: string, query: string, topK = 5) {
  const params = new URLSearchParams({ session_id: sessionId, query, top_k: String(topK) });
  return apiRequest<JobRecommendationsResponse>(`/api/jobs/recommendations?${params.toString()}`);
}

export function getMatch(candidateSkills: string[], jobDescription: string, jobId: string) {
  return apiRequest<MatchResult>("/api/match", {
    method: "POST",
    body: JSON.stringify({ candidate_skills: candidateSkills, job_description: jobDescription, job_id: jobId }),
  });
}

export function runEvaluation(topK = 5, includeRagas = false) {
  return apiRequest<EvaluationResponse>("/api/evaluation/run", {
    method: "POST",
    body: JSON.stringify({ top_k: topK, include_ragas: includeRagas }),
  });
}

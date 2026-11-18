export type ViewId = "overview" | "jobs" | "assistant" | "profile" | "evaluation";

export interface CandidateProfile {
  skills: string[];
  experience_level: string;
  location: string;
  preferences: {
    remote: boolean;
  };
  preferred_role: string;
}

export interface JobItem {
  job_id: string;
  title: string;
  company: string;
  description: string;
  location: string;
  remote: boolean;
  experience_level: string;
  required_skills: string[];
  salary?: string;
  role: string;
  score?: number;
  rerank_score?: number;
  personalization_boost?: number;
  final_score?: number;
  explanation?: string;
}

export interface JobRecommendationsResponse {
  session_id: string;
  query: string;
  original_ranking: JobItem[];
  reranked_ranking: JobItem[];
  final_personalized_ranking: JobItem[];
}

export interface MatchResult {
  job_id: string;
  match_score: number;
  matched_skills: string[];
  missing_skills: string[];
  reason: string;
}

export interface AgentHistoryMessage {
  role: string;
  content: string;
  timestamp: string;
}

export interface AgentHistoryResponse {
  session_id: string;
  history: AgentHistoryMessage[];
}

export interface ToolTraceItem {
  tool: string;
  arguments: Record<string, unknown>;
  result: Record<string, unknown>;
}

export interface AgentChatResponse {
  response: string;
  trace: ToolTraceItem[];
}

export interface EvaluationMetrics {
  "precision@5": number;
  "recall@5": number;
  mrr: number;
  "ndcg@5": number;
}

export interface EvaluationRow {
  query_id: string;
  query: string;
  strategy: string;
  retrieved: string[];
  relevant: string[];
  "precision@5": number;
  "recall@5": number;
  mrr: number;
  "ndcg@5": number;
}

export interface EvaluationResponse {
  top_k: number;
  dataset_size: number;
  summary: Record<"baseline" | "reranked" | "personalized", EvaluationMetrics>;
  strategy_results: Record<"baseline" | "reranked" | "personalized", EvaluationRow[]>;
  ragas?: {
    status: "executed" | "skipped";
    reason?: string;
    result?: unknown;
  };
}

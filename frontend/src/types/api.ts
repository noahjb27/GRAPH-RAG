// API Types for Graph-RAG Research System
// These types correspond to the FastAPI backend responses

// System Status Types
export interface SystemStatus {
  neo4j_connected: boolean;
  available_llm_providers: string[];
  available_pipelines: string[];
  total_questions: number;
}

// LLM Provider Types
export interface LLMProviderInfo {
  name: string;
  available: boolean;
  connected: boolean;
}

export interface LLMProvidersResponse {
  providers: LLMProviderInfo[];
  total_available: number;
}

// Pipeline Types
export interface PipelineInfo {
  name: string;
  display_name: string;
  description: string;
  required_capabilities: string[];
  stats: Record<string, any>;
}

export interface PipelinesResponse {
  pipelines: PipelineInfo[];
}

// Question Types
export interface Question {
  question_id: string;
  question_text: string;
  category: string;
  sub_category: string;
  difficulty: number;
  required_capabilities: string[];
  historical_context?: string;
  evaluation_method: string;
}

export interface QuestionDetails extends Question {
  ground_truth?: any;
  ground_truth_type?: string;
  cypher_query?: string;
  notes?: string;
}

export interface TaxonomySummary {
  total_questions: number;
  categories: Record<string, number>;
  difficulties: Record<string, number>;
  avg_difficulty: number;
}

export interface QuestionsResponse {
  questions: Question[];
  total: number;
  taxonomy_summary: TaxonomySummary;
}

// Evaluation Types
export interface EvaluationResult {
  question_id: string;
  question_text: string;
  pipeline_name: string;
  llm_provider: string;
  answer: string;
  success: boolean;
  execution_time_seconds: number;
  cost_usd: number;
  total_tokens: number;
  tokens_per_second?: number;
  generated_cypher?: string;
  error_message?: string;
  timestamp?: string;
  metadata?: Record<string, any>;
}

export interface EvaluationSummary {
  total_evaluations: number;
  successful_evaluations: number;
  failed_evaluations: number;
  success_rate: number;
  avg_execution_time: number;
  total_cost: number;
  total_tokens: number;
  avg_tokens_per_second: number;
}

export interface PipelineComparison {
  pipeline_name: string;
  success_rate: number;
  avg_execution_time: number;
  avg_cost: number;
  total_evaluations: number;
}

export interface LLMComparison {
  llm_provider: string;
  success_rate: number;
  avg_execution_time: number;
  avg_cost: number;
  avg_tokens_per_second: number;
  total_evaluations: number;
}

export interface SingleQuestionEvaluationResponse {
  results: EvaluationResult[];
  summary: EvaluationSummary;
  total_evaluations: number;
}

export interface BatchEvaluationResponse extends SingleQuestionEvaluationResponse {
  pipeline_comparison: PipelineComparison[];
  llm_comparison: LLMComparison[];
}

// Request Types
export interface SingleQuestionRequest {
  question_id: string;
  pipeline_names: string[];
  llm_providers: string[];
}

export interface BatchEvaluationRequest {
  pipeline_names: string[];
  llm_providers: string[];
  question_count?: number;
  categories?: string[];
  max_difficulty?: number;
}

export interface QueryRequest {
  question: string;
  pipeline_names: string[];
  llm_providers: string[];
}

// Database Types
export interface DatabaseInfo {
  database_info: Record<string, any>;
  connection_status: string;
  error?: string;
}

// Health Check Types
export interface HealthStatus {
  status: string;
  timestamp: number;
  components: {
    neo4j: string;
    llm_providers: Record<string, boolean> | string;
  };
}

// API Response Wrapper
export interface APIResponse<T> {
  data?: T;
  error?: string;
  status: number;
}

// Utility types
export type DifficultyLevel = 1 | 2 | 3 | 4 | 5;

export interface QuestionFilters {
  category?: string;
  difficulty?: DifficultyLevel;
  limit?: number;
} 
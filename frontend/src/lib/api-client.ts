import {
  SystemStatus,
  LLMProvidersResponse,
  PipelinesResponse,
  QuestionsResponse,
  QuestionDetails,
  SingleQuestionEvaluationResponse,
  BatchEvaluationResponse,
  DatabaseInfo,
  HealthStatus,
  SingleQuestionRequest,
  BatchEvaluationRequest,
  QuestionFilters,
  APIResponse,
  GraphRAGRequest,
  GraphRAGResponse,
  GraphRAGCacheRequest,
  GraphRAGCacheResponse,
  GraphRAGCacheStats,
} from '@/types/api';

class APIError extends Error {
  constructor(
    message: string,
    public status?: number,
    public statusText?: string
  ) {
    super(message);
    this.name = 'APIError';
  }
}

class APIClient {
  private baseURL: string;

  constructor(baseURL: string = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000') {
    this.baseURL = baseURL.replace(/\/+$/, ''); // Remove trailing slashes
  }

  private async makeRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<APIResponse<T>> {
    const url = `${this.baseURL}${endpoint}`;
    
    const defaultHeaders = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    try {
      const response = await fetch(url, {
        ...options,
        headers: defaultHeaders,
      });

      let data: T | undefined;
      const contentType = response.headers.get('content-type');
      
      if (contentType && contentType.includes('application/json')) {
        data = await response.json();
      }

      if (!response.ok) {
        throw new APIError(
          `HTTP error ${response.status}: ${response.statusText}`,
          response.status,
          response.statusText
        );
      }

      return {
        data,
        status: response.status,
      };
    } catch (error) {
      if (error instanceof APIError) {
        return {
          error: error.message,
          status: error.status || 500,
        };
      }

      return {
        error: error instanceof Error ? error.message : 'Unknown error occurred',
        status: 500,
      };
    }
  }

  // System endpoints
  async getSystemStatus(): Promise<APIResponse<SystemStatus>> {
    return this.makeRequest<SystemStatus>('/status');
  }

  async getHealthStatus(): Promise<APIResponse<HealthStatus>> {
    return this.makeRequest<HealthStatus>('/health');
  }

  async getDatabaseInfo(): Promise<APIResponse<DatabaseInfo>> {
    return this.makeRequest<DatabaseInfo>('/database/info');
  }

  // LLM Provider endpoints
  async getLLMProviders(): Promise<APIResponse<LLMProvidersResponse>> {
    return this.makeRequest<LLMProvidersResponse>('/llm-providers');
  }

  // Pipeline endpoints
  async getPipelines(): Promise<APIResponse<PipelinesResponse>> {
    return this.makeRequest<PipelinesResponse>('/pipelines');
  }

  // Question endpoints
  async getQuestions(filters?: QuestionFilters): Promise<APIResponse<QuestionsResponse>> {
    const queryParams = new URLSearchParams();
    
    if (filters?.category) {
      queryParams.append('category', filters.category);
    }
    if (filters?.difficulty) {
      queryParams.append('difficulty', filters.difficulty.toString());
    }
    if (filters?.limit) {
      queryParams.append('limit', filters.limit.toString());
    }

    const endpoint = `/questions${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
    return this.makeRequest<QuestionsResponse>(endpoint);
  }

  async getQuestionDetails(questionId: string): Promise<APIResponse<QuestionDetails>> {
    return this.makeRequest<QuestionDetails>(`/questions/${questionId}`);
  }

  // Evaluation endpoints
  async evaluateSingleQuestion(
    request: SingleQuestionRequest
  ): Promise<APIResponse<SingleQuestionEvaluationResponse>> {
    return this.makeRequest<SingleQuestionEvaluationResponse>('/evaluate/question', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async evaluateSampleQuestions(
    request: BatchEvaluationRequest
  ): Promise<APIResponse<BatchEvaluationResponse>> {
    return this.makeRequest<BatchEvaluationResponse>('/evaluate/sample', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // GraphRAG Methods
  async graphragQuery(request: GraphRAGRequest): Promise<APIResponse<GraphRAGResponse>> {
    return await this.makeRequest<GraphRAGResponse>('/graphrag/query', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async getGraphRAGCacheStats(): Promise<APIResponse<{ cache_stats: GraphRAGCacheStats }>> {
    return await this.makeRequest<{ cache_stats: GraphRAGCacheStats }>('/graphrag/cache/stats');
  }

  async manageGraphRAGCache(request: GraphRAGCacheRequest): Promise<APIResponse<GraphRAGCacheResponse>> {
    return await this.makeRequest<GraphRAGCacheResponse>('/graphrag/cache/manage', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // Utility methods
  async ping(): Promise<boolean> {
    try {
      const response = await this.makeRequest('/');
      return response.status === 200;
    } catch {
      return false;
    }
  }

  setBaseURL(url: string): void {
    this.baseURL = url.replace(/\/+$/, '');
  }

  getBaseURL(): string {
    return this.baseURL;
  }
}

// Create a singleton instance
export const apiClient = new APIClient();

// Export the class for potential multiple instances
export { APIClient, APIError };

// SWR fetcher functions for common endpoints
export const fetchers = {
  systemStatus: () => apiClient.getSystemStatus(),
  healthStatus: () => apiClient.getHealthStatus(),
  databaseInfo: () => apiClient.getDatabaseInfo(),
  llmProviders: () => apiClient.getLLMProviders(),
  pipelines: () => apiClient.getPipelines(),
  questions: (filters?: QuestionFilters) => apiClient.getQuestions(filters),
  questionDetails: (questionId: string) => apiClient.getQuestionDetails(questionId),
  graphragCacheStats: () => apiClient.getGraphRAGCacheStats(),
};

// Utility function to handle API responses
export function handleAPIResponse<T>(response: APIResponse<T>): T {
  if (response.error) {
    throw new APIError(response.error, response.status);
  }
  
  if (!response.data) {
    throw new APIError('No data received from API', response.status);
  }
  
  return response.data;
} 
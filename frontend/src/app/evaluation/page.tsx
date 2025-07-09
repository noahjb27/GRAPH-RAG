'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { apiClient, handleAPIResponse } from '@/lib/api-client';
import { 
  SystemStatus, 
  LLMProvidersResponse, 
  PipelinesResponse, 
  QuestionsResponse,
  SingleQuestionRequest,
  BatchEvaluationRequest,
  SingleQuestionEvaluationResponse,
  BatchEvaluationResponse,
  Question
} from '@/types/api';
import { 
  Play, 
  Settings, 
  Zap,
  MessageSquare,
  RefreshCw,
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle
} from 'lucide-react';
import { 
  formatDuration, 
  formatCurrency, 
  formatNumber, 
  formatPercentage, 
  getDifficultyLabel, 
  getDifficultyColor 
} from '@/lib/utils';

interface EvaluationState {
  isRunning: boolean;
  type: 'single' | 'batch' | null;
  results: SingleQuestionEvaluationResponse | BatchEvaluationResponse | null;
  error: string | null;
}

export default function EvaluationPage() {
  // System data
  const [llmProviders, setLLMProviders] = useState<LLMProvidersResponse | null>(null);
  const [pipelines, setPipelines] = useState<PipelinesResponse | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Evaluation configuration
  const [selectedPipelines, setSelectedPipelines] = useState<string[]>([]);
  const [selectedProviders, setSelectedProviders] = useState<string[]>([]);
  const [selectedQuestion, setSelectedQuestion] = useState<string>('');
  const [batchSize, setBatchSize] = useState(5);
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [maxDifficulty, setMaxDifficulty] = useState(3);

  // Evaluation state
  const [evaluation, setEvaluation] = useState<EvaluationState>({
    isRunning: false,
    type: null,
    results: null,
    error: null,
  });

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [providersResponse, pipelinesResponse, questionsResponse] = await Promise.all([
        apiClient.getLLMProviders(),
        apiClient.getPipelines(),
        apiClient.getQuestions({ limit: 50 }),
      ]);

      const providersData = handleAPIResponse(providersResponse);
      const pipelinesData = handleAPIResponse(pipelinesResponse);
      const questionsData = handleAPIResponse(questionsResponse);

      setLLMProviders(providersData);
      setPipelines(pipelinesData);
      setQuestions(questionsData.questions);

      // Auto-select connected providers and available pipelines
      const connectedProviders = providersData.providers
        .filter(p => p.connected)
        .map(p => p.name);
      setSelectedProviders(connectedProviders);

      if (pipelinesData.pipelines.length > 0) {
        setSelectedPipelines([pipelinesData.pipelines[0].name]);
      }

      if (questionsData.questions.length > 0) {
        setSelectedQuestion(questionsData.questions[0].question_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch initial data');
    } finally {
      setLoading(false);
    }
  };

  const runSingleEvaluation = async () => {
    if (!selectedQuestion || selectedPipelines.length === 0 || selectedProviders.length === 0) {
      setEvaluation(prev => ({ ...prev, error: 'Please select a question, at least one pipeline, and one LLM provider' }));
      return;
    }

    try {
      setEvaluation({
        isRunning: true,
        type: 'single',
        results: null,
        error: null,
      });

      const request: SingleQuestionRequest = {
        question_id: selectedQuestion,
        pipeline_names: selectedPipelines,
        llm_providers: selectedProviders,
      };

      const response = await apiClient.evaluateSingleQuestion(request);
      const results = handleAPIResponse(response);

      setEvaluation({
        isRunning: false,
        type: 'single',
        results,
        error: null,
      });
    } catch (err) {
      setEvaluation({
        isRunning: false,
        type: 'single',
        results: null,
        error: err instanceof Error ? err.message : 'Evaluation failed',
      });
    }
  };

  const runBatchEvaluation = async () => {
    if (selectedPipelines.length === 0 || selectedProviders.length === 0) {
      setEvaluation(prev => ({ ...prev, error: 'Please select at least one pipeline and one LLM provider' }));
      return;
    }

    try {
      setEvaluation({
        isRunning: true,
        type: 'batch',
        results: null,
        error: null,
      });

      const request: BatchEvaluationRequest = {
        pipeline_names: selectedPipelines,
        llm_providers: selectedProviders,
        question_count: batchSize,
        categories: selectedCategories.length > 0 ? selectedCategories : undefined,
        max_difficulty: maxDifficulty,
      };

      const response = await apiClient.evaluateSampleQuestions(request);
      const results = handleAPIResponse(response);

      setEvaluation({
        isRunning: false,
        type: 'batch',
        results,
        error: null,
      });
    } catch (err) {
      setEvaluation({
        isRunning: false,
        type: 'batch',
        results: null,
        error: err instanceof Error ? err.message : 'Batch evaluation failed',
      });
    }
  };

  const clearResults = () => {
    setEvaluation({
      isRunning: false,
      type: null,
      results: null,
      error: null,
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center space-x-2 text-gray-600">
          <RefreshCw className="h-5 w-5 animate-spin" />
          <span>Loading evaluation configuration...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-4">
        <div className="text-red-600 flex items-center space-x-2">
          <XCircle className="h-5 w-5" />
          <span>Error loading evaluation page: {error}</span>
        </div>
        <Button onClick={fetchInitialData} variant="outline">
          Try Again
        </Button>
      </div>
    );
  }

  const availableCategories = Array.from(new Set(questions.map(q => q.category)));
  const selectedQuestionObj = questions.find(q => q.question_id === selectedQuestion);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Evaluation</h1>
          <p className="text-gray-600 mt-1">
            Run Graph-RAG evaluations with different pipelines and LLM providers
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button onClick={fetchInitialData} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          {evaluation.results && (
            <Button onClick={clearResults} variant="outline" size="sm">
              Clear Results
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Configuration Panel */}
        <div className="lg:col-span-1 space-y-6">
          {/* Pipeline Selection */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Zap className="h-5 w-5" />
                <span>Pipelines</span>
              </CardTitle>
              <CardDescription>Select evaluation pipelines to test</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {pipelines?.pipelines.map((pipeline) => (
                  <label key={pipeline.name} className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedPipelines.includes(pipeline.name)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedPipelines([...selectedPipelines, pipeline.name]);
                        } else {
                          setSelectedPipelines(selectedPipelines.filter(p => p !== pipeline.name));
                        }
                      }}
                      className="rounded"
                    />
                    <div className="flex-1">
                      <div className="font-medium">{pipeline.display_name}</div>
                      <div className="text-xs text-gray-600">{pipeline.description}</div>
                    </div>
                  </label>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* LLM Provider Selection */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Settings className="h-5 w-5" />
                <span>LLM Providers</span>
              </CardTitle>
              <CardDescription>Select language model providers</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {llmProviders?.providers.map((provider) => (
                  <label key={provider.name} className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedProviders.includes(provider.name)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedProviders([...selectedProviders, provider.name]);
                        } else {
                          setSelectedProviders(selectedProviders.filter(p => p !== provider.name));
                        }
                      }}
                      disabled={!provider.connected}
                      className="rounded"
                    />
                    <div className="flex-1 flex items-center justify-between">
                      <div>
                        <div className="font-medium capitalize">{provider.name}</div>
                        <div className="text-xs text-gray-600">
                          {provider.connected ? 'Connected' : 'Disconnected'}
                        </div>
                      </div>
                      <Badge variant={provider.connected ? 'success' : 'error'}>
                        {provider.connected ? 'Available' : 'Offline'}
                      </Badge>
                    </div>
                  </label>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Evaluation Controls */}
        <div className="lg:col-span-2 space-y-6">
          {/* Single Question Evaluation */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <MessageSquare className="h-5 w-5" />
                <span>Single Question Evaluation</span>
              </CardTitle>
              <CardDescription>
                Evaluate a specific question across selected pipelines and providers
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select Question
                </label>
                <select
                  value={selectedQuestion}
                  onChange={(e) => setSelectedQuestion(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  {questions.map((question) => (
                    <option key={question.question_id} value={question.question_id}>
                      {question.question_text.substring(0, 80)}...
                    </option>
                  ))}
                </select>
              </div>

              {selectedQuestionObj && (
                <div className="p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">Selected Question</span>
                    <Badge 
                      variant="outline" 
                      className={getDifficultyColor(selectedQuestionObj.difficulty)}
                    >
                      {getDifficultyLabel(selectedQuestionObj.difficulty)}
                    </Badge>
                  </div>
                  <p className="text-sm text-gray-700">{selectedQuestionObj.question_text}</p>
                  <div className="mt-2 text-xs text-gray-600">
                    {selectedQuestionObj.category} • {selectedQuestionObj.sub_category}
                  </div>
                </div>
              )}

              <Button 
                onClick={runSingleEvaluation}
                disabled={evaluation.isRunning || !selectedQuestion || selectedPipelines.length === 0 || selectedProviders.length === 0}
                loading={evaluation.isRunning && evaluation.type === 'single'}
                className="w-full"
              >
                <Play className="h-4 w-4 mr-2" />
                Run Single Evaluation
              </Button>
            </CardContent>
          </Card>

          {/* Batch Evaluation */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Zap className="h-5 w-5" />
                <span>Batch Evaluation</span>
              </CardTitle>
              <CardDescription>
                Evaluate multiple questions for comprehensive testing
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Number of Questions
                  </label>
                  <input
                    type="number"
                    value={batchSize}
                    onChange={(e) => setBatchSize(Number(e.target.value))}
                    min="1"
                    max="20"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Max Difficulty
                  </label>
                  <select
                    value={maxDifficulty}
                    onChange={(e) => setMaxDifficulty(Number(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    {[1, 2, 3, 4, 5].map((difficulty) => (
                      <option key={difficulty} value={difficulty}>
                        {getDifficultyLabel(difficulty)} ({difficulty})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Categories (optional)
                </label>
                <div className="flex flex-wrap gap-2">
                  {availableCategories.map((category) => (
                    <label key={category} className="inline-flex items-center">
                      <input
                        type="checkbox"
                        checked={selectedCategories.includes(category)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedCategories([...selectedCategories, category]);
                          } else {
                            setSelectedCategories(selectedCategories.filter(c => c !== category));
                          }
                        }}
                        className="rounded mr-2"
                      />
                      <Badge variant="outline" className="text-xs">
                        {category}
                      </Badge>
                    </label>
                  ))}
                </div>
              </div>

              <Button 
                onClick={runBatchEvaluation}
                disabled={evaluation.isRunning || selectedPipelines.length === 0 || selectedProviders.length === 0}
                loading={evaluation.isRunning && evaluation.type === 'batch'}
                className="w-full"
              >
                <Zap className="h-4 w-4 mr-2" />
                Run Batch Evaluation
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Results Section */}
      {(evaluation.results || evaluation.error) && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              {evaluation.error ? (
                <XCircle className="h-5 w-5 text-red-600" />
              ) : (
                <CheckCircle className="h-5 w-5 text-green-600" />
              )}
              <span>Evaluation Results</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {evaluation.error ? (
              <div className="text-red-600 flex items-center space-x-2">
                <AlertCircle className="h-5 w-5" />
                <span>{evaluation.error}</span>
              </div>
            ) : evaluation.results ? (
              <div className="space-y-6">
                {/* Summary */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="text-center p-3 bg-blue-50 rounded-lg">
                    <div className="text-2xl font-bold text-blue-600">
                      {evaluation.results.summary.total_evaluations}
                    </div>
                    <div className="text-sm text-gray-600">Total Evaluations</div>
                  </div>
                  <div className="text-center p-3 bg-green-50 rounded-lg">
                    <div className="text-2xl font-bold text-green-600">
                      {formatPercentage(evaluation.results.summary.success_rate)}
                    </div>
                    <div className="text-sm text-gray-600">Success Rate</div>
                  </div>
                  <div className="text-center p-3 bg-yellow-50 rounded-lg">
                    <div className="text-2xl font-bold text-yellow-600">
                      {formatDuration(evaluation.results.summary.avg_execution_time)}
                    </div>
                    <div className="text-sm text-gray-600">Avg Time</div>
                  </div>
                  <div className="text-center p-3 bg-purple-50 rounded-lg">
                    <div className="text-2xl font-bold text-purple-600">
                      {formatCurrency(evaluation.results.summary.total_cost)}
                    </div>
                    <div className="text-sm text-gray-600">Total Cost</div>
                  </div>
                </div>

                {/* Detailed Results */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold">Detailed Results</h3>
                  {evaluation.results.results.map((result, index) => (
                    <div key={index} className="border rounded-lg p-4">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1">
                          <h4 className="font-medium">{result.question_text}</h4>
                          <div className="text-sm text-gray-600 mt-1">
                            {result.pipeline_name} • {result.llm_provider}
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Badge variant={result.success ? 'success' : 'error'}>
                            {result.success ? 'Success' : 'Failed'}
                          </Badge>
                          <div className="text-sm text-gray-600">
                            {formatDuration(result.execution_time_seconds)}
                          </div>
                        </div>
                      </div>
                      
                      {result.answer && (
                        <div className="mt-3 p-3 bg-gray-50 rounded">
                          <div className="text-sm font-medium text-gray-700 mb-1">Answer:</div>
                          <div className="text-sm">{result.answer}</div>
                        </div>
                      )}
                      
                      {result.error_message && (
                        <div className="mt-3 p-3 bg-red-50 rounded">
                          <div className="text-sm font-medium text-red-700 mb-1">Error:</div>
                          <div className="text-sm text-red-600">{result.error_message}</div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>
      )}
    </div>
  );
} 
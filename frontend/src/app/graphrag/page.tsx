'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { apiClient, handleAPIResponse } from '@/lib/api-client';
import { useAPIData } from '@/lib/api-context';
import { 
  GraphRAGRequest,
  GraphRAGResponse,
  GraphRAGCacheStats,
  GraphRAGCacheRequest,
  LLMProvidersResponse,
  SystemStatus 
} from '@/types/api';
import { 
  Brain, 
  Layers3,
  Database,
  RefreshCw,
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle,
  Trash2,
  Flame,
  BarChart3,
  Search,
  Filter,
  Calendar,
  MapPin,
  MessageSquare
} from 'lucide-react';

interface GraphRAGState {
  isQuerying: boolean;
  response: GraphRAGResponse | null;
  error: string | null;
}

interface CacheState {
  isLoading: boolean;
  stats: GraphRAGCacheStats | null;
  error: string | null;
}

export default function GraphRAGPage() {
  // Data from context
  const { systemStatus, llmProviders } = useAPIData();
  
  // Query state
  const [queryState, setQueryState] = useState<GraphRAGState>({
    isQuerying: false,
    response: null,
    error: null
  });
  
  // Cache state
  const [cacheState, setCacheState] = useState<CacheState>({
    isLoading: false,
    stats: null,
    error: null
  });
  
  // Form state
  const [query, setQuery] = useState('');
  const [selectedLLM, setSelectedLLM] = useState('openai');
  const [yearFilter, setYearFilter] = useState<number | undefined>();
  const [communityTypes, setCommunityTypes] = useState<string[]>([]);
  
  // Available options
  const availableYears = [1946, 1950, 1961, 1970, 1975, 1980, 1989];
  const availableCommunityTypes = ['geographic', 'temporal', 'operational', 'service_type'];
  const sampleQuestions = [
    "What were the main characteristics of Berlin's transport network in terms of political division?",
    "How did the transport network in East Berlin differ from West Berlin in 1970?",
    "What transport developments occurred during the pre-wall era (1950-1961)?",
    "Which geographic areas had the most comprehensive transport coverage?",
    "How did different transport modes (U-Bahn, S-Bahn, tram) evolve over time?"
  ];

  useEffect(() => {
    fetchCacheStats();
  }, []);

  const fetchCacheStats = async () => {
    setCacheState(prev => ({ ...prev, isLoading: true, error: null }));
    
    try {
      const response = await apiClient.getGraphRAGCacheStats();
      const data = handleAPIResponse(response);
      setCacheState({
        isLoading: false,
        stats: data.cache_stats,
        error: null
      });
    } catch (error) {
      setCacheState({
        isLoading: false,
        stats: null,
        error: error instanceof Error ? error.message : 'Failed to fetch cache stats'
      });
    }
  };

  const runGraphRAGQuery = async () => {
    if (!query.trim()) {
      setQueryState(prev => ({ ...prev, error: 'Please enter a question' }));
      return;
    }

    setQueryState({ isQuerying: true, response: null, error: null });
    
    try {
      const request: GraphRAGRequest = {
        question: query.trim(),
        llm_provider: selectedLLM,
        year_filter: yearFilter,
        community_types: communityTypes.length > 0 ? communityTypes : undefined
      };

      const response = await apiClient.graphragQuery(request);
      const data = handleAPIResponse(response);
      
      setQueryState({
        isQuerying: false,
        response: data,
        error: null
      });
    } catch (error) {
      setQueryState({
        isQuerying: false,
        response: null,
        error: error instanceof Error ? error.message : 'GraphRAG query failed'
      });
    }
  };

  const manageCacheAction = async (action: 'warm' | 'clear' | 'validate') => {
    setCacheState(prev => ({ ...prev, isLoading: true }));
    
    try {
      const request: GraphRAGCacheRequest = { action };
      const response = await apiClient.manageGraphRAGCache(request);
      const data = handleAPIResponse(response);
      
      // Refresh cache stats after action
      setTimeout(() => {
        fetchCacheStats();
      }, 1000);
      
      console.log(`Cache ${action} action completed:`, data);
    } catch (error) {
      setCacheState(prev => ({ 
        ...prev, 
        isLoading: false,
        error: error instanceof Error ? error.message : `Cache ${action} failed`
      }));
    }
  };

  const toggleCommunityType = (type: string) => {
    setCommunityTypes(prev => 
      prev.includes(type) 
        ? prev.filter(t => t !== type)
        : [...prev, type]
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-gray-200 pb-4">
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
          <Brain className="h-8 w-8 text-blue-600" />
          GraphRAG Transport Analysis
        </h1>
        <p className="text-gray-600 mt-2">
          Hierarchical community-based analysis of Berlin's historical transport network using GraphRAG methodology
        </p>
      </div>

      {/* System Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-green-600" />
            System Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {systemStatus?.available_pipelines?.includes('graphrag_transport') ? 'Available' : 'Unavailable'}
              </div>
              <div className="text-sm text-gray-600">GraphRAG Pipeline</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {systemStatus?.neo4j_connected ? 'Connected' : 'Disconnected'}
              </div>
              <div className="text-sm text-gray-600">Neo4j Database</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">
                {llmProviders?.providers?.filter(p => p.available).length || 0}
              </div>
              <div className="text-sm text-gray-600">Available LLMs</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Query Interface */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5 text-blue-600" />
            GraphRAG Query Interface
          </CardTitle>
          <CardDescription>
            Ask questions about Berlin's transport network using hierarchical community analysis
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Sample Questions */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Sample Questions (click to use):
            </label>
            <div className="space-y-2">
              {sampleQuestions.map((sampleQ, index) => (
                <Button
                  key={index}
                  variant="outline"
                  size="sm"
                  className="w-full text-left justify-start h-auto p-3"
                  onClick={() => setQuery(sampleQ)}
                >
                  <MessageSquare className="h-4 w-4 mr-2 flex-shrink-0" />
                  <span className="text-sm">{sampleQ}</span>
                </Button>
              ))}
            </div>
          </div>

          {/* Query Input */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Your Question:
            </label>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter your question about Berlin's transport network..."
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Configuration Options */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* LLM Provider */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                LLM Provider:
              </label>
              <select
                value={selectedLLM}
                onChange={(e) => setSelectedLLM(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {llmProviders?.providers?.filter(p => p.available).map(provider => (
                  <option key={provider.name} value={provider.name}>
                    {provider.name.toUpperCase()}
                  </option>
                ))}
              </select>
            </div>

            {/* Year Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-1">
                <Calendar className="h-4 w-4" />
                Year Filter:
              </label>
              <select
                value={yearFilter || ''}
                onChange={(e) => setYearFilter(e.target.value ? parseInt(e.target.value) : undefined)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All years</option>
                {availableYears.map(year => (
                  <option key={year} value={year}>{year}</option>
                ))}
              </select>
            </div>

            {/* Community Types */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-1">
                <Layers3 className="h-4 w-4" />
                Community Types:
              </label>
              <div className="space-y-1">
                {availableCommunityTypes.map(type => (
                  <label key={type} className="flex items-center space-x-2 text-sm">
                    <input
                      type="checkbox"
                      checked={communityTypes.includes(type)}
                      onChange={() => toggleCommunityType(type)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="capitalize">{type.replace('_', ' ')}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>

          {/* Submit Button */}
          <Button 
            onClick={runGraphRAGQuery}
            disabled={queryState.isQuerying || !query.trim()}
            className="w-full"
          >
            {queryState.isQuerying ? (
              <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Brain className="h-4 w-4 mr-2" />
            )}
            {queryState.isQuerying ? 'Analyzing...' : 'Run GraphRAG Analysis'}
          </Button>

          {/* Error Display */}
          {queryState.error && (
            <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-md">
              <XCircle className="h-5 w-5 text-red-600" />
              <span className="text-red-700">{queryState.error}</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Query Results */}
      {queryState.response && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              GraphRAG Analysis Results
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Metadata */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-gray-50 rounded-lg">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {queryState.response.communities_analyzed}
                </div>
                <div className="text-sm text-gray-600">Communities Analyzed</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {queryState.response.execution_time_seconds.toFixed(2)}s
                </div>
                <div className="text-sm text-gray-600">Execution Time</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {queryState.response.question_type}
                </div>
                <div className="text-sm text-gray-600">Question Type</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-orange-600">
                  {queryState.response.context_summaries_count}
                </div>
                <div className="text-sm text-gray-600">Context Summaries</div>
              </div>
            </div>

            {/* Answer */}
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Answer:</h3>
              <div className="p-4 bg-white border border-gray-200 rounded-lg">
                <div className="prose max-w-none">
                  {queryState.response.answer.split('\n').map((paragraph, index) => (
                    <p key={index} className="mb-2">{paragraph}</p>
                  ))}
                </div>
              </div>
            </div>

            {/* Configuration Used */}
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline">
                <Brain className="h-3 w-3 mr-1" />
                {queryState.response.approach}
              </Badge>
              {queryState.response.year_filter && (
                <Badge variant="outline">
                  <Calendar className="h-3 w-3 mr-1" />
                  Year: {queryState.response.year_filter}
                </Badge>
              )}
              {queryState.response.community_types && queryState.response.community_types.length > 0 && (
                <Badge variant="outline">
                  <Filter className="h-3 w-3 mr-1" />
                  Types: {queryState.response.community_types.join(', ')}
                </Badge>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Cache Management */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5 text-blue-600" />
            Cache Management
          </CardTitle>
          <CardDescription>
            Manage GraphRAG community detection and summary caches for optimal performance
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Cache Stats */}
          {cacheState.stats && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-gray-50 rounded-lg">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {cacheState.stats.total_cached_communities}
                </div>
                <div className="text-sm text-gray-600">Cached Communities</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {cacheState.stats.summary_caches}
                </div>
                <div className="text-sm text-gray-600">Cached Summaries</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {cacheState.stats.community_caches}
                </div>
                <div className="text-sm text-gray-600">Community Cache Files</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-orange-600">
                  {cacheState.stats.cache_dir_size_mb.toFixed(1)} MB
                </div>
                <div className="text-sm text-gray-600">Cache Size</div>
              </div>
            </div>
          )}

          {/* Cache Actions */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Button 
              onClick={() => manageCacheAction('warm')}
              disabled={cacheState.isLoading}
              variant="outline"
              className="flex items-center gap-2"
            >
              <Flame className="h-4 w-4" />
              Warm Cache
            </Button>
            
            <Button 
              onClick={() => manageCacheAction('validate')}
              disabled={cacheState.isLoading}
              variant="outline"
              className="flex items-center gap-2"
            >
              <CheckCircle className="h-4 w-4" />
              Validate Cache
            </Button>
            
            <Button 
              onClick={fetchCacheStats}
              disabled={cacheState.isLoading}
              variant="outline"
              className="flex items-center gap-2"
            >
              <BarChart3 className="h-4 w-4" />
              Refresh Stats
            </Button>
            
            <Button 
              onClick={() => manageCacheAction('clear')}
              disabled={cacheState.isLoading}
              variant="outline"
              className="flex items-center gap-2 text-red-600 hover:text-red-700"
            >
              <Trash2 className="h-4 w-4" />
              Clear Cache
            </Button>
          </div>

          {/* Cache Error */}
          {cacheState.error && (
            <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-md">
              <XCircle className="h-5 w-5 text-red-600" />
              <span className="text-red-700">{cacheState.error}</span>
            </div>
          )}

          {/* Loading Indicator */}
          {cacheState.isLoading && (
            <div className="flex items-center gap-2 p-3 bg-blue-50 border border-blue-200 rounded-md">
              <RefreshCw className="h-5 w-5 text-blue-600 animate-spin" />
              <span className="text-blue-700">Processing cache operation...</span>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
} 
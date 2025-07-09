'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { apiClient, handleAPIResponse } from '@/lib/api-client';
import { QuestionsResponse, Question, QuestionFilters } from '@/types/api';
import { 
  Search, 
  Filter, 
  MessageSquare,
  RefreshCw,
  ExternalLink
} from 'lucide-react';
import { getDifficultyColor, getDifficultyLabel, formatNumber, debounce } from '@/lib/utils';

export default function QuestionsPage() {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [categories, setCategories] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Filters
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedDifficulty, setSelectedDifficulty] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [limit, setLimit] = useState(20);

  const fetchQuestions = async (filters?: QuestionFilters) => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.getQuestions(filters);
      const data = handleAPIResponse(response);

      setQuestions(data.questions);
      setTotalQuestions(data.total);
      setCategories(data.taxonomy_summary.categories);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch questions');
    } finally {
      setLoading(false);
    }
  };

  // Debounced search function
  const debouncedFetch = debounce((filters: QuestionFilters) => {
    fetchQuestions(filters);
  }, 300);

  useEffect(() => {
    fetchQuestions();
  }, []);

  useEffect(() => {
    const filters: QuestionFilters = {
      ...(selectedCategory && { category: selectedCategory }),
      ...(selectedDifficulty && { difficulty: selectedDifficulty as any }),
      limit,
    };

    debouncedFetch(filters);
  }, [selectedCategory, selectedDifficulty, limit]);

  const handleClearFilters = () => {
    setSelectedCategory('');
    setSelectedDifficulty(null);
    setSearchQuery('');
    setLimit(20);
    fetchQuestions();
  };

  // Filter questions by search query locally
  const filteredQuestions = questions.filter(question =>
    searchQuery === '' || 
    question.question_text.toLowerCase().includes(searchQuery.toLowerCase()) ||
    question.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
    question.sub_category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (loading && questions.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center space-x-2 text-gray-600">
          <RefreshCw className="h-5 w-5 animate-spin" />
          <span>Loading questions...</span>
        </div>
      </div>
    );
  }

  if (error && questions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-4">
        <div className="text-red-600 flex items-center space-x-2">
          <MessageSquare className="h-5 w-5" />
          <span>Error loading questions: {error}</span>
        </div>
        <Button onClick={() => fetchQuestions()} variant="outline">
          Try Again
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Questions</h1>
          <p className="text-gray-600 mt-1">
            Browse and explore evaluation questions ({formatNumber(totalQuestions)} total)
          </p>
        </div>
        <Button onClick={() => fetchQuestions()} variant="outline" loading={loading}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Filter className="h-5 w-5" />
            <span>Filters</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <input
                type="text"
                placeholder="Search questions..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* Category Filter */}
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">All Categories</option>
              {Object.entries(categories).map(([category, count]) => (
                <option key={category} value={category}>
                  {category} ({count})
                </option>
              ))}
            </select>

            {/* Difficulty Filter */}
            <select
              value={selectedDifficulty || ''}
              onChange={(e) => setSelectedDifficulty(e.target.value ? Number(e.target.value) : null)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">All Difficulties</option>
              {[1, 2, 3, 4, 5].map((difficulty) => (
                <option key={difficulty} value={difficulty}>
                  {getDifficultyLabel(difficulty)} ({difficulty})
                </option>
              ))}
            </select>

            {/* Clear Filters */}
            <Button onClick={handleClearFilters} variant="outline">
              Clear Filters
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Questions List */}
      <div className="space-y-4">
        {filteredQuestions.length > 0 ? (
          filteredQuestions.map((question) => (
            <Card key={question.question_id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg mb-2">
                      {question.question_text}
                    </CardTitle>
                    <div className="flex items-center space-x-4 text-sm text-gray-600">
                      <span>ID: {question.question_id}</span>
                      <span>•</span>
                      <span>{question.category}</span>
                      <span>•</span>
                      <span>{question.sub_category}</span>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Badge 
                      variant="outline" 
                      className={getDifficultyColor(question.difficulty)}
                    >
                      {getDifficultyLabel(question.difficulty)}
                    </Badge>
                    <Button size="sm" variant="ghost">
                      <ExternalLink className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              
              {(question.historical_context || question.required_capabilities.length > 0) && (
                <CardContent>
                  {question.historical_context && (
                    <div className="mb-3">
                      <h4 className="text-sm font-medium text-gray-700 mb-1">Historical Context</h4>
                      <p className="text-sm text-gray-600">{question.historical_context}</p>
                    </div>
                  )}
                  
                  {question.required_capabilities.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Required Capabilities</h4>
                      <div className="flex flex-wrap gap-1">
                        {question.required_capabilities.map((capability) => (
                          <Badge key={capability} variant="outline" className="text-xs">
                            {capability}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              )}
            </Card>
          ))
        ) : (
          <Card>
            <CardContent className="text-center py-12">
              <MessageSquare className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No Questions Found</h3>
              <p className="text-gray-600">
                {searchQuery || selectedCategory || selectedDifficulty
                  ? 'Try adjusting your filters to see more questions.'
                  : 'No questions are available in the system.'}
              </p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Load More */}
      {filteredQuestions.length > 0 && filteredQuestions.length >= limit && (
        <div className="text-center">
          <Button 
            onClick={() => setLimit(limit + 20)} 
            variant="outline"
            loading={loading}
          >
            Load More Questions
          </Button>
        </div>
      )}
    </div>
  );
} 
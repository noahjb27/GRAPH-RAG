'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  BarChart3, 
  TrendingUp, 
  Clock, 
  DollarSign,
  Zap,
  Target,
  RefreshCw,
  Download,
  Filter
} from 'lucide-react';
import { 
  formatDuration, 
  formatCurrency, 
  formatNumber, 
  formatPercentage, 
  getChartColor 
} from '@/lib/utils';

// Mock data for demonstration - in a real app this would come from the API
const mockAnalytics = {
  overview: {
    totalEvaluations: 156,
    avgSuccessRate: 0.847,
    avgExecutionTime: 2.34,
    totalCost: 0.0892,
    lastUpdated: new Date().toISOString(),
  },
  pipelineComparison: [
    {
      pipeline_name: 'direct_cypher',
      success_rate: 0.92,
      avg_execution_time: 1.8,
      avg_cost: 0.0012,
      total_evaluations: 45,
    },
    {
      pipeline_name: 'vector_pipeline',
      success_rate: 0.78,
      avg_execution_time: 3.2,
      avg_cost: 0.0018,
      total_evaluations: 38,
    },
    {
      pipeline_name: 'hybrid_pipeline',
      success_rate: 0.85,
      avg_execution_time: 2.9,
      avg_cost: 0.0021,
      total_evaluations: 42,
    },
    {
      pipeline_name: 'no_rag',
      success_rate: 0.65,
      avg_execution_time: 1.2,
      avg_cost: 0.0008,
      total_evaluations: 31,
    },
  ],
  llmComparison: [
    {
      llm_provider: 'openai',
      success_rate: 0.89,
      avg_execution_time: 2.1,
      avg_cost: 0.0015,
      avg_tokens_per_second: 45.2,
      total_evaluations: 78,
    },
    {
      llm_provider: 'gemini',
      success_rate: 0.81,
      avg_execution_time: 2.8,
      avg_cost: 0.0011,
      avg_tokens_per_second: 38.7,
      total_evaluations: 56,
    },
    {
      llm_provider: 'mistral',
      success_rate: 0.83,
      avg_execution_time: 2.0,
      avg_cost: 0.0009,
      avg_tokens_per_second: 42.1,
      total_evaluations: 22,
    },
  ],
  recentEvaluations: [
    {
      id: '1',
      timestamp: new Date(Date.now() - 300000).toISOString(),
      type: 'single',
      pipeline: 'direct_cypher',
      provider: 'openai',
      success: true,
      duration: 1.8,
      cost: 0.0012,
    },
    {
      id: '2',
      timestamp: new Date(Date.now() - 600000).toISOString(),
      type: 'batch',
      pipeline: 'hybrid_pipeline',
      provider: 'gemini',
      success: true,
      duration: 14.2,
      cost: 0.0089,
    },
    {
      id: '3',
      timestamp: new Date(Date.now() - 1200000).toISOString(),
      type: 'single',
      pipeline: 'vector_pipeline',
      provider: 'openai',
      success: false,
      duration: 0.5,
      cost: 0.0003,
    },
  ],
};

export default function ResultsPage() {
  const [analytics] = useState(mockAnalytics);
  const [timeRange, setTimeRange] = useState('7d');
  const [selectedMetric, setSelectedMetric] = useState('success_rate');

  const MetricCard = ({ 
    title, 
    value, 
    icon: Icon, 
    color = 'blue',
    subtitle 
  }: {
    title: string;
    value: string;
    icon: any;
    color?: string;
    subtitle?: string;
  }) => (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-600">{title}</p>
            <p className="text-2xl font-bold">{value}</p>
            {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
          </div>
          <div className={`p-3 rounded-full bg-${color}-100`}>
            <Icon className={`h-6 w-6 text-${color}-600`} />
          </div>
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Results & Analytics</h1>
          <p className="text-gray-600 mt-1">
            Performance metrics and evaluation insights
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="24h">Last 24 hours</option>
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="all">All time</option>
          </select>
          <Button variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
          <Button variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Overview Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total Evaluations"
          value={formatNumber(analytics.overview.totalEvaluations)}
          icon={BarChart3}
          color="blue"
          subtitle="Across all pipelines"
        />
        <MetricCard
          title="Average Success Rate"
          value={formatPercentage(analytics.overview.avgSuccessRate)}
          icon={Target}
          color="green"
          subtitle="System-wide performance"
        />
        <MetricCard
          title="Average Execution Time"
          value={formatDuration(analytics.overview.avgExecutionTime)}
          icon={Clock}
          color="yellow"
          subtitle="Per evaluation"
        />
        <MetricCard
          title="Total Cost"
          value={formatCurrency(analytics.overview.totalCost)}
          icon={DollarSign}
          color="purple"
          subtitle="LLM API costs"
        />
      </div>

      {/* Pipeline Comparison */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Zap className="h-5 w-5" />
            <span>Pipeline Performance Comparison</span>
          </CardTitle>
          <CardDescription>
            Compare different Graph-RAG pipeline performance metrics
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center space-x-4 mb-4">
              <span className="text-sm font-medium text-gray-700">Metric:</span>
              <select
                value={selectedMetric}
                onChange={(e) => setSelectedMetric(e.target.value)}
                className="px-3 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="success_rate">Success Rate</option>
                <option value="avg_execution_time">Execution Time</option>
                <option value="avg_cost">Cost</option>
                <option value="total_evaluations">Total Evaluations</option>
              </select>
            </div>

            <div className="space-y-3">
              {analytics.pipelineComparison.map((pipeline, index) => {
                const value = pipeline[selectedMetric as keyof typeof pipeline];
                const maxValue = Math.max(...analytics.pipelineComparison.map(p => p[selectedMetric as keyof typeof p] as number));
                const percentage = ((value as number) / maxValue) * 100;
                
                let formattedValue: string;
                switch (selectedMetric) {
                  case 'success_rate':
                    formattedValue = formatPercentage(value as number);
                    break;
                  case 'avg_execution_time':
                    formattedValue = formatDuration(value as number);
                    break;
                  case 'avg_cost':
                    formattedValue = formatCurrency(value as number);
                    break;
                  default:
                    formattedValue = formatNumber(value as number);
                }

                return (
                  <div key={pipeline.pipeline_name} className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium capitalize">
                        {pipeline.pipeline_name.replace('_', ' ')}
                      </span>
                      <span className="text-gray-600">{formattedValue}</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="h-2 rounded-full transition-all duration-300"
                        style={{
                          width: `${percentage}%`,
                          backgroundColor: getChartColor(index),
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* LLM Provider Comparison */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <TrendingUp className="h-5 w-5" />
              <span>LLM Provider Performance</span>
            </CardTitle>
            <CardDescription>
              Performance metrics by language model provider
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {analytics.llmComparison.map((provider, index) => (
                <div key={provider.llm_provider} className="p-4 border rounded-lg">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="font-medium capitalize">{provider.llm_provider}</h4>
                    <Badge variant="outline">
                      {formatNumber(provider.total_evaluations)} evaluations
                    </Badge>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-gray-600">Success Rate:</span>
                      <span className="ml-2 font-medium">
                        {formatPercentage(provider.success_rate)}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-600">Avg Time:</span>
                      <span className="ml-2 font-medium">
                        {formatDuration(provider.avg_execution_time)}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-600">Avg Cost:</span>
                      <span className="ml-2 font-medium">
                        {formatCurrency(provider.avg_cost)}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-600">Speed:</span>
                      <span className="ml-2 font-medium">
                        {formatNumber(provider.avg_tokens_per_second, 1)} t/s
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Recent Evaluations */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Clock className="h-5 w-5" />
              <span>Recent Evaluations</span>
            </CardTitle>
            <CardDescription>
              Latest evaluation runs and their results
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {analytics.recentEvaluations.map((evaluation) => (
                <div key={evaluation.id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center space-x-3">
                    <Badge variant={evaluation.success ? 'success' : 'error'}>
                      {evaluation.success ? 'Success' : 'Failed'}
                    </Badge>
                    <div>
                      <div className="text-sm font-medium">
                        {evaluation.type === 'single' ? 'Single Question' : 'Batch Evaluation'}
                      </div>
                      <div className="text-xs text-gray-600">
                        {evaluation.pipeline} • {evaluation.provider}
                      </div>
                    </div>
                  </div>
                  <div className="text-right text-sm">
                    <div className="font-medium">{formatDuration(evaluation.duration)}</div>
                    <div className="text-gray-600">{formatCurrency(evaluation.cost)}</div>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4 text-center">
              <Button variant="outline" size="sm">
                View All Evaluations
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Performance Insights */}
      <Card>
        <CardHeader>
          <CardTitle>Performance Insights</CardTitle>
          <CardDescription>
            Key findings and recommendations based on evaluation data
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-3">
              <h4 className="font-medium text-green-600">✓ Top Performers</h4>
              <ul className="space-y-2 text-sm">
                <li>• Direct Cypher pipeline shows highest success rate (92%)</li>
                <li>• OpenAI provider delivers best overall performance</li>
                <li>• Simple questions (difficulty 1-2) have 95% success rate</li>
              </ul>
            </div>
            <div className="space-y-3">
              <h4 className="font-medium text-yellow-600">⚠ Areas for Improvement</h4>
              <ul className="space-y-2 text-sm">
                <li>• No-RAG pipeline needs optimization (65% success rate)</li>
                <li>• Vector pipeline has higher latency than expected</li>
                <li>• Complex temporal queries show inconsistent results</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
} 
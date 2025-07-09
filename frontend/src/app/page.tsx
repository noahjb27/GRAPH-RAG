'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useAPIData } from '@/lib/api-context';
import { 
  CheckCircle, 
  XCircle, 
  Clock, 
  Database, 
  Cpu, 
  MessageSquare,
  Zap,
  RefreshCw
} from 'lucide-react';
import { getStatusColor, getStatusBgColor, formatNumber } from '@/lib/utils';

export default function Dashboard() {
  const { data, loading, error, refetch } = useAPIData();
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  useEffect(() => {
    if (data.systemStatus || data.llmProviders || data.pipelines) {
      setLastUpdated(new Date());
    }
  }, [data.systemStatus, data.llmProviders, data.pipelines]);

  const handleRefresh = async () => {
    await refetch('all');
    setLastUpdated(new Date());
  };

  const isLoading = loading.systemStatus || loading.llmProviders || loading.pipelines;

  if (isLoading && !data.systemStatus && !data.llmProviders && !data.pipelines) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center space-x-2 text-gray-800">
          <RefreshCw className="h-5 w-5 animate-spin" />
          <span>Loading system status...</span>
        </div>
      </div>
    );
  }

  if (error && !data.systemStatus && !data.llmProviders && !data.pipelines) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-4">
        <div className="text-red-600 flex items-center space-x-2">
          <XCircle className="h-5 w-5" />
          <span>Error loading dashboard: {error}</span>
        </div>
        <Button onClick={handleRefresh} variant="outline">
          Try Again
        </Button>
      </div>
    );
  }

  const getOverallSystemHealth = () => {
    if (!data.systemStatus || !data.llmProviders) return 'unknown';
    
    const hasNeo4j = data.systemStatus.neo4j_connected;
    const hasLLMs = data.llmProviders.total_available > 0;
    
    if (hasNeo4j && hasLLMs) return 'healthy';
    if (hasNeo4j || hasLLMs) return 'partial';
    return 'unhealthy';
  };

  const systemHealth = getOverallSystemHealth();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-800 mt-1">
            Graph-RAG Research System Overview
          </p>
        </div>
        <div className="flex items-center space-x-4">
          {lastUpdated && (
            <div className="text-sm text-gray-800 flex items-center space-x-1">
              <Clock className="h-4 w-4" />
              <span>Last updated: {lastUpdated.toLocaleTimeString()}</span>
            </div>
          )}
          <Button 
            onClick={handleRefresh} 
            variant="outline" 
            size="sm"
            loading={isLoading}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* System Health Overview */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <div className={`h-3 w-3 rounded-full ${getStatusBgColor(systemHealth)}`} />
            <span>System Health</span>
            <Badge 
              variant={systemHealth === 'healthy' ? 'success' : systemHealth === 'partial' ? 'warning' : 'error'}
            >
              {systemHealth}
            </Badge>
          </CardTitle>
          <CardDescription>
            Overall system status and component health
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Neo4j Status */}
                         <div className="flex items-center space-x-3 p-3 rounded-lg bg-gray-50">
               <Database className={`h-5 w-5 ${getStatusColor(Boolean(data.systemStatus?.neo4j_connected ?? false))}`} />
              <div>
                <div className="font-medium">Neo4j Database</div>
                <div className="text-sm text-gray-800 flex items-center space-x-1">
                  {data.systemStatus?.neo4j_connected ? (
                    <CheckCircle className="h-4 w-4 text-green-600" />
                  ) : (
                    <XCircle className="h-4 w-4 text-red-600" />
                  )}
                  <span>{data.systemStatus?.neo4j_connected ? 'Connected' : 'Disconnected'}</span>
                </div>
              </div>
            </div>

            {/* LLM Providers */}
            <div className="flex items-center space-x-3 p-3 rounded-lg bg-gray-50">
              <Cpu className={`h-5 w-5 ${getStatusColor(Boolean(data.llmProviders && data.llmProviders.total_available > 0))}`} />
              <div>
                <div className="font-medium">LLM Providers</div>
                <div className="text-sm text-gray-800">
                  {data.llmProviders?.total_available || 0} available
                </div>
              </div>
            </div>

            {/* Questions */}
            <div className="flex items-center space-x-3 p-3 rounded-lg bg-gray-50">
              <MessageSquare className="h-5 w-5 text-blue-600" />
              <div>
                <div className="font-medium">Questions</div>
                <div className="text-sm text-gray-800">
                  {formatNumber(data.systemStatus?.total_questions || 0)} loaded
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Component Details */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* LLM Providers Details */}
        <Card>
          <CardHeader>
            <CardTitle>LLM Providers</CardTitle>
            <CardDescription>
              Available language model providers and their status
            </CardDescription>
          </CardHeader>
          <CardContent>
            {data.llmProviders?.providers.length ? (
              <div className="space-y-3">
                {data.llmProviders.providers.map((provider) => (
                  <div key={provider.name} className="flex items-center justify-between p-3 rounded-lg border">
                    <div className="flex items-center space-x-3">
                      <div className={`h-2 w-2 rounded-full ${getStatusBgColor(provider.connected)}`} />
                      <span className="font-medium capitalize">{provider.name}</span>
                    </div>
                    <Badge variant={provider.connected ? 'success' : 'error'}>
                      {provider.connected ? 'Connected' : 'Disconnected'}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center text-gray-800 py-8">
                No LLM providers configured
              </div>
            )}
          </CardContent>
        </Card>

        {/* Pipelines */}
        <Card>
          <CardHeader>
            <CardTitle>Available Pipelines</CardTitle>
            <CardDescription>
              Graph-RAG evaluation pipelines
            </CardDescription>
          </CardHeader>
          <CardContent>
            {data.pipelines?.pipelines.length ? (
              <div className="space-y-3">
                {data.pipelines.pipelines.map((pipeline) => (
                  <div key={pipeline.name} className="p-3 rounded-lg border">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium">{pipeline.display_name}</span>
                      <Zap className="h-4 w-4 text-blue-600" />
                    </div>
                    <p className="text-sm text-gray-800">{pipeline.description}</p>
                    {pipeline.required_capabilities.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {pipeline.required_capabilities.map((capability) => (
                          <Badge key={capability} variant="outline" className="text-xs">
                            {capability}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center text-gray-800 py-8">
                No pipelines available
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>
            Common tasks and operations
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Button className="h-20 flex-col space-y-2" variant="outline">
              <MessageSquare className="h-6 w-6" />
              <span>Browse Questions</span>
            </Button>
            <Button className="h-20 flex-col space-y-2" variant="outline">
              <Zap className="h-6 w-6" />
              <span>Run Evaluation</span>
            </Button>
            <Button className="h-20 flex-col space-y-2" variant="outline">
              <Database className="h-6 w-6" />
              <span>Database Info</span>
            </Button>
            <Button className="h-20 flex-col space-y-2" variant="outline">
              <Cpu className="h-6 w-6" />
              <span>System Settings</span>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

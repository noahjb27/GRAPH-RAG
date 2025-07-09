'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { apiClient, handleAPIResponse } from '@/lib/api-client';
import { DatabaseInfo, HealthStatus } from '@/types/api';
import { 
  Database, 
  RefreshCw, 
  CheckCircle, 
  XCircle,
  Info,
  Activity,
  HardDrive,
  Network
} from 'lucide-react';
import { formatNumber, getStatusColor, getStatusBgColor } from '@/lib/utils';

export default function DatabasePage() {
  const [databaseInfo, setDatabaseInfo] = useState<DatabaseInfo | null>(null);
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDatabaseInfo();
  }, []);

  const fetchDatabaseInfo = async () => {
    try {
      setLoading(true);
      setError(null);

      const [dbResponse, healthResponse] = await Promise.all([
        apiClient.getDatabaseInfo(),
        apiClient.getHealthStatus(),
      ]);

      setDatabaseInfo(handleAPIResponse(dbResponse));
      setHealthStatus(handleAPIResponse(healthResponse));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch database information');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center space-x-2 text-gray-600">
          <RefreshCw className="h-5 w-5 animate-spin" />
          <span>Loading database information...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-4">
        <div className="text-red-600 flex items-center space-x-2">
          <XCircle className="h-5 w-5" />
          <span>Error loading database information: {error}</span>
        </div>
        <Button onClick={fetchDatabaseInfo} variant="outline">
          Try Again
        </Button>
      </div>
    );
  }

  const neo4jStatus = healthStatus?.components?.neo4j || 'unknown';
  const isConnected = databaseInfo?.connection_status === 'connected';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Database</h1>
          <p className="text-gray-800 mt-1">
            Neo4j database connection and statistics
          </p>
        </div>
        <Button onClick={fetchDatabaseInfo} variant="outline" loading={loading}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Connection Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <div className={`h-3 w-3 rounded-full ${getStatusBgColor(isConnected)}`} />
            <span>Connection Status</span>
            <Badge variant={isConnected ? 'success' : 'error'}>
              {isConnected ? 'Connected' : 'Disconnected'}
            </Badge>
          </CardTitle>
          <CardDescription>
            Current status of the Neo4j database connection
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="flex items-center space-x-3 p-4 rounded-lg bg-gray-50">
              <Database className={`h-6 w-6 ${getStatusColor(isConnected)}`} />
              <div>
                <div className="font-medium">Database Status</div>
                <div className="text-sm text-gray-800 flex items-center space-x-1">
                  {isConnected ? (
                    <CheckCircle className="h-4 w-4 text-green-600" />
                  ) : (
                    <XCircle className="h-4 w-4 text-red-600" />
                  )}
                  <span>{databaseInfo?.connection_status || 'Unknown'}</span>
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-3 p-4 rounded-lg bg-gray-50">
              <Network className={`h-6 w-6 ${getStatusColor(neo4jStatus === 'healthy')}`} />
              <div>
                <div className="font-medium">Health Check</div>
                <div className="text-sm text-gray-800">
                  {typeof neo4jStatus === 'string' ? neo4jStatus : 'Checking...'}
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-3 p-4 rounded-lg bg-gray-50">
              <Activity className="h-6 w-6 text-blue-600" />
              <div>
                <div className="font-medium">Response Time</div>
                <div className="text-sm text-gray-800">
                  {isConnected ? '< 100ms' : 'N/A'}
                </div>
              </div>
            </div>
          </div>

          {databaseInfo?.error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-center space-x-2 text-red-700">
                <XCircle className="h-5 w-5" />
                <span className="font-medium">Connection Error</span>
              </div>
              <p className="text-red-600 text-sm mt-1">{databaseInfo.error}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Database Statistics */}
      {isConnected && databaseInfo?.database_info && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <HardDrive className="h-5 w-5" />
                <span>Database Statistics</span>
              </CardTitle>
              <CardDescription>
                Overview of data stored in the Neo4j database
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {Object.entries(databaseInfo.database_info).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-b-0">
                    <span className="text-sm font-medium text-gray-800 capitalize">
                      {key.replace(/_/g, ' ')}
                    </span>
                    <span className="text-sm text-gray-900">
                      {typeof value === 'number' ? formatNumber(value) : String(value)}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Info className="h-5 w-5" />
                <span>Connection Details</span>
              </CardTitle>
              <CardDescription>
                Database connection configuration and details
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between py-2 border-b border-gray-100">
                                  <span className="text-sm font-medium text-gray-800">Database Type</span>
                <span className="text-sm text-gray-900">Neo4j</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm font-medium text-gray-800">Connection Protocol</span>
                <span className="text-sm text-gray-900">Bolt</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm font-medium text-gray-800">Query Language</span>
                <span className="text-sm text-gray-900">Cypher</span>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-sm font-medium text-gray-800">Graph Database</span>
                  <Badge variant="info">Berlin Transport Network</Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Database Schema Information */}
      {isConnected && (
        <Card>
          <CardHeader>
            <CardTitle>Graph Schema</CardTitle>
            <CardDescription>
              Overview of the Berlin transport network graph structure
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <div className="text-2xl font-bold text-blue-600">Stations</div>
                <div className="text-sm text-gray-800">Transport stops and hubs</div>
              </div>
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <div className="text-2xl font-bold text-green-600">Lines</div>
                <div className="text-sm text-gray-800">Transit routes</div>
              </div>
              <div className="text-center p-4 bg-yellow-50 rounded-lg">
                <div className="text-2xl font-bold text-yellow-600">Districts</div>
                <div className="text-sm text-gray-800">Administrative areas</div>
              </div>
              <div className="text-center p-4 bg-purple-50 rounded-lg">
                <div className="text-2xl font-bold text-purple-600">Years</div>
                <div className="text-sm text-gray-800">Temporal data points</div>
              </div>
            </div>

            <div className="mt-6 p-4 bg-gray-50 rounded-lg">
              <h4 className="font-medium text-gray-900 mb-2">Key Relationships</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-medium">SERVES:</span> Lines serve stations
                </div>
                <div>
                  <span className="font-medium">LOCATED_IN:</span> Stations in districts
                </div>
                <div>
                  <span className="font-medium">IN_YEAR:</span> Temporal relationships
                </div>
                <div>
                  <span className="font-medium">CONNECTS:</span> Station connections
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
} 
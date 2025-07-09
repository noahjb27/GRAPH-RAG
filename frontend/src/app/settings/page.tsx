'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api-client';
import { 
  Settings as SettingsIcon, 
  Server, 
  Globe, 
  Save,
  RefreshCw,
  Info
} from 'lucide-react';

export default function SettingsPage() {
  const [apiUrl, setApiUrl] = useState(apiClient.getBaseURL());
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(30);
  const [notifications, setNotifications] = useState(true);

  const handleSaveSettings = () => {
    apiClient.setBaseURL(apiUrl);
    // In a real app, you'd save these settings to localStorage or a backend
    localStorage.setItem('graph-rag-settings', JSON.stringify({
      apiUrl,
      autoRefresh,
      refreshInterval,
      notifications
    }));
    alert('Settings saved successfully!');
  };

  const testConnection = async () => {
    try {
      const isConnected = await apiClient.ping();
      alert(isConnected ? 'Connection successful!' : 'Connection failed!');
    } catch (error) {
      alert('Connection failed: ' + (error instanceof Error ? error.message : 'Unknown error'));
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-600 mt-1">
          Configure your Graph-RAG Research System preferences
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* API Configuration */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Server className="h-5 w-5" />
              <span>API Configuration</span>
            </CardTitle>
            <CardDescription>
              Configure connection to the Graph-RAG backend API
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Backend API URL
              </label>
              <input
                type="url"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                placeholder="http://localhost:8000"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <p className="text-xs text-gray-500 mt-1">
                The URL where your FastAPI backend is running
              </p>
            </div>

            <div className="flex space-x-2">
              <Button onClick={testConnection} variant="outline" size="sm">
                <Globe className="h-4 w-4 mr-2" />
                Test Connection
              </Button>
              <Button onClick={handleSaveSettings} size="sm">
                <Save className="h-4 w-4 mr-2" />
                Save Settings
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* UI Preferences */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <SettingsIcon className="h-5 w-5" />
              <span>UI Preferences</span>
            </CardTitle>
            <CardDescription>
              Customize your interface and behavior settings
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">
                  Auto-refresh Data
                </label>
                <p className="text-xs text-gray-500">
                  Automatically refresh dashboard and status information
                </p>
              </div>
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded"
              />
            </div>

            {autoRefresh && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Refresh Interval (seconds)
                </label>
                <input
                  type="number"
                  value={refreshInterval}
                  onChange={(e) => setRefreshInterval(Number(e.target.value))}
                  min="10"
                  max="300"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            )}

            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">
                  Enable Notifications
                </label>
                <p className="text-xs text-gray-500">
                  Show notifications for evaluation completion and errors
                </p>
              </div>
              <input
                type="checkbox"
                checked={notifications}
                onChange={(e) => setNotifications(e.target.checked)}
                className="rounded"
              />
            </div>
          </CardContent>
        </Card>

        {/* System Information */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Info className="h-5 w-5" />
              <span>System Information</span>
            </CardTitle>
            <CardDescription>
              Information about the frontend application
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm font-medium text-gray-700">Application</span>
                <span className="text-sm text-gray-900">Graph-RAG Frontend</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm font-medium text-gray-700">Version</span>
                <Badge variant="outline">1.0.0</Badge>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm font-medium text-gray-700">Framework</span>
                <span className="text-sm text-gray-900">Next.js 15.3.5</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm font-medium text-gray-700">UI Library</span>
                <span className="text-sm text-gray-900">Tailwind CSS</span>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-sm font-medium text-gray-700">Build</span>
                <span className="text-sm text-gray-900">Development</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Environment Setup */}
        <Card>
          <CardHeader>
            <CardTitle>Environment Setup</CardTitle>
            <CardDescription>
              Instructions for configuring your development environment
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <h4 className="font-medium text-blue-900 mb-2">Frontend Configuration</h4>
              <p className="text-sm text-blue-800 mb-3">
                Create a <code className="bg-blue-100 px-1 rounded">.env.local</code> file in the frontend directory:
              </p>
              <pre className="text-xs bg-blue-100 p-3 rounded overflow-x-auto">
{`# Frontend Environment Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NODE_ENV=development`}
              </pre>
            </div>

            <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
              <h4 className="font-medium text-green-900 mb-2">Backend Setup</h4>
              <p className="text-sm text-green-800">
                Ensure your FastAPI backend is running on port 8000 with the correct CORS configuration 
                to allow requests from localhost:3000.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Advanced Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Advanced Settings</CardTitle>
          <CardDescription>
            Advanced configuration options for power users
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium text-gray-900 mb-3">Performance</h4>
              <div className="space-y-2 text-sm">
                <div className="flex items-center justify-between">
                  <span>Request Timeout:</span>
                  <span className="text-gray-600">30 seconds</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Max Retries:</span>
                  <span className="text-gray-600">3</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Cache Duration:</span>
                  <span className="text-gray-600">5 minutes</span>
                </div>
              </div>
            </div>

            <div>
              <h4 className="font-medium text-gray-900 mb-3">Security</h4>
              <div className="space-y-2 text-sm">
                <div className="flex items-center justify-between">
                  <span>HTTPS Only:</span>
                  <Badge variant="outline">Production</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span>API Key Required:</span>
                  <Badge variant="outline">Optional</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span>CORS Enabled:</span>
                  <Badge variant="success">Yes</Badge>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
} 
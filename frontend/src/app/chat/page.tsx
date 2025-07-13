'use client';

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ChatInterface } from '@/components/chat/chat-interface';
import { 
  Bot, 
  Settings, 
  Info,
  Cpu,
  Database,
  MessageSquare,
  RefreshCw
} from 'lucide-react';

export default function ChatPage() {
  const [llmProvider, setLLMProvider] = useState('openai');
  const [sessionId, setSessionId] = useState('default');
  const [showSettings, setShowSettings] = useState(false);
  const [selectedPipeline, setSelectedPipeline] = useState('auto');

  const providers = [
    { id: 'openai', name: 'OpenAI GPT-4o', available: true },
    { id: 'gemini', name: 'Google Gemini', available: true },
    { id: 'mistral', name: 'Mistral Large', available: false, note: 'VPN required' }
  ];

  const pipelines = [
    { id: 'auto', name: 'Auto-Select', description: 'Automatically choose the best pipeline' },
    { id: 'direct_cypher', name: 'Direct Cypher', description: 'Schema-aware Cypher generation' },
    { id: 'multi_query_cypher', name: 'Multi-Query Cypher', description: 'Complex analytical questions' },
    { id: 'vector', name: 'Vector-based RAG', description: 'Semantic similarity search' },
    { id: 'path_traversal', name: 'Path Traversal', description: 'Entity relationship discovery' },
    { id: 'graph_embedding', name: 'Graph Embedding', description: 'Structural similarity' },
    { id: 'hybrid', name: 'Hybrid', description: 'Multi-modal approach' }
  ];

  const handleSessionChange = (newSessionId: string) => {
    setSessionId(newSessionId);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center">
            <Bot className="h-8 w-8 mr-3 text-blue-600" />
            Graph-RAG Chatbot
          </h1>
          <p className="text-gray-600 mt-1">
            Conversational AI for historical Berlin transport networks (1946-1989)
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowSettings(!showSettings)}
          >
            <Settings className="h-4 w-4 mr-2" />
            Settings
          </Button>
        </div>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Settings className="h-5 w-5 mr-2" />
              Chat Settings
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  LLM Provider
                </label>
                <div className="flex flex-wrap gap-2">
                  {providers.map((provider) => (
                                         <Button
                       key={provider.id}
                       variant={llmProvider === provider.id ? "primary" : "outline"}
                       size="sm"
                       onClick={() => provider.available && setLLMProvider(provider.id)}
                       disabled={!provider.available}
                       className="flex items-center space-x-2"
                     >
                      <Cpu className="h-4 w-4" />
                      <span>{provider.name}</span>
                      {!provider.available && (
                        <Badge variant="outline" className="text-xs">
                          {provider.note}
                        </Badge>
                      )}
                    </Button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Session ID
                </label>
                <div className="flex items-center space-x-2">
                  <code className="px-2 py-1 bg-gray-100 rounded text-sm">
                    {sessionId}
                  </code>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSessionId(`session_${Date.now()}`)}
                  >
                    <RefreshCw className="h-4 w-4 mr-1" />
                    New Session
                  </Button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Pipeline Selection
                </label>
                <div className="flex flex-wrap gap-2">
                  {pipelines.map((pipeline) => (
                    <Button
                      key={pipeline.id}
                      variant={selectedPipeline === pipeline.id ? "primary" : "outline"}
                      size="sm"
                      onClick={() => setSelectedPipeline(pipeline.id)}
                      className="flex flex-col items-center space-y-1 h-auto py-2 px-3"
                      title={pipeline.description}
                    >
                      <span className="text-xs font-medium">{pipeline.name}</span>
                    </Button>
                  ))}
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  Auto-Select intelligently chooses the optimal pipeline based on your query type and complexity.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Chat Interface */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main Chat */}
        <div className="lg:col-span-3">
          <Card className="h-[700px]">
            <CardContent className="p-0 h-full">
              <ChatInterface
                sessionId={sessionId}
                llmProvider={llmProvider}
                onSessionChange={handleSessionChange}
              />
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Features */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center text-lg">
                <Bot className="h-5 w-5 mr-2" />
                Features
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-start space-x-2">
                  <Database className="h-4 w-4 text-blue-600 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium">Smart Query Routing</p>
                    <p className="text-xs text-gray-600">
                      Automatically detects if queries need database access
                    </p>
                  </div>
                </div>
                <div className="flex items-start space-x-2">
                  <MessageSquare className="h-4 w-4 text-green-600 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium">Route Planning</p>
                    <p className="text-xs text-gray-600">
                      Plan historical routes between Berlin locations
                    </p>
                  </div>
                </div>
                <div className="flex items-start space-x-2">
                  <RefreshCw className="h-4 w-4 text-purple-600 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium">Streaming Responses</p>
                    <p className="text-xs text-gray-600">
                      Real-time response generation with live updates
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Example Queries */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center text-lg">
                <Info className="h-5 w-5 mr-2" />
                Example Queries
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="p-2 bg-gray-50 rounded text-xs">
                  <p className="font-medium">Route Planning:</p>
                  <p className="text-gray-600">
                    "How would I have gotten from Alexanderplatz to Potsdamer Platz in 1971?"
                  </p>
                </div>
                <div className="p-2 bg-gray-50 rounded text-xs">
                  <p className="font-medium">Factual:</p>
                  <p className="text-gray-600">
                    "What was the frequency of tram Line 1 in 1964?"
                  </p>
                </div>
                <div className="p-2 bg-gray-50 rounded text-xs">
                  <p className="font-medium">Temporal:</p>
                  <p className="text-gray-600">
                    "How did the transport network change after 1961?"
                  </p>
                </div>
                <div className="p-2 bg-gray-50 rounded text-xs">
                  <p className="font-medium">Spatial:</p>
                  <p className="text-gray-600">
                    "What stations were in East Berlin in 1970?"
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Status */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center text-lg">
                <Database className="h-5 w-5 mr-2" />
                Status
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm">Database</span>
                  <Badge variant="success" className="text-xs">
                    Connected
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">LLM Provider</span>
                  <Badge variant="info" className="text-xs">
                    {llmProvider}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">Session</span>
                  <Badge variant="outline" className="text-xs">
                    Active
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">Pipeline</span>
                  <Badge variant="outline" className="text-xs">
                    {selectedPipeline === 'auto' ? 'Auto-Select' : pipelines.find(p => p.id === selectedPipeline)?.name || 'Unknown'}
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
} 
'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  Send, 
  User, 
  Bot, 
  Database, 
  MessageCircle,
  Clock,
  Loader2,
  RefreshCw,
  Trash2,
  MapPin,
  Calendar,
  Info,
  Cpu
} from 'lucide-react';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  query_type?: string;
  used_database?: boolean;
  suggested_questions?: string[];
  metadata?: Record<string, any>;
  is_streaming?: boolean;
  selected_pipeline?: string;
  pipeline_description?: string;
}

interface ChatInterfaceProps {
  sessionId?: string;
  llmProvider?: string;
  onSessionChange?: (sessionId: string) => void;
}

export function ChatInterface({ 
  sessionId = 'default', 
  llmProvider = 'openai',
  onSessionChange
}: ChatInterfaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState(sessionId);
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const sendMessage = async (messageText: string) => {
    if (!messageText.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: messageText.trim(),
      timestamp: Date.now()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setIsStreaming(true);

    // Create a temporary assistant message for streaming
    const assistantMessageId = (Date.now() + 1).toString();
    setStreamingMessageId(assistantMessageId);
    
    const assistantMessage: ChatMessage = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      is_streaming: true
    };

    setMessages(prev => [...prev, assistantMessage]);

    try {
      // Create abort controller for this request
      abortControllerRef.current = new AbortController();

      const response = await fetch('http://localhost:8000/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: messageText,
          session_id: currentSessionId,
          llm_provider: llmProvider,
          stream: true
        }),
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data.trim()) {
              try {
                const parsed = JSON.parse(data);
                
                if (parsed.type === 'end') {
                  // End of stream
                  setIsStreaming(false);
                  setStreamingMessageId(null);
                  break;
                } else if (parsed.type === 'error') {
                  // Error in stream
                  setMessages(prev => prev.map(msg => 
                    msg.id === assistantMessageId 
                      ? { ...msg, content: parsed.message, is_streaming: false }
                      : msg
                  ));
                  setIsStreaming(false);
                  setStreamingMessageId(null);
                  break;
                } else {
                  // Regular message update
                  setMessages(prev => prev.map(msg => 
                    msg.id === assistantMessageId 
                      ? {
                          ...msg,
                          content: parsed.message,
                          query_type: parsed.query_type,
                          used_database: parsed.used_database,
                          suggested_questions: parsed.suggested_questions,
                          metadata: parsed.metadata,
                          is_streaming: parsed.is_streaming,
                          selected_pipeline: parsed.metadata?.selected_pipeline,
                          pipeline_description: parsed.metadata?.pipeline_description
                        }
                      : msg
                  ));
                }
              } catch (e) {
                console.error('Error parsing streaming data:', e);
              }
            }
          }
        }
      }

    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        // Request was aborted
        setMessages(prev => prev.map(msg => 
          msg.id === assistantMessageId 
            ? { ...msg, content: 'Message cancelled', is_streaming: false }
            : msg
        ));
      } else {
        console.error('Error in chat stream:', error);
        setMessages(prev => prev.map(msg => 
          msg.id === assistantMessageId 
            ? { ...msg, content: 'Sorry, I encountered an error. Please try again.', is_streaming: false }
            : msg
        ));
      }
    } finally {
      setIsLoading(false);
      setIsStreaming(false);
      setStreamingMessageId(null);
      abortControllerRef.current = null;
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  const handleSuggestedQuestion = (question: string) => {
    sendMessage(question);
  };

  const clearChat = async () => {
    try {
      await fetch(`http://localhost:8000/chat/sessions/${currentSessionId}`, {
        method: 'DELETE',
      });
      setMessages([]);
    } catch (error) {
      console.error('Error clearing chat:', error);
    }
  };

  const newSession = () => {
    const newSessionId = `session_${Date.now()}`;
    setCurrentSessionId(newSessionId);
    setMessages([]);
    onSessionChange?.(newSessionId);
  };

  const stopStream = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  const getQueryTypeColor = (queryType?: string) => {
    switch (queryType) {
      case 'route_planning': return 'bg-blue-100 text-blue-800';
      case 'factual': return 'bg-green-100 text-green-800';
      case 'temporal': return 'bg-purple-100 text-purple-800';
      case 'spatial': return 'bg-yellow-100 text-yellow-800';
      case 'general': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getQueryTypeIcon = (queryType?: string) => {
    switch (queryType) {
      case 'route_planning': return <MapPin className="h-3 w-3" />;
      case 'factual': return <Info className="h-3 w-3" />;
      case 'temporal': return <Calendar className="h-3 w-3" />;
      case 'spatial': return <MapPin className="h-3 w-3" />;
      default: return <MessageCircle className="h-3 w-3" />;
    }
  };

  const formatTime = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  return (
    <div className="flex flex-col h-full max-h-[600px]">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center space-x-2">
          <Bot className="h-5 w-5 text-blue-600" />
          <h3 className="font-semibold">Graph-RAG Chatbot</h3>
          <Badge variant="outline" className="text-xs">
            {llmProvider}
          </Badge>
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={newSession}
            className="text-xs"
          >
            <RefreshCw className="h-3 w-3 mr-1" />
            New Chat
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={clearChat}
            className="text-xs"
          >
            <Trash2 className="h-3 w-3 mr-1" />
            Clear
          </Button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 py-8">
            <Bot className="h-12 w-12 mx-auto mb-4 text-gray-400" />
            <p className="text-lg font-medium mb-2">Welcome to Graph-RAG Chat!</p>
            <p className="text-sm">
              Ask me about historical Berlin transport networks (1946-1989)
            </p>
            <div className="mt-4 space-y-2">
              <p className="text-xs text-gray-400">Try asking:</p>
              <div className="flex flex-wrap gap-2 justify-center">
                <Button
                  variant="outline"
                  size="sm"
                  className="text-xs"
                  onClick={() => handleSuggestedQuestion("What was the frequency of tram Line 1 in 1964?")}
                >
                  Tram frequencies
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="text-xs"
                  onClick={() => handleSuggestedQuestion("How would I have gotten from Alexanderplatz to Potsdamer Platz in 1971?")}
                >
                  Route planning
                </Button>
              </div>
            </div>
          </div>
        )}

        {messages.map((message) => (
          <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-lg p-3 ${
              message.role === 'user' 
                ? 'bg-blue-300 text-white' 
                : 'bg-gray-100 text-gray-900'
            }`}>
              <div className="flex items-start space-x-2">
                {message.role === 'user' ? (
                  <User className="h-4 w-4 mt-0.5 flex-shrink-0" />
                ) : (
                  <Bot className="h-4 w-4 mt-0.5 flex-shrink-0" />
                )}
                <div className="flex-1 min-w-0">
                  <div className="whitespace-pre-wrap text-sm">
                    {message.content}
                    {message.is_streaming && (
                      <span className="inline-block w-2 h-4 bg-current ml-1 animate-pulse" />
                    )}
                  </div>
                  
                  {/* Message metadata */}
                  {message.role === 'assistant' && !message.is_streaming && (
                    <div className="mt-2 space-y-2">
                      <div className="flex items-center space-x-2 text-xs">
                        <span className="text-gray-500">
                          {formatTime(message.timestamp)}
                        </span>
                        {message.query_type && (
                                                   <Badge 
                           variant="outline" 
                           className={`text-xs ${getQueryTypeColor(message.query_type)}`}
                         >
                            {getQueryTypeIcon(message.query_type)}
                            <span className="ml-1">{message.query_type}</span>
                          </Badge>
                        )}
                                                 {message.used_database && (
                           <Badge variant="outline" className="text-xs bg-green-100 text-green-800">
                             <Database className="h-3 w-3 mr-1" />
                             Database
                           </Badge>
                         )}
                         {message.selected_pipeline && (
                           <Badge variant="outline" className="text-xs bg-blue-100 text-blue-800">
                             <Cpu className="h-3 w-3 mr-1" />
                             {message.selected_pipeline}
                           </Badge>
                         )}
                      </div>
                      
                      {/* Suggested questions */}
                      {message.suggested_questions && message.suggested_questions.length > 0 && (
                        <div className="space-y-1">
                          <p className="text-xs text-gray-600">You might also ask:</p>
                          <div className="flex flex-wrap gap-1">
                            {message.suggested_questions.map((question, index) => (
                              <Button
                                key={index}
                                variant="outline"
                                size="sm"
                                className="text-xs h-6 px-2"
                                onClick={() => handleSuggestedQuestion(question)}
                              >
                                {question}
                              </Button>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        ))}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t">
        <form onSubmit={handleSubmit} className="flex space-x-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about Berlin transport history..."
            className="flex-1 px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isLoading}
          />
          {isStreaming ? (
            <Button
              type="button"
              onClick={stopStream}
              variant="outline"
              className="px-4"
            >
              <RefreshCw className="h-4 w-4 animate-spin" />
            </Button>
          ) : (
            <Button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="px-4"
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          )}
        </form>
      </div>
    </div>
  );
} 
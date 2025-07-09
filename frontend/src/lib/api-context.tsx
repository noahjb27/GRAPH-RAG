'use client';

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { apiClient, handleAPIResponse } from './api-client';
import { 
  SystemStatus, 
  LLMProvidersResponse, 
  PipelinesResponse, 
  SingleQuestionEvaluationResponse, 
  BatchEvaluationResponse 
} from '@/types/api';

interface CachedData {
  systemStatus: SystemStatus | null;
  llmProviders: LLMProvidersResponse | null;
  pipelines: PipelinesResponse | null;
  latestEvaluationResults: SingleQuestionEvaluationResponse | BatchEvaluationResponse | null;
  lastUpdated: {
    systemStatus: number | null;
    llmProviders: number | null;
    pipelines: number | null;
    latestEvaluationResults: number | null;
  };
}

interface APIContextType {
  data: CachedData;
  loading: {
    systemStatus: boolean;
    llmProviders: boolean;
    pipelines: boolean;
  };
  error: string | null;
  refetch: (type?: 'systemStatus' | 'llmProviders' | 'pipelines' | 'all') => Promise<void>;
  updateEvaluationResults: (results: SingleQuestionEvaluationResponse | BatchEvaluationResponse) => void;
}

const APIContext = createContext<APIContextType | undefined>(undefined);

const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes in milliseconds

export function APIProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<CachedData>({
    systemStatus: null,
    llmProviders: null,
    pipelines: null,
    latestEvaluationResults: null,
    lastUpdated: {
      systemStatus: null,
      llmProviders: null,
      pipelines: null,
      latestEvaluationResults: null,
    },
  });

  const [loading, setLoading] = useState({
    systemStatus: false,
    llmProviders: false,
    pipelines: false,
  });

  const [error, setError] = useState<string | null>(null);

  const isDataStale = (lastUpdated: number | null): boolean => {
    if (!lastUpdated) return true;
    return Date.now() - lastUpdated > CACHE_DURATION;
  };

  const fetchSystemStatus = async () => {
    if (!isDataStale(data.lastUpdated.systemStatus)) return;

    setLoading(prev => ({ ...prev, systemStatus: true }));
    try {
      const response = await apiClient.getSystemStatus();
      const result = handleAPIResponse(response);
      setData(prev => ({
        ...prev,
        systemStatus: result,
        lastUpdated: { ...prev.lastUpdated, systemStatus: Date.now() },
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch system status');
    } finally {
      setLoading(prev => ({ ...prev, systemStatus: false }));
    }
  };

  const fetchLLMProviders = async () => {
    if (!isDataStale(data.lastUpdated.llmProviders)) return;

    setLoading(prev => ({ ...prev, llmProviders: true }));
    try {
      const response = await apiClient.getLLMProviders();
      const result = handleAPIResponse(response);
      setData(prev => ({
        ...prev,
        llmProviders: result,
        lastUpdated: { ...prev.lastUpdated, llmProviders: Date.now() },
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch LLM providers');
    } finally {
      setLoading(prev => ({ ...prev, llmProviders: false }));
    }
  };

  const fetchPipelines = async () => {
    if (!isDataStale(data.lastUpdated.pipelines)) return;

    setLoading(prev => ({ ...prev, pipelines: true }));
    try {
      const response = await apiClient.getPipelines();
      const result = handleAPIResponse(response);
      setData(prev => ({
        ...prev,
        pipelines: result,
        lastUpdated: { ...prev.lastUpdated, pipelines: Date.now() },
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch pipelines');
    } finally {
      setLoading(prev => ({ ...prev, pipelines: false }));
    }
  };

  const updateEvaluationResults = (results: SingleQuestionEvaluationResponse | BatchEvaluationResponse) => {
    setData(prev => ({
      ...prev,
      latestEvaluationResults: results,
      lastUpdated: { 
        ...prev.lastUpdated, 
        latestEvaluationResults: Date.now() 
      },
    }));
  };

  const refetch = async (type: 'systemStatus' | 'llmProviders' | 'pipelines' | 'all' = 'all') => {
    setError(null);
    
    // Force refresh by clearing the lastUpdated timestamp
    if (type === 'all') {
      setData(prev => ({
        ...prev,
        lastUpdated: {
          systemStatus: null,
          llmProviders: null,
          pipelines: null,
          latestEvaluationResults: null,
        },
      }));
      await Promise.all([fetchSystemStatus(), fetchLLMProviders(), fetchPipelines()]);
    } else {
      setData(prev => ({
        ...prev,
        lastUpdated: { ...prev.lastUpdated, [type]: null },
      }));
      
      switch (type) {
        case 'systemStatus':
          await fetchSystemStatus();
          break;
        case 'llmProviders':
          await fetchLLMProviders();
          break;
        case 'pipelines':
          await fetchPipelines();
          break;
      }
    }
  };

  // Initial data fetch
  useEffect(() => {
    const fetchInitialData = async () => {
      await Promise.all([fetchSystemStatus(), fetchLLMProviders(), fetchPipelines()]);
    };
    fetchInitialData();
  }, []);

  return (
    <APIContext.Provider
      value={{
        data,
        loading,
        error,
        refetch,
        updateEvaluationResults,
      }}
    >
      {children}
    </APIContext.Provider>
  );
}

export function useAPIData() {
  const context = useContext(APIContext);
  if (context === undefined) {
    throw new Error('useAPIData must be used within an APIProvider');
  }
  return context;
} 
import { type ClassValue, clsx } from 'clsx';

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

// Utility functions for formatting
export function formatDuration(seconds: number): string {
  if (seconds == null || isNaN(seconds)) {
    return 'N/A';
  }
  if (seconds < 1) {
    return `${Math.round(seconds * 1000)}ms`;
  }
  if (seconds < 60) {
    return `${seconds.toFixed(2)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
}

export function formatCurrency(amount: number): string {
  if (amount == null || isNaN(amount)) {
    return 'N/A';
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 4,
  }).format(amount);
}

export function formatNumber(num: number, decimals = 0): string {
  if (num == null || isNaN(num)) {
    return 'N/A';
  }
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(num);
}

export function formatPercentage(value: number): string {
  if (value == null || isNaN(value)) {
    return 'N/A';
  }
  return `${(value * 100).toFixed(1)}%`;
}

export function formatTokensPerSecond(tps: number): string {
  if (tps == null || isNaN(tps)) {
    return 'N/A';
  }
  if (tps < 1) {
    return `${tps.toFixed(2)} t/s`;
  }
  return `${Math.round(tps)} t/s`;
}

// Date formatting
export function formatTimestamp(timestamp: string): string {
  return new Date(timestamp).toLocaleString();
}

export function formatRelativeTime(timestamp: string): string {
  const now = new Date();
  const date = new Date(timestamp);
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (diffInSeconds < 60) {
    return 'just now';
  }
  
  const diffInMinutes = Math.floor(diffInSeconds / 60);
  if (diffInMinutes < 60) {
    return `${diffInMinutes} minute${diffInMinutes > 1 ? 's' : ''} ago`;
  }
  
  const diffInHours = Math.floor(diffInMinutes / 60);
  if (diffInHours < 24) {
    return `${diffInHours} hour${diffInHours > 1 ? 's' : ''} ago`;
  }
  
  const diffInDays = Math.floor(diffInHours / 24);
  return `${diffInDays} day${diffInDays > 1 ? 's' : ''} ago`;
}

// Color utilities for charts and status indicators
export function getStatusColor(status: boolean | string): string {
  if (typeof status === 'boolean') {
    return status ? 'text-green-600' : 'text-red-600';
  }
  
  switch (status.toLowerCase()) {
    case 'healthy':
    case 'connected':
    case 'success':
      return 'text-green-600';
    case 'unhealthy':
    case 'disconnected':
    case 'error':
    case 'failed':
      return 'text-red-600';
    case 'warning':
    case 'partial':
      return 'text-yellow-600';
    default:
      return 'text-gray-600';
  }
}

export function getStatusBgColor(status: boolean | string): string {
  if (typeof status === 'boolean') {
    return status ? 'bg-green-100' : 'bg-red-100';
  }
  
  switch (status.toLowerCase()) {
    case 'healthy':
    case 'connected':
    case 'success':
      return 'bg-green-100';
    case 'unhealthy':
    case 'disconnected':
    case 'error':
    case 'failed':
      return 'bg-red-100';
    case 'warning':
    case 'partial':
      return 'bg-yellow-100';
    default:
      return 'bg-gray-100';
  }
}

// Difficulty level utilities
export function getDifficultyColor(difficulty: number): string {
  switch (difficulty) {
    case 1:
      return 'text-green-600';
    case 2:
      return 'text-blue-600';
    case 3:
      return 'text-yellow-600';
    case 4:
      return 'text-orange-600';
    case 5:
      return 'text-red-600';
    default:
      return 'text-gray-600';
  }
}

export function getDifficultyLabel(difficulty: number): string {
  switch (difficulty) {
    case 1:
      return 'Beginner';
    case 2:
      return 'Easy';
    case 3:
      return 'Medium';
    case 4:
      return 'Hard';
    case 5:
      return 'Expert';
    default:
      return 'Unknown';
  }
}

// Chart color palette
export const chartColors = [
  '#3B82F6', // blue-500
  '#10B981', // emerald-500
  '#F59E0B', // amber-500
  '#EF4444', // red-500
  '#8B5CF6', // violet-500
  '#06B6D4', // cyan-500
  '#84CC16', // lime-500
  '#F97316', // orange-500
  '#EC4899', // pink-500
  '#6B7280', // gray-500
];

export function getChartColor(index: number): string {
  return chartColors[index % chartColors.length];
}

// Truncate text utility
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) {
    return text;
  }
  return text.slice(0, maxLength) + '...';
}

// Debounce utility
export function debounce<T extends (...args: any[]) => void>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout;
  
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
} 
'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  BarChart3,
  Database,
  Home,
  MessageSquare,
  Settings,
  Zap,
  Bot,
} from 'lucide-react';

const navigationItems = [
  {
    name: 'Dashboard',
    href: '/',
    icon: Home,
    description: 'System overview and status',
  },
  {
    name: 'Chat',
    href: '/chat',
    icon: Bot,
    description: 'Conversational AI interface',
  },
  {
    name: 'Questions',
    href: '/questions',
    icon: MessageSquare,
    description: 'Browse evaluation questions',
  },
  {
    name: 'Evaluation',
    href: '/evaluation',
    icon: Zap,
    description: 'Run evaluations and tests',
  },
  {
    name: 'Results',
    href: '/results',
    icon: BarChart3,
    description: 'View results and analytics',
  },
  {
    name: 'Database',
    href: '/database',
    icon: Database,
    description: 'Neo4j database information',
  },
  {
    name: 'Settings',
    href: '/settings',
    icon: Settings,
    description: 'Configuration and preferences',
  },
];

export function Navigation() {
  const pathname = usePathname();

  return (
    <nav className="flex h-full w-64 flex-col bg-gray-900 text-white navigation-dark">
      {/* Logo/Header */}
      <div className="flex h-16 items-center border-b border-gray-700 px-6">
        <div className="flex items-center space-x-2">
          <div className="h-8 w-8 rounded bg-blue-600 flex items-center justify-center">
            <BarChart3 className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-white">Graph-RAG</h1>
            <p className="text-xs text-gray-300">Research System</p>
          </div>
        </div>
      </div>

      {/* Navigation Links */}
      <div className="flex-1 space-y-1 px-3 py-6">
        {navigationItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'group flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-100 hover:bg-gray-700 hover:text-white'
              )}
            >
              <item.icon
                className={cn(
                  'mr-3 h-5 w-5 flex-shrink-0',
                  isActive ? 'text-white' : 'text-gray-100 group-hover:text-white'
                )}
              />
              <div className="flex-1">
                <div className={cn(
                  'font-medium',
                  isActive ? 'text-white' : 'text-gray-100 group-hover:text-white'
                )}>{item.name}</div>
                <div className="text-xs text-gray-300 group-hover:text-white">
                  {item.description}
                </div>
              </div>
            </Link>
          );
        })}
      </div>

      {/* Footer */}
      <div className="border-t border-gray-700 p-4">
                  <div className="text-xs text-gray-300">
          <div className="text-gray-300">Backend: localhost:8000</div>
          <div className="text-gray-300">Version: 1.0.0</div>
        </div>
      </div>
    </nav>
  );
} 
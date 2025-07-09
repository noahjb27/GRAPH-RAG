'use client';

import { Navigation } from './navigation';

interface MainLayoutProps {
  children: React.ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  return (
    <div className="flex h-screen bg-gray-50">
      <Navigation />
      <main className="flex-1 overflow-auto">
        <div className="container mx-auto py-6 px-6">
          {children}
        </div>
      </main>
    </div>
  );
} 
/**
 * Main application layout with sidebar navigation
 */

'use client';

import React from 'react';
import { 
  Database, 
  MessageSquare, 
  Briefcase, 
  Settings, 
  Menu,
  X,
  Github,
  Zap,
  Download
} from 'lucide-react';
import { useAppStore } from '@/lib/store';
import { cn } from '@/lib/utils';

interface LayoutProps {
  children: React.ReactNode;
}

const navItems = [
  { id: 'chat' as const, label: 'Generate', icon: MessageSquare },
  { id: 'downloads' as const, label: 'Downloads', icon: Download },
  { id: 'settings' as const, label: 'Settings', icon: Settings },
];

export default function Layout({ children }: LayoutProps) {
  const { sidebarOpen, setSidebarOpen, currentView, setCurrentView } = useAppStore();

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside
        className={cn(
          'bg-white border-r border-gray-200 transition-all duration-300 flex flex-col',
          sidebarOpen ? 'w-64' : 'w-0 lg:w-20'
        )}
      >
        {/* Logo */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-gray-200">
          {sidebarOpen && (
            <div className="flex items-center space-x-2">
              <Zap className="w-6 h-6 text-primary-600" />
              <span className="font-bold text-lg text-gray-900">DataForge</span>
            </div>
          )}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 hover:bg-gray-100 rounded-lg lg:hidden"
          >
            {sidebarOpen ? <X className="w-5 h-5 text-gray-700" /> : <Menu className="w-5 h-5 text-gray-700" />}
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentView === item.id;
            
            return (
              <button
                key={item.id}
                onClick={() => setCurrentView(item.id)}
                className={cn(
                  'w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors',
                  isActive
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-600 hover:bg-gray-100'
                )}
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                {sidebarOpen && <span className="font-medium">{item.label}</span>}
              </button>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200">
          <a
            href="https://github.com/yourusername/dataforge-studio"
            target="_blank"
            rel="noopener noreferrer"
            className={cn(
              'flex items-center space-x-3 px-4 py-3 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors',
              !sidebarOpen && 'justify-center'
            )}
          >
            <Github className="w-5 h-5 text-gray-700" />
            {sidebarOpen && <span className="text-gray-700">GitHub</span>}
          </a>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden flex flex-col" style={{ minWidth: 0, overflowX: 'hidden' }}>
        {/* Mobile Header */}
        <header className="h-16 bg-white border-b border-gray-200 flex items-center px-4 lg:hidden">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 hover:bg-gray-100 rounded-lg"
          >
            <Menu className="w-5 h-5 text-gray-700" />
          </button>
          <div className="flex-1 flex items-center justify-center">
            <Zap className="w-6 h-6 text-primary-600 mr-2" />
            <span className="font-bold text-lg text-gray-900">DataForge</span>
          </div>
        </header>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden" style={{ minWidth: 0 }}>
          {children}
        </div>
      </main>
    </div>
  );
}


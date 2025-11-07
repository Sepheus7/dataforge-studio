/**
 * Application settings view
 */

'use client';

import React, { useState, useEffect } from 'react';
import { CheckCircle2, XCircle, Loader2, AlertCircle, ExternalLink } from 'lucide-react';
import { api } from '@/services/api';

export default function SettingsView() {
  const [apiUrl, setApiUrl] = useState(
    process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  );
  const [apiKey, setApiKey] = useState(process.env.NEXT_PUBLIC_API_KEY || 'dev-key');
  const [healthStatus, setHealthStatus] = useState<any>(null);
  const [isChecking, setIsChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const checkHealth = async () => {
    setIsChecking(true);
    setError(null);
    try {
      const health = await api.healthCheck();
      setHealthStatus(health);
    } catch (err: any) {
      setError(err.message || 'Failed to connect to backend');
      setHealthStatus(null);
    } finally {
      setIsChecking(false);
    }
  };

  useEffect(() => {
    checkHealth();
  }, []);

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-sm text-gray-600 mt-1">Configure your DataForge Studio</p>
      </div>

      {/* Settings Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-3xl mx-auto space-y-6">
          {/* Backend Connection */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Backend Connection</h2>

            {/* API URL */}
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  API URL
                </label>
                <input
                  type="text"
                  value={apiUrl}
                  onChange={(e) => setApiUrl(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="http://localhost:8000"
                />
                <p className="text-xs text-gray-500 mt-1">
                  URL of your DataForge backend server
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  API Key
                </label>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="dev-key"
                />
                <p className="text-xs text-gray-500 mt-1">
                  API key for authentication (X-API-Key header)
                </p>
              </div>

              <button
                onClick={checkHealth}
                disabled={isChecking}
                className="w-full px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors flex items-center justify-center space-x-2"
              >
                {isChecking ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Checking...</span>
                  </>
                ) : (
                  <span>Test Connection</span>
                )}
              </button>

              {/* Health Status */}
              {healthStatus && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <div className="flex items-center space-x-2 text-green-800 mb-3">
                    <CheckCircle2 className="w-5 h-5" />
                    <span className="font-medium">Connected</span>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Status:</span>
                      <span className="font-medium text-gray-900">
                        {healthStatus.status}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Version:</span>
                      <span className="font-medium text-gray-900">
                        {healthStatus.version}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">LLM Provider:</span>
                      <span className="font-medium text-gray-900">
                        {healthStatus.services?.llm_provider}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Storage:</span>
                      <span className="font-medium text-gray-900">
                        {healthStatus.services?.storage}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Error */}
              {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="flex items-center space-x-2 text-red-800">
                    <XCircle className="w-5 h-5" />
                    <span className="text-sm">{error}</span>
                  </div>
                  <p className="text-xs text-red-600 mt-2">
                    Make sure the backend is running at {apiUrl}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* About */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">About</h2>
            <div className="space-y-3 text-sm">
              <p className="text-gray-600">
                DataForge Studio is an AI-powered synthetic data generation platform.
              </p>
              <div className="flex items-center justify-between py-2 border-t border-gray-200">
                <span className="text-gray-600">Frontend Version</span>
                <span className="font-medium text-gray-900">0.1.0</span>
              </div>
              <div className="flex items-center justify-between py-2 border-t border-gray-200">
                <span className="text-gray-600">Backend Version</span>
                <span className="font-medium text-gray-900">
                  {healthStatus?.version || 'N/A'}
                </span>
              </div>
              <div className="pt-2 border-t border-gray-200">
                <a
                  href="https://github.com/yourusername/dataforge-studio"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center space-x-2 text-primary-600 hover:text-primary-700"
                >
                  <span>View on GitHub</span>
                  <ExternalLink className="w-4 h-4" />
                </a>
              </div>
            </div>
          </div>

          {/* Documentation */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
            <div className="flex items-start space-x-3">
              <AlertCircle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-medium text-blue-900 mb-1">Need Help?</h3>
                <p className="text-sm text-blue-800 mb-2">
                  Check out the documentation to get started with DataForge Studio.
                </p>
                <a
                  href="https://github.com/yourusername/dataforge-studio/tree/main/docs"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center space-x-1 text-sm text-blue-600 hover:text-blue-700 font-medium"
                >
                  <span>Read Documentation</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


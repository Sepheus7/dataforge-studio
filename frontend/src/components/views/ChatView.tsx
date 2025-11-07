/**
 * Chat interface for natural language data generation
 */

'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Database, FileText, AlertCircle } from 'lucide-react';
import { api, APIError } from '@/services/api';
import { useAppStore } from '@/lib/store';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/cjs/styles/prism';
import TimeDisplay from '@/components/TimeDisplay';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  jobId?: string;
}

const examples = [
  "Generate a customer database with orders and products",
  "Create synthetic user data with 1000 records",
  "Generate an e-commerce dataset with transactions",
  "Create a healthcare patient dataset",
];

export default function ChatView() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '0',
      role: 'assistant',
      content: "👋 Hi! I'm DataForge, your AI assistant for generating synthetic data. I can help you create:\n\n- **Database schemas** with tables and relationships\n- **Synthetic datasets** in CSV/JSON format\n- **Text documents** and reports\n\nWhat would you like to generate today?",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const addJob = useAppStore((state) => state.addJob);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Call the API to generate from prompt
      const response = await api.generateFromPrompt({
        prompt: input.trim(),
      });

      // Add job to store
      addJob({
        job_id: response.job_id,
        status: response.status as any,
        created_at: new Date().toISOString(),
      });

      // Add assistant response
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `✅ Great! I've started generating your data.\n\n**Job ID:** \`${response.job_id}\`\n\nYou can monitor the progress in the **Jobs** tab. I'll analyze your request and create:\n\n1. 📊 A data schema matching your description\n2. 📁 Synthetic data files (CSV format)\n\nThis usually takes 30-60 seconds. You'll be notified when it's ready!`,
        timestamp: new Date(),
        jobId: response.job_id,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'system',
        content: `❌ **Error:** ${error instanceof APIError ? error.message : 'Failed to start generation. Make sure the backend is running.'}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleExample = (example: string) => {
    setInput(example);
  };

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <h1 className="text-2xl font-bold text-gray-900">AI Chat</h1>
        <p className="text-sm text-gray-600 mt-1">
          Describe your data needs in natural language
        </p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-3xl rounded-lg px-4 py-3 ${
                message.role === 'user'
                  ? 'bg-primary-600 text-white'
                  : message.role === 'system'
                  ? 'bg-red-50 text-red-900 border border-red-200'
                  : 'bg-white border border-gray-200 text-gray-900'
              }`}
            >
              {message.role !== 'user' ? (
                <div className="prose prose-sm max-w-none text-gray-900">
                  <ReactMarkdown
                    components={{
                      code({ node, inline, className, children, ...props }) {
                        const match = /language-(\w+)/.exec(className || '');
                        return !inline && match ? (
                          <SyntaxHighlighter
                            style={vscDarkPlus as any}
                            language={match[1]}
                            PreTag="div"
                            {...props}
                          >
                            {String(children).replace(/\n$/, '')}
                          </SyntaxHighlighter>
                        ) : (
                          <code className={className} {...props}>
                            {children}
                          </code>
                        );
                      },
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                </div>
              ) : (
                <p className="text-sm text-white">{message.content}</p>
              )}
              <p className="text-xs mt-2 opacity-70">
                <TimeDisplay timestamp={message.timestamp} />
              </p>
            </div>
          </div>
        ))}

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 rounded-lg px-4 py-3">
              <div className="flex items-center space-x-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-sm text-gray-600">Thinking...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Examples (show when no user messages yet) */}
      {messages.filter((m) => m.role === 'user').length === 0 && (
        <div className="px-6 pb-4">
          <p className="text-sm text-gray-600 mb-2">Try these examples:</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {examples.map((example, i) => (
              <button
                key={i}
                onClick={() => handleExample(example)}
                className="text-left px-4 py-2 bg-white border border-gray-200 rounded-lg hover:border-primary-300 hover:bg-primary-50 transition-colors text-sm"
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="bg-white border-t border-gray-200 px-6 py-4">
        <div className="flex space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Describe your data needs..."
            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}


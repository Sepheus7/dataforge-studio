/**
 * Enhanced Chat interface with live progress streaming
 */

'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Download, CheckCircle2, XCircle, Clock } from 'lucide-react';
import { api, APIError } from '@/services/api';
import { useAppStore, ChatMessage } from '@/lib/store';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/cjs/styles/prism';
import TimeDisplay from '@/components/TimeDisplay';

const examples = [
  "Generate a customer database with orders and products",
  "Create synthetic user data with 1000 records",
  "Generate e-commerce data with customers, orders, and products",
  "Create a healthcare patient dataset",
];

export default function ChatViewEnhanced() {
  const { 
    chatMessages, 
    addChatMessage, 
    updateChatMessage,
    addJob, 
    updateJob,
    jobs 
  } = useAppStore();
  
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [activeStreams, setActiveStreams] = useState<Record<string, EventSource>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatMessages]);

  // Cleanup streams on unmount
  useEffect(() => {
    return () => {
      Object.values(activeStreams).forEach(stream => stream.close());
    };
  }, []);

  const connectToStream = (jobId: string) => {
    if (activeStreams[jobId]) return; // Already connected

    console.log(`🔌 Connecting to SSE stream for job ${jobId}`);

    try {
      const eventSource = api.createJobStream(jobId);
      
      // Progress message ID
      const progressMsgId = `progress-${jobId}`;
      
      // Add initial progress message
      addChatMessage({
        id: progressMsgId,
        role: 'progress',
        content: '🔄 Connecting to progress stream...',
        timestamp: new Date(),
        jobId,
        progress: 0,
      });

      console.log('📝 Initial progress message added');

      // Listen for 'progress' events specifically (backend sends event="progress")
      eventSource.addEventListener('progress', (event: any) => {
        try {
          const data = JSON.parse(event.data);
          console.log('📡 SSE progress event received:', data);

          // Update progress message - always update if we have progress
          if (data.progress !== undefined) {
            const progressPercent = Math.round((data.progress || 0) * 100);
            const displayMessage = data.message || `${progressPercent}% Processing...`;
            
            console.log(`🔄 Updating progress: ${progressPercent}% - ${displayMessage}`);
            
            updateChatMessage(progressMsgId, {
              content: displayMessage,
              progress: data.progress,
            });
          }

          // Update job status in store
          if (data.status) {
            console.log(`📊 Updating job status: ${data.status}`);
            
            updateJob(jobId, {
              status: data.status,
              progress: data.progress,
              result: data.result,
              error: data.error,
            });

            // On completion, add final message
            if (data.status === 'succeeded') {
              console.log('✅ Job succeeded, adding completion message');
              addChatMessage({
                id: `complete-${jobId}-${Date.now()}`,
                role: 'assistant',
                content: `✅ **Data generation complete!**\n\n${getResultSummary(data.result)}`,
                timestamp: new Date(),
                jobId,
              });
              eventSource.close();
              delete activeStreams[jobId];
            } else if (data.status === 'failed') {
              console.log('❌ Job failed');
              addChatMessage({
                id: `error-${jobId}-${Date.now()}`,
                role: 'system',
                content: `❌ **Generation failed:** ${data.error || 'Unknown error'}`,
                timestamp: new Date(),
                jobId,
              });
              eventSource.close();
              delete activeStreams[jobId];
            }
          }
        } catch (error) {
          console.error('Error parsing SSE event:', error, event);
        }
      });

      // Also listen for generic messages (connect event)
      eventSource.onmessage = (event) => {
        console.log('📡 SSE generic event:', event.data);
      };

      eventSource.onerror = (error) => {
        console.error('SSE connection error:', error);
        eventSource.close();
        delete activeStreams[jobId];
      };

      setActiveStreams(prev => ({ ...prev, [jobId]: eventSource }));
    } catch (error) {
      console.error('Failed to create SSE connection:', error);
    }
  };

  const getResultSummary = (result: any): string => {
    if (!result) return '';
    
    if (result.tables) {
      const tables = result.tables;
      const lines = [
        `📊 Generated **${tables.length} table${tables.length > 1 ? 's' : ''}**:`,
        '',
        ...tables.map((t: any) => `- **${t.name}**: ${t.rows.toLocaleString()} rows, ${t.columns} columns`),
        '',
        `📁 **Total:** ${result.total_rows?.toLocaleString() || '?'} rows across all tables`,
      ];
      return lines.join('\n');
    }
    
    return 'Generation completed successfully!';
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    addChatMessage(userMessage);
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

      // Add initial assistant response
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: `🚀 Started job **${response.job_id}**\n\nI'll show you the progress live below...`,
        timestamp: new Date(),
        jobId: response.job_id,
      };

      addChatMessage(assistantMessage);

      // Connect to progress stream
      connectToStream(response.job_id);

    } catch (error) {
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        role: 'system',
        content: `❌ **Error:** ${error instanceof APIError ? error.message : 'Failed to start generation. Make sure the backend is running.'}`,
        timestamp: new Date(),
      };
      addChatMessage(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleExample = (example: string) => {
    setInput(example);
  };

  const handleDownload = (jobId: string, tableName: string) => {
    const url = api.getDownloadUrl(jobId, tableName, 'csv');
    window.open(url, '_blank');
  };

  const renderMessage = (message: ChatMessage) => {
    const job = message.jobId ? jobs[message.jobId] : null;
    
    return (
      <div
        key={message.id}
        className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
      >
        <div
          className={`max-w-3xl rounded-lg px-4 py-3 ${
            message.role === 'user'
              ? 'bg-blue-600 text-white'
              : message.role === 'system'
              ? 'bg-red-50 border border-red-200 text-red-900'
              : message.role === 'progress'
              ? 'bg-yellow-50 border border-yellow-200 text-gray-900'
              : 'bg-white border border-gray-200 text-gray-900'
          }`}
        >
          {/* Progress bar for progress messages */}
          {message.role === 'progress' && message.progress !== undefined && (
            <div className="mb-2">
              <div className="flex items-center justify-between text-xs mb-1">
                <span>{Math.round(message.progress * 100)}%</span>
                <span className="text-gray-500">
                  {message.progress >= 1 ? 'Complete' : 'Processing...'}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${message.progress * 100}%` }}
                />
              </div>
            </div>
          )}

          {/* Message content */}
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

          {/* Download buttons for completed jobs */}
          {job?.status === 'succeeded' && job.result?.tables && message.role === 'assistant' && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <p className="text-xs font-semibold text-gray-600 mb-2">📥 Download Data:</p>
              <div className="flex flex-wrap gap-2">
                {job.result.tables.map((table: any) => (
                  <button
                    key={table.name}
                    onClick={() => handleDownload(job.job_id, table.name)}
                    className="inline-flex items-center px-3 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700 transition-colors"
                  >
                    <Download className="w-3 h-3 mr-1" />
                    {table.name}.csv
                  </button>
                ))}
              </div>
            </div>
          )}

          <p className="text-xs mt-2 opacity-70">
            <TimeDisplay timestamp={message.timestamp} />
          </p>
        </div>
      </div>
    );
  };

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {chatMessages.map(renderMessage)}

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
      {chatMessages.filter((m) => m.role === 'user').length === 0 && !isLoading && (
        <div className="px-4 pb-4">
          <p className="text-sm text-gray-600 mb-2">Try these examples:</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {examples.map((example, idx) => (
              <button
                key={idx}
                onClick={() => handleExample(example)}
                className="text-left p-3 bg-white border border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors text-sm"
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="border-t bg-white p-4">
        <div className="max-w-4xl mx-auto flex space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Describe the data you want to generate..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
          >
            <Send className="w-4 h-4" />
            <span>Send</span>
          </button>
        </div>
      </div>
    </div>
  );
}


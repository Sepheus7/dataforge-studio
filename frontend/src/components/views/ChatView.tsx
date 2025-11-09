/**
 * Enhanced Chat interface with live agent reasoning
 * Provides real-time updates and conversation memory
 */

'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Download, Brain, CheckCircle2, AlertCircle } from 'lucide-react';
import { api, APIError } from '@/services/api';
import { useAppStore } from '@/lib/store';
import ReactMarkdown from 'react-markdown';
import TimeDisplay from '@/components/TimeDisplay';

const examples = [
  "Generate 100 customers with orders and line items",
  "Create stock market data with companies and prices",
  "Generate IoT sensor data with devices and readings",
  "Create blog posts with authors, comments, and tags",
];

interface ReasoningMessage {
  timestamp: string;
  message: string;
}

interface DataTable {
  name: string;
  rows: number;
  columns: number;
  data?: any[];
}

export default function ChatView() {
  const { chatMessages, addChatMessage, updateChatMessage, addJob, updateJob } = useAppStore();
  const [input, setInput] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState('');
  const [reasoning, setReasoning] = useState<ReasoningMessage[]>([]);
  const [generatedTables, setGeneratedTables] = useState<DataTable[]>([]);
  const [showReasoning, setShowReasoning] = useState(true);
  const [previewedTable, setPreviewedTable] = useState<string | null>(null);
  const [threadId, setThreadId] = useState<string | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const reasoningEndRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const scrollReasoningToBottom = () => {
    reasoningEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollReasoningToBottom();
  }, [reasoning]);

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  // Load chat history and restore thread_id from last job
  useEffect(() => {
    // Find the most recent job with a thread_id or create a new one
    const lastJob = Object.values(useAppStore.getState().jobs)
      .sort((a, b) => {
        const aTime = a.created_at instanceof Date 
          ? a.created_at.getTime() 
          : new Date(a.created_at || 0).getTime();
        const bTime = b.created_at instanceof Date 
          ? b.created_at.getTime() 
          : new Date(b.created_at || 0).getTime();
        return bTime - aTime;
      })[0];
    
    if (lastJob?.thread_id) {
      setThreadId(lastJob.thread_id);
    } else {
      // Generate a new thread_id for this conversation
      const newThreadId = `thread_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      setThreadId(newThreadId);
    }
  }, []);

  const addReasoningMessage = (message: string) => {
    // Deduplicate messages
    setReasoning(prev => {
      const exists = prev.some(m => m.message === message);
      if (exists) return prev;
      
      const newMsg = {
        timestamp: new Date().toLocaleTimeString('en-US', { 
          hour: '2-digit', 
          minute: '2-digit', 
          second: '2-digit',
          hour12: false 
        }),
        message
      };
      return [...prev, newMsg];
    });
  };

  const connectToStream = (jobId: string) => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      const streamUrl = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/v1/generation/${jobId}/stream?key=dev-key`;
      console.log('🔌 Connecting to SSE:', streamUrl);
      
      const eventSource = new EventSource(streamUrl);
      eventSourceRef.current = eventSource;

      eventSource.addEventListener('connect', (event: any) => {
        console.log('✅ SSE Connected');
      });

      eventSource.addEventListener('progress', (event: any) => {
        try {
          const data = JSON.parse(event.data);
          console.log('📡 Progress event:', data);

          // Update progress
          if (data.progress !== undefined) {
            const progressPercent = Math.round(data.progress * 100);
            setProgress(progressPercent);
            
            // Update chat message progress
            const lastAssistantMsg = chatMessages
              .filter(m => m.role === 'assistant' && m.jobId === currentJobId)
              .pop();
            if (lastAssistantMsg) {
              updateChatMessage(lastAssistantMsg.id, {
                progress: progressPercent,
                content: data.message || lastAssistantMsg.content,
              });
            }
          }

          // Update message
          if (data.message) {
            setProgressMessage(data.message);
            addReasoningMessage(data.message);
            
            // Update chat message content
            const lastAssistantMsg = chatMessages
              .filter(m => m.role === 'assistant' && m.jobId === currentJobId)
              .pop();
            if (lastAssistantMsg) {
              updateChatMessage(lastAssistantMsg.id, {
                content: data.message,
              });
            }
          }

          // Handle completion
          if (data.status === 'succeeded') {
            console.log('✅ Job succeeded');
            setIsGenerating(false);
            setProgress(100);
            
            // Load generated tables
            if (data.result?.tables) {
              setGeneratedTables(data.result.tables.map((t: any) => ({
                name: t.name,
                rows: t.rows || 0,
                columns: t.columns || 0,
              })));
            }
            
            // Update job in store with result
            if (currentJobId) {
              updateJob(currentJobId, {
                status: 'succeeded',
                result: data.result,
                completed_at: new Date().toISOString(),
              });
            }
            
            // Update assistant message with completion
            const lastAssistantMsg = chatMessages
              .filter(m => m.role === 'assistant' && m.jobId === currentJobId)
              .pop();
            if (lastAssistantMsg) {
              updateChatMessage(lastAssistantMsg.id, {
                content: `✅ Generated ${data.result?.tables?.length || 0} table(s) with ${data.result?.total_rows || 0} total rows`,
                progress: 100,
              });
            }
            
            eventSource.close();
          } else if (data.status === 'failed') {
            console.error('❌ Job failed:', data.error);
            setIsGenerating(false);
            setProgressMessage(`Error: ${data.error || 'Unknown error'}`);
            
            // Update assistant message with error
            const lastAssistantMsg = chatMessages
              .filter(m => m.role === 'assistant' && m.jobId === currentJobId)
              .pop();
            if (lastAssistantMsg) {
              updateChatMessage(lastAssistantMsg.id, {
                content: `❌ Error: ${data.error || 'Unknown error'}`,
              });
            }
            
            eventSource.close();
          }
        } catch (error) {
          console.error('Error parsing SSE event:', error);
        }
      });

      eventSource.onerror = (error) => {
        console.error('❌ SSE error:', error);
        eventSource.close();
      };

    } catch (error) {
      console.error('Failed to create SSE connection:', error);
    }
  };

  const pollJobStatus = async (jobId: string) => {
    // Fallback polling if SSE fails
    const maxAttempts = 60; // 5 minutes (5s intervals)
    let attempts = 0;

    const poll = async () => {
      try {
        const status = await api.getJobStatus(jobId);
        console.log('📡 Polling job status:', status);

        // Update progress
        if (status.progress !== undefined) {
          setProgress(Math.round(status.progress * 100));
        }

        // Update message
        if (status.message) {
          setProgressMessage(status.message);
        }

        // Check if complete
        if (status.status === 'succeeded') {
          console.log('✅ Job completed (via polling)');
          setIsGenerating(false);
          setProgress(100);

          // Load tables
          if (status.result?.tables) {
            setGeneratedTables(status.result.tables.map((t: any) => ({
              name: t.name,
              rows: t.rows || 0,
              columns: t.columns || 0,
            })));
          }
          
          // Update job in store
          if (jobId) {
            updateJob(jobId, {
              status: 'succeeded',
              result: status.result,
              completed_at: status.completed_at,
            });
          }
          return;
        } else if (status.status === 'failed') {
          console.error('❌ Job failed (via polling):', status.error);
          setIsGenerating(false);
          setProgressMessage(`Error: ${status.error || 'Unknown error'}`);
          return;
        }

        // Continue polling if still running
        if (status.status === 'running' && attempts < maxAttempts) {
          attempts++;
          setTimeout(poll, 5000); // Poll every 5 seconds
        }
      } catch (error) {
        console.error('❌ Polling error:', error);
        if (attempts < maxAttempts) {
          attempts++;
          setTimeout(poll, 5000);
        } else {
          setIsGenerating(false);
          setProgressMessage('Failed to fetch job status');
        }
      }
    };

    // Start polling after a delay (give SSE a chance first)
    setTimeout(poll, 10000); // Start polling after 10 seconds
  };

  const shouldGenerate = (prompt: string): boolean => {
    // Check if user explicitly wants to generate
    const generateKeywords = [
      'generate', 'create', 'make', 'build', 'proceed', 'go ahead', 
      'yes', 'sure', 'okay', 'ok', 'do it', 'start', 'begin'
    ];
    const promptLower = prompt.toLowerCase();
    return generateKeywords.some(keyword => promptLower.includes(keyword));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isGenerating) return;

    const prompt = input.trim();
    setInput('');

    // Add user message to chat
    const userMessageId = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    addChatMessage({
      id: userMessageId,
      role: 'user',
      content: prompt,
      timestamp: new Date(),
    });

    try {
      // Ensure we have a thread_id
      if (!threadId) {
        const newThreadId = `thread_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        setThreadId(newThreadId);
      }

      // Check if user wants to generate or if we should just chat
      const wantsToGenerate = shouldGenerate(prompt);
      
      if (wantsToGenerate) {
        // User explicitly wants to generate - start generation
        setIsGenerating(true);
        setProgress(0);
        setProgressMessage('Starting...');
        setReasoning([]);
        setGeneratedTables([]);

        const response = await api.generateFromPrompt({ 
          prompt,
          thread_id: threadId || undefined,
        });
        const jobId = response.job_id;
        setCurrentJobId(jobId);
        
        // Add job to store
        addJob({
          job_id: jobId,
          status: response.status as any,
          created_at: new Date().toISOString(),
          thread_id: threadId || undefined,
        });
        
        // Add assistant message placeholder
        const assistantMessageId = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        addChatMessage({
          id: assistantMessageId,
          role: 'assistant',
          content: '🔄 Generating data...',
          timestamp: new Date(),
          jobId,
          progress: 0,
        });
        
        console.log('✅ Job created:', jobId);
        
        // Connect to stream
        connectToStream(jobId);
        
        // Start polling as fallback
        pollJobStatus(jobId);
      } else {
        // Just have a conversation - no generation
        setIsGenerating(true); // Show loading state
        
        const chatResponse = await api.chat({
          prompt,
          thread_id: threadId || undefined,
        });
        
        // Update thread_id if returned
        if (chatResponse.thread_id) {
          setThreadId(chatResponse.thread_id);
        }
        
        // Add assistant response
        const assistantMessageId = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        addChatMessage({
          id: assistantMessageId,
          role: 'assistant',
          content: chatResponse.response,
          timestamp: new Date(),
        });
        
        setIsGenerating(false);
      }
      
    } catch (error) {
      console.error('❌ Error:', error);
      setIsGenerating(false);
      
      // Add error message
      const errorMessageId = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      addChatMessage({
        id: errorMessageId,
        role: 'assistant',
        content: `❌ Error: ${error instanceof APIError ? error.message : 'Something went wrong'}`,
        timestamp: new Date(),
      });
    }
  };

  const handleDownload = async (tableName: string) => {
    if (!currentJobId) return;
    
    try {
      const downloadUrl = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/v1/generation/${currentJobId}/download?table_name=${tableName}&format=csv`;
      
      // Fetch with API key header
      const response = await fetch(downloadUrl, {
        headers: {
          'X-API-Key': 'dev-key'
        }
      });
      
      if (!response.ok) {
        throw new Error('Download failed');
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${tableName}_${currentJobId}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Download error:', error);
    }
  };

  const handlePreview = async (tableName: string) => {
    if (!currentJobId) return;
    
    // Toggle preview - if already previewed, hide it
    if (previewedTable === tableName) {
      setPreviewedTable(null);
      // Clear preview data
      setGeneratedTables(prev => prev.map(t => 
        t.name === tableName ? { ...t, data: undefined } : t
      ));
      return;
    }
    
    // Show preview for this table
    setPreviewedTable(tableName);
    
    try {
      const downloadUrl = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/v1/generation/${currentJobId}/download?table_name=${tableName}&format=csv`;
      
      const response = await fetch(downloadUrl, {
        headers: {
          'X-API-Key': 'dev-key'
        }
      });
      
      if (!response.ok) {
        // Try to get error message from response
        let errorMessage = 'Preview failed';
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch {
          errorMessage = `Preview failed: ${response.status} ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }
      
      const csvText = await response.text();
      
      if (!csvText || csvText.trim().length === 0) {
        throw new Error('Preview failed: Empty response from server');
      }
      
      const lines = csvText.split('\n').filter(l => l.trim());
      
      if (lines.length === 0) {
        throw new Error('Preview failed: No data in CSV file');
      }
      
      const headers = lines[0].split(',').map(h => h.trim());
      const rows = lines.slice(1, 11).map(line => {
        // Handle CSV parsing more carefully (quoted values, commas in values)
        const values: string[] = [];
        let current = '';
        let inQuotes = false;
        
        for (let i = 0; i < line.length; i++) {
          const char = line[i];
          if (char === '"') {
            inQuotes = !inQuotes;
          } else if (char === ',' && !inQuotes) {
            values.push(current.trim());
            current = '';
          } else {
            current += char;
          }
        }
        values.push(current.trim()); // Add last value
        return values;
      });
      
      // Update table with preview data
      setGeneratedTables(prev => prev.map(t => 
        t.name === tableName 
          ? { ...t, data: rows.map(row => Object.fromEntries(headers.map((h, i) => [h, row[i] || '']))) }
          : t
      ));
    } catch (error) {
      console.error('Preview error:', error);
      // Show error to user
      const errorMessage = error instanceof Error ? error.message : 'Preview failed';
      setProgressMessage(`Preview error: ${errorMessage}`);
      // You could also show a toast notification here
    }
  };

  return (
    <div className="flex h-full bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900" style={{ overflowX: 'hidden', width: '100%', maxWidth: '100%' }}>
      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-gray-800/50 backdrop-blur-sm border-b border-gray-700 px-6 py-4">
          <h1 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-500">
            🔥 DataForge Studio
          </h1>
          <p className="text-gray-400 text-sm mt-1">Generate synthetic data with AI reasoning</p>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-hidden flex" style={{ minWidth: 0, width: '100%' }}>
          {/* Chat Area */}
          <div className="flex-1 flex flex-col" style={{ minWidth: 0, maxWidth: '100%', overflow: 'hidden', width: 0 }}>
            {/* Messages */}
            <div className="flex-1 overflow-y-auto overflow-x-hidden px-6 py-4" style={{ minWidth: 0, maxWidth: '100%', backgroundColor: 'rgba(17, 24, 39, 0.5)' }}>
              {/* Chat History */}
              {chatMessages.length > 0 && (
                <div className="space-y-4 mb-6">
                  {chatMessages.map((msg) => (
                    <div
                      key={msg.id}
                      className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-3xl rounded-lg p-4 shadow-lg ${
                          msg.role === 'user'
                            ? 'bg-blue-600'
                            : msg.role === 'assistant'
                            ? 'bg-gray-800/50 border border-gray-700'
                            : 'bg-gray-700'
                        }`}
                      >
                        <div className="flex items-start space-x-3">
                          {msg.role === 'user' && <span className="text-xl">👤</span>}
                          {msg.role === 'assistant' && <span className="text-xl">🤖</span>}
                          <div className="flex-1">
                            <div className="text-sm text-white [&_p]:text-white [&_strong]:text-white [&_em]:text-white [&_code]:text-white [&_pre]:text-white [&_ul]:text-white [&_ol]:text-white [&_li]:text-white [&_h1]:text-white [&_h2]:text-white [&_h3]:text-white [&_h4]:text-white [&_h5]:text-white [&_h6]:text-white">
                              <ReactMarkdown className="prose prose-invert max-w-none [&_*]:text-white [&_*]:text-sm">
                                {msg.content}
                              </ReactMarkdown>
                            </div>
                            {msg.progress !== undefined && msg.progress < 100 && (
                              <div className="mt-3">
                                <div className="w-full bg-gray-700 rounded-full h-2.5">
                                  <div
                                    className="bg-blue-400 h-2.5 rounded-full transition-all"
                                    style={{ width: `${msg.progress}%` }}
                                  />
                                </div>
                              </div>
                            )}
                            <p className="text-xs text-gray-300 mt-2">
                              <TimeDisplay timestamp={msg.timestamp} />
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {!isGenerating && generatedTables.length === 0 && chatMessages.filter(m => m.role !== 'assistant' || m.content !== "👋 Hi! I'm DataForge, your AI assistant for generating synthetic data. I can help you create:\n\n- **Database schemas** with tables and relationships\n- **Synthetic datasets** in CSV/JSON format\n- **Text documents** and reports\n\nWhat would you like to generate today?").length === 0 && (
                <div className="h-full flex flex-col items-center justify-center text-gray-400">
                  <Brain className="w-16 h-16 mb-4 text-blue-500 animate-pulse" />
                  <h2 className="text-xl font-semibold mb-4">Ready to generate synthetic data</h2>
                  <p className="text-sm mb-6">Try one of these examples:</p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-3xl">
                    {examples.map((example, idx) => (
                      <button
                        key={idx}
                        onClick={() => setInput(example)}
                        className="px-4 py-3 bg-gray-800/50 hover:bg-gray-700/50 border border-gray-700 rounded-lg text-left text-sm transition-all hover:border-blue-500"
                      >
                        {example}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Generation Progress */}
              {isGenerating && (
                <div className="space-y-4 mb-6">
                  <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-lg p-6">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center space-x-3">
                        <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
                        <span className="font-semibold text-white">Generating...</span>
                      </div>
                      <span className="text-2xl font-bold text-blue-400">{progress}%</span>
                    </div>
                    
                    {/* Progress Bar */}
                    <div className="w-full bg-gray-700 rounded-full h-3 mb-3 overflow-hidden">
                      <div 
                        className="bg-gradient-to-r from-blue-500 to-purple-500 h-full transition-all duration-300 ease-out"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                    
                    <p className="text-sm text-gray-400">{progressMessage}</p>
                  </div>
                </div>
              )}

              {/* Generated Tables */}
              {generatedTables.length > 0 && (
                <div className="space-y-4">
                  <div className="flex items-center space-x-2 mb-4">
                    <CheckCircle2 className="w-6 h-6 text-green-500" />
                    <h3 className="text-xl font-bold text-white">Generation Complete!</h3>
                  </div>
                  
                  {generatedTables.map((table, idx) => (
                    <div key={idx} className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-lg p-6" style={{ width: '100%', maxWidth: '100%', minWidth: 0, overflow: 'hidden' }}>
                      <div className="flex items-center justify-between mb-4">
                        <div>
                          <h4 className="text-lg font-semibold text-white">{table.name}</h4>
                          <p className="text-sm text-gray-400">
                            {table.rows.toLocaleString()} rows × {table.columns} columns
                          </p>
                        </div>
                        <div className="flex space-x-2">
                          <button
                            onClick={() => handlePreview(table.name)}
                            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                              previewedTable === table.name
                                ? 'bg-blue-700 text-white border-2 border-blue-400'
                                : 'bg-blue-600 hover:bg-blue-700 text-white'
                            }`}
                          >
                            {previewedTable === table.name ? 'Hide Preview' : 'Preview'}
                          </button>
                          <button
                            onClick={() => handleDownload(table.name)}
                            className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center space-x-2"
                          >
                            <Download className="w-4 h-4" />
                            <span>Download CSV</span>
                          </button>
                        </div>
                      </div>
                      
                      {/* Preview Table */}
                      {previewedTable === table.name && table.data && table.data.length > 0 && (
                        <div className="mt-4" style={{ width: '100%', maxWidth: '100%', overflow: 'hidden' }}>
                          <div 
                            className="overflow-x-auto overflow-y-visible"
                            style={{ 
                              width: '100%',
                              maxWidth: '100%',
                              scrollbarWidth: 'thin',
                              scrollbarColor: '#4B5563 #1F2937',
                              WebkitOverflowScrolling: 'touch'
                            }}
                          >
                            <table className="text-sm border-collapse" style={{ minWidth: 'max-content', width: 'auto', display: 'table' }}>
                              <thead>
                                <tr className="border-b border-gray-700">
                                  {Object.keys(table.data[0]).map((header, i) => (
                                    <th key={i} className="px-3 py-2 text-left text-gray-400 font-medium whitespace-nowrap bg-gray-800/50">
                                      {header}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {table.data.slice(0, 10).map((row, i) => (
                                  <tr key={i} className="border-b border-gray-800 hover:bg-gray-800/30">
                                    {Object.values(row).map((cell: any, j) => (
                                      <td key={j} className="px-3 py-2 text-gray-300 whitespace-nowrap">
                                        {String(cell).length > 50 ? String(cell).substring(0, 50) + '...' : String(cell)}
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                          <p className="text-xs text-gray-500 mt-2">Showing first 10 rows • Scroll horizontally to see all columns</p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="border-t border-gray-700 bg-gray-800/50 backdrop-blur-sm p-4">
              <form onSubmit={handleSubmit} className="flex space-x-3">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Describe the data you want to generate..."
                  disabled={isGenerating}
                  className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 disabled:opacity-50"
                />
                <button
                  type="submit"
                  disabled={isGenerating || !input.trim()}
                  className="px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white rounded-lg font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                >
                  {isGenerating ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      <span>Generating...</span>
                    </>
                  ) : (
                    <>
                      <Send className="w-5 h-5" />
                      <span>Generate</span>
                    </>
                  )}
                </button>
              </form>
            </div>
          </div>

          {/* Reasoning Panel */}
          {(isGenerating || reasoning.length > 0) && (
            <div className="w-96 border-l border-gray-700 bg-gray-800/30 backdrop-blur-sm flex flex-col flex-shrink-0">
              <div className="px-4 py-3 border-b border-gray-700 flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Brain className="w-5 h-5 text-purple-400" />
                  <h3 className="font-semibold text-white">Agent Reasoning</h3>
                </div>
                <button
                  onClick={() => setShowReasoning(!showReasoning)}
                  className="text-gray-400 hover:text-white text-sm"
                >
                  {showReasoning ? 'Hide' : 'Show'}
                </button>
              </div>
              
              {showReasoning && (
                <div className="flex-1 overflow-y-auto p-4 space-y-2">
                  {reasoning.map((r, idx) => (
                    <div key={idx} className="text-sm">
                      <span className="text-gray-500 font-mono text-xs">[{r.timestamp}]</span>
                      <p className="text-gray-300 mt-1">{r.message}</p>
                    </div>
                  ))}
                  {reasoning.length === 0 && (
                    <p className="text-gray-500 text-sm italic">Waiting for agent updates...</p>
                  )}
                  <div ref={reasoningEndRef} />
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

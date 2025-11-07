/**
 * Downloads view - Browse and download all generated files
 */

'use client';

import React, { useState, useEffect } from 'react';
import {
  Download,
  FileText,
  Database,
  Calendar,
  Trash2,
  Search,
  Filter,
  FileSpreadsheet,
  RefreshCw,
} from 'lucide-react';
import { useAppStore } from '@/lib/store';
import { api } from '@/services/api';
import { formatDate, formatNumber, getStatusColor } from '@/lib/utils';
import ClientOnly from '@/components/ClientOnly';

type FileFilter = 'all' | 'datasets' | 'documents';

export default function DownloadsView() {
  const { jobs, updateJob } = useAppStore();
  const [filter, setFilter] = useState<FileFilter>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  // Get all completed jobs with results
  const completedJobs = Object.values(jobs).filter(
    (job) => job.status === 'succeeded' && job.result
  );

  // Filter jobs based on search and filter
  const filteredJobs = completedJobs.filter((job) => {
    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      const matchesId = job.job_id.toLowerCase().includes(query);
      const matchesTables = job.result?.tables?.some((t: any) =>
        t.name.toLowerCase().includes(query)
      );
      if (!matchesId && !matchesTables) return false;
    }

    // Type filter
    if (filter === 'datasets' && !job.result?.tables) return false;
    if (filter === 'documents' && job.result?.tables) return false;

    return true;
  });

  const handleDownload = (jobId: string, tableName: string, format: string = 'csv') => {
    const url = api.getDownloadUrl(jobId, tableName, format);
    window.open(url, '_blank');
  };

  const handleDownloadAll = async (jobId: string) => {
    const job = jobs[jobId];
    if (job?.result?.tables) {
      job.result.tables.forEach((table: any) => {
        setTimeout(() => {
          handleDownload(jobId, table.name, 'csv');
        }, 100);
      });
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await Promise.all(
        completedJobs.map(async (job) => {
          try {
            const status = await api.getJobStatus(job.job_id);
            updateJob(job.job_id, status);
          } catch (error) {
            console.error(`Failed to refresh job ${job.job_id}:`, error);
          }
        })
      );
    } finally {
      setRefreshing(false);
    }
  };

  // Calculate stats
  const totalFiles = completedJobs.reduce((sum, job) => {
    return sum + (job.result?.tables?.length || 0);
  }, 0);

  const totalRows = completedJobs.reduce((sum, job) => {
    return sum + (job.result?.total_rows || 0);
  }, 0);

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Downloads</h1>
            <p className="text-sm text-gray-600 mt-1">
              Access and download your generated files
            </p>
          </div>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center space-x-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors text-gray-700"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div className="bg-blue-50 rounded-lg p-4">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Database className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-blue-600 font-medium">Total Jobs</p>
                <p className="text-2xl font-bold text-blue-900">{completedJobs.length}</p>
              </div>
            </div>
          </div>
          <div className="bg-green-50 rounded-lg p-4">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-green-100 rounded-lg">
                <FileSpreadsheet className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-green-600 font-medium">Total Files</p>
                <p className="text-2xl font-bold text-green-900">{totalFiles}</p>
              </div>
            </div>
          </div>
          <div className="bg-purple-50 rounded-lg p-4">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-purple-100 rounded-lg">
                <FileText className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-purple-600 font-medium">Total Rows</p>
                <p className="text-2xl font-bold text-purple-900">
                  {formatNumber(totalRows)}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Search and Filter */}
        <div className="flex flex-col md:flex-row gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by job ID or table name..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-gray-900"
            />
          </div>
          <div className="flex items-center space-x-2">
            <Filter className="w-5 h-5 text-gray-600" />
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value as FileFilter)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-gray-900"
            >
              <option value="all">All Files</option>
              <option value="datasets">Datasets Only</option>
              <option value="documents">Documents Only</option>
            </select>
          </div>
        </div>
      </div>

      {/* Files List */}
      <div className="flex-1 overflow-y-auto p-6">
        {filteredJobs.length === 0 ? (
          <div className="text-center py-12">
            <FileSpreadsheet className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              {completedJobs.length === 0 ? 'No files yet' : 'No files match your search'}
            </h3>
            <p className="text-gray-600">
              {completedJobs.length === 0
                ? 'Generate some data to see your files here'
                : 'Try adjusting your search or filters'}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {filteredJobs.map((job) => (
              <div
                key={job.job_id}
                className="bg-white rounded-lg border border-gray-200 p-6 hover:border-primary-300 transition-colors"
              >
                {/* Job Header */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <Database className="w-5 h-5 text-primary-600" />
                      <span className="font-medium text-gray-900">
                        Job #{job.job_id.slice(0, 8)}
                      </span>
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(
                          job.status
                        )}`}
                      >
                        {job.status.toUpperCase()}
                      </span>
                    </div>
                    <ClientOnly>
                      <div className="flex items-center space-x-4 text-sm text-gray-600">
                        <div className="flex items-center space-x-1">
                          <Calendar className="w-4 h-4" />
                          <span>Created {formatDate(job.created_at)}</span>
                        </div>
                        {job.result?.tables && (
                          <>
                            <span>•</span>
                            <span>{job.result.tables.length} tables</span>
                            <span>•</span>
                            <span>{formatNumber(job.result.total_rows)} rows</span>
                          </>
                        )}
                      </div>
                    </ClientOnly>
                  </div>

                  {/* Download All Button */}
                  {job.result?.tables && job.result.tables.length > 1 && (
                    <button
                      onClick={() => handleDownloadAll(job.job_id)}
                      className="flex items-center space-x-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
                    >
                      <Download className="w-4 h-4" />
                      <span>Download All</span>
                    </button>
                  )}
                </div>

                {/* Files List */}
                {job.result?.tables && job.result.tables.length > 0 && (
                  <div className="space-y-2">
                    {job.result.tables.map((table: any, idx: number) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                      >
                        <div className="flex items-center space-x-3 flex-1">
                          <FileSpreadsheet className="w-5 h-5 text-gray-600" />
                          <div>
                            <p className="font-medium text-gray-900">{table.name}.csv</p>
                            <p className="text-sm text-gray-600">
                              {formatNumber(table.rows)} rows × {table.columns} columns
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <button
                            onClick={() => handleDownload(job.job_id, table.name, 'csv')}
                            className="flex items-center space-x-2 px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                          >
                            <Download className="w-4 h-4" />
                            <span>Download CSV</span>
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}


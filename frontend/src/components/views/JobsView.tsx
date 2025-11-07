/**
 * Jobs monitoring dashboard with real-time updates
 */

'use client';

import React, { useEffect, useState } from 'react';
import {
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  Download,
  Trash2,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';
import { api } from '@/services/api';
import { useAppStore } from '@/lib/store';
import { formatDate, getDuration, formatDuration, getStatusColor, formatNumber } from '@/lib/utils';
import JobStreamMonitor from '@/components/JobStreamMonitor';
import ClientOnly from '@/components/ClientOnly';

export default function JobsView() {
  const { jobs, updateJob, removeJob } = useAppStore();
  const [refreshing, setRefreshing] = useState(false);

  const jobList = Object.values(jobs).sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      // Refresh all non-terminal jobs
      const activeJobs = jobList.filter(
        (job) => job.status === 'queued' || job.status === 'running'
      );

      await Promise.all(
        activeJobs.map(async (job) => {
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

  const handleDelete = async (jobId: string) => {
    if (confirm('Are you sure you want to delete this job?')) {
      try {
        await api.cancelJob(jobId);
        removeJob(jobId);
      } catch (error) {
        console.error('Failed to delete job:', error);
      }
    }
  };

  const handleDownload = (jobId: string, tableName: string = 'data') => {
    const url = api.getDownloadUrl(jobId, tableName, 'csv');
    window.open(url, '_blank');
  };

  useEffect(() => {
    // Auto-refresh active jobs every 5 seconds
    const interval = setInterval(() => {
      const activeJobs = jobList.filter(
        (job) => job.status === 'queued' || job.status === 'running'
      );
      if (activeJobs.length > 0) {
        handleRefresh();
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [jobList]);

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Jobs</h1>
          <p className="text-sm text-gray-600 mt-1">
            Monitor your data generation jobs
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center space-x-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Jobs List */}
      <div className="flex-1 overflow-y-auto p-6">
        {jobList.length === 0 ? (
          <div className="text-center py-12">
            <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No jobs yet</h3>
            <p className="text-gray-600">
              Start by creating a data generation job in the Chat view
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {jobList.map((job) => (
              <div
                key={job.job_id}
                className="bg-white rounded-lg border border-gray-200 p-6"
              >
                {/* Job Header */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(
                          job.status
                        )}`}
                      >
                        {job.status === 'running' && (
                          <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                        )}
                        {job.status === 'succeeded' && (
                          <CheckCircle2 className="w-3 h-3 mr-1" />
                        )}
                        {job.status === 'failed' && <XCircle className="w-3 h-3 mr-1" />}
                        {job.status === 'queued' && <Clock className="w-3 h-3 mr-1" />}
                        {job.status.toUpperCase()}
                      </span>
                      <span className="text-sm text-gray-500 font-mono">
                        {job.job_id.slice(0, 8)}...
                      </span>
                    </div>
                    <ClientOnly>
                      <p className="text-sm text-gray-600">
                        Created {formatDate(job.created_at)}
                      </p>
                    </ClientOnly>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center space-x-2">
                    {job.status === 'succeeded' && job.result && (
                      <button
                        onClick={() => handleDownload(job.job_id)}
                        className="p-2 text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
                        title="Download CSV"
                      >
                        <Download className="w-5 h-5" />
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(job.job_id)}
                      className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      title="Delete job"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>
                </div>

                {/* Job Details */}
                {job.status === 'succeeded' && job.result && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h4 className="font-medium text-gray-900 mb-2">Results</h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div>
                        <p className="text-sm text-gray-600">Tables</p>
                        <p className="text-lg font-semibold text-gray-900">
                          {job.result.tables?.length || 0}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600">Total Rows</p>
                        <p className="text-lg font-semibold text-gray-900">
                          {formatNumber(job.result.total_rows || 0)}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600">Duration</p>
                        <p className="text-lg font-semibold text-gray-900">
                          {job.completed_at &&
                            formatDuration(getDuration(job.started_at || job.created_at, job.completed_at))}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600">Status</p>
                        <p className="text-lg font-semibold text-green-600">Complete</p>
                      </div>
                    </div>

                    {/* Table Details */}
                    {job.result.tables && job.result.tables.length > 0 && (
                      <div className="mt-4">
                        <h5 className="text-sm font-medium text-gray-700 mb-2">Tables:</h5>
                        <div className="space-y-2">
                          {job.result.tables.map((table: any, idx: number) => (
                            <div
                              key={idx}
                              className="flex items-center justify-between bg-white rounded p-2"
                            >
                              <div className="flex items-center space-x-3">
                                <span className="font-mono text-sm">{table.name}</span>
                                <span className="text-xs text-gray-500">
                                  {formatNumber(table.rows)} rows × {table.columns} cols
                                </span>
                              </div>
                              <button
                                onClick={() => handleDownload(job.job_id, table.name)}
                                className="text-primary-600 hover:text-primary-700 text-sm"
                              >
                                Download
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Error Message */}
                {job.status === 'failed' && job.error && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <h4 className="font-medium text-red-900 mb-2">Error</h4>
                    <p className="text-sm text-red-700">{job.error}</p>
                  </div>
                )}

                {/* Progress Monitor */}
                {(job.status === 'running' || job.status === 'queued') && (
                  <JobStreamMonitor jobId={job.job_id} />
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}


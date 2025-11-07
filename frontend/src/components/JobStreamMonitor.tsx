/**
 * Real-time job monitoring using Server-Sent Events (SSE)
 */

'use client';

import React, { useEffect, useState } from 'react';
import { api } from '@/services/api';
import { useAppStore } from '@/lib/store';
import { Loader2 } from 'lucide-react';

interface JobStreamMonitorProps {
  jobId: string;
}

export default function JobStreamMonitor({ jobId }: JobStreamMonitorProps) {
  const [events, setEvents] = useState<string[]>([]);
  const [progress, setProgress] = useState(0);
  const updateJob = useAppStore((state) => state.updateJob);

  useEffect(() => {
    let eventSource: EventSource | null = null;

    try {
      // Create SSE connection
      eventSource = api.createJobStream(jobId);

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // Update progress
          if (data.progress !== undefined) {
            setProgress(data.progress);
          }

          // Add event message
          if (data.message) {
            setEvents((prev) => [...prev, data.message]);
          }

          // Update job status
          if (data.status) {
            updateJob(jobId, {
              status: data.status,
              progress: data.progress,
              result: data.result,
              error: data.error,
            });

            // Close stream on terminal status
            if (
              data.status === 'succeeded' ||
              data.status === 'failed' ||
              data.status === 'cancelled'
            ) {
              eventSource?.close();
            }
          }
        } catch (error) {
          console.error('Error parsing SSE event:', error);
        }
      };

      eventSource.onerror = (error) => {
        console.error('SSE connection error:', error);
        eventSource?.close();
      };
    } catch (error) {
      console.error('Failed to create SSE connection:', error);
    }

    return () => {
      eventSource?.close();
    };
  }, [jobId, updateJob]);

  return (
    <div className="mt-4 bg-gray-50 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-medium text-gray-900">Progress</h4>
        <span className="text-sm text-gray-600">{progress}%</span>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
        <div
          className="bg-primary-600 h-2 rounded-full transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Event Log */}
      {events.length > 0 && (
        <div className="space-y-1 max-h-32 overflow-y-auto">
          {events.map((event, idx) => (
            <div key={idx} className="flex items-start space-x-2 text-sm">
              <Loader2 className="w-3 h-3 mt-0.5 text-primary-600 animate-spin flex-shrink-0" />
              <span className="text-gray-700">{event}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


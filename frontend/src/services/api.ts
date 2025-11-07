/**
 * API Service Layer for DataForge Studio Backend
 */

import axios, { AxiosInstance, AxiosError } from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || 'dev-key';
const API_PREFIX = '/v1';

// Types matching backend models
export interface PromptRequest {
  prompt: string;
  size_hint?: Record<string, number>;
  seed?: number;
}

export interface SchemaRequest {
  schema: Record<string, any>;
  seed?: number;
}

export interface JobResponse {
  job_id: string;
  status: string;
  message: string;
}

export enum JobStatus {
  QUEUED = 'queued',
  RUNNING = 'running',
  SUCCEEDED = 'succeeded',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

export interface JobStatusResponse {
  job_id: string;
  status: JobStatus;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
  result?: any;
  progress?: number;
}

export interface DocumentRequest {
  subject: string;
  style?: string;
  language?: string;
  length?: string;
}

export interface DocumentResponse {
  document_id: string;
  content: string;
  metadata: {
    subject: string;
    style: string;
    language: string;
    word_count: number;
  };
}

// Custom error class
export class APIError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public details?: any
  ) {
    super(message);
    this.name = 'APIError';
  }
}

/**
 * API Client for DataForge Studio
 */
class DataForgeAPI {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_URL}${API_PREFIX}`,
      headers: {
        'X-API-Key': API_KEY,
        'Content-Type': 'application/json',
      },
      timeout: 30000, // 30 seconds
    });

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response) {
          throw new APIError(
            error.response.data?.detail || error.message,
            error.response.status,
            error.response.data
          );
        } else if (error.request) {
          throw new APIError('No response from server. Check if backend is running.');
        } else {
          throw new APIError(error.message);
        }
      }
    );
  }

  /**
   * Generation API
   */

  async generateFromPrompt(request: PromptRequest): Promise<JobResponse> {
    const response = await this.client.post<JobResponse>('/generation/prompt', request);
    return response.data;
  }

  async generateFromSchema(request: SchemaRequest): Promise<JobResponse> {
    const response = await this.client.post<JobResponse>('/generation/schema', request);
    return response.data;
  }

  async getJobStatus(jobId: string): Promise<JobStatusResponse> {
    const response = await this.client.get<JobStatusResponse>(`/generation/${jobId}`);
    return response.data;
  }

  async cancelJob(jobId: string): Promise<{ job_id: string; status: string }> {
    const response = await this.client.delete(`/generation/${jobId}`);
    return response.data;
  }

  getDownloadUrl(jobId: string, tableName: string = 'data', format: string = 'csv'): string {
    return `${API_URL}${API_PREFIX}/generation/${jobId}/download?table_name=${tableName}&format=${format}&api_key=${API_KEY}`;
  }

  /**
   * Streaming API - Returns EventSource for SSE
   */
  createJobStream(jobId: string): EventSource {
    return new EventSource(`${API_URL}${API_PREFIX}/generation/${jobId}/stream`);
  }

  /**
   * Documents API
   */

  async generateDocument(request: DocumentRequest): Promise<DocumentResponse> {
    const response = await this.client.post<DocumentResponse>('/documents/generate', request);
    return response.data;
  }

  /**
   * Health Check
   */

  async healthCheck(): Promise<any> {
    const response = await this.client.get('/healthz');
    return response.data;
  }
}

// Export singleton instance
export const api = new DataForgeAPI();

// Export class for testing/custom instances
export default DataForgeAPI;


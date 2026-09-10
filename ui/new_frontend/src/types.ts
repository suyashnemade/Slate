export interface Citation {
  chunk_id?: string;
  source?: string;
  filename?: string;
  similarity_score?: number;
  score?: number;
  content?: string;
  metadata?: Record<string, any>;
}

export interface GradeInfo {
  score?: number;
  passed?: boolean;
  feedback?: string;
  criteria?: Record<string, any>;
}

export interface Message {
  id?: number | string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  citations?: Citation[];
  grade?: GradeInfo | null;
  created_at?: string;
}

export interface Chat {
  chat_id: string;
  project_id: string;
  title: string;
  created_at?: string;
  updated_at?: string;
}

export interface DocumentItem {
  doc_id?: string;
  filename: string;
  file_type?: string;
  file_size?: number;
  chunk_count?: number;
  status?: string;
  created_at?: string;
  [key: string]: any;
}

export interface ProjectStats {
  project_id: string;
  total_chunks: number;
}

export interface HealthStatus {
  status: string;
  version: string;
  chroma_dir: string;
  timestamp: string;
}

export interface QueryResponse {
  project_id: string;
  query: string;
  answer: string;
  citations: Citation[];
  context?: string;
  routing?: {
    intent?: string;
    modalities?: string[];
    complexity?: string;
    subqueries?: string[];
  };
  grade?: GradeInfo | null;
  chat_id?: string;
}

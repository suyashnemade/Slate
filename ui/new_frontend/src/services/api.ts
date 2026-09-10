import type { Chat, DocumentItem, HealthStatus, Message, ProjectStats, QueryResponse } from '../types';

let cachedApiBase = localStorage.getItem('slate_api_url') || 'http://127.0.0.1:8000';

export function getApiBase(): string {
  return cachedApiBase;
}

export function setApiBase(url: string): void {
  cachedApiBase = url.replace(/\/+$/, '');
  localStorage.setItem('slate_api_url', cachedApiBase);
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const errorText = await res.text();
    let detail = errorText;
    try {
      const parsed = JSON.parse(errorText);
      detail = parsed.detail || parsed.message || errorText;
    } catch {
      // keep raw detail
    }
    throw new Error(detail || `HTTP Error ${res.status}`);
  }
  return res.json();
}

export const api = {
  async getHealth(): Promise<HealthStatus> {
    const res = await fetch(`${getApiBase()}/health`);
    return handleResponse<HealthStatus>(res);
  },

  async ping(): Promise<{ status: string; timestamp: string }> {
    const res = await fetch(`${getApiBase()}/api/ping`);
    return handleResponse<{ status: string; timestamp: string }>(res);
  },

  async listProjects(): Promise<string[]> {
    const res = await fetch(`${getApiBase()}/api/projects`);
    const data = await handleResponse<{ projects: string[] }>(res);
    return data.projects || [];
  },

  async createProject(projectId: string): Promise<{ status: string; project_id: string }> {
    const res = await fetch(`${getApiBase()}/api/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: projectId }),
    });
    return handleResponse<{ status: string; project_id: string }>(res);
  },

  async deleteProject(projectId: string): Promise<{ status: string; project_id: string }> {
    const res = await fetch(`${getApiBase()}/api/projects/${encodeURIComponent(projectId)}`, {
      method: 'DELETE',
    });
    return handleResponse<{ status: string; project_id: string }>(res);
  },

  async getProjectStats(projectId: string): Promise<ProjectStats> {
    const res = await fetch(`${getApiBase()}/api/projects/${encodeURIComponent(projectId)}/stats`);
    return handleResponse<ProjectStats>(res);
  },

  async listDocuments(projectId: string): Promise<DocumentItem[]> {
    const res = await fetch(`${getApiBase()}/api/projects/${encodeURIComponent(projectId)}/documents`);
    const data = await handleResponse<{ project_id: string; documents: DocumentItem[] }>(res);
    return data.documents || [];
  },

  async uploadDocument(projectId: string, file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${getApiBase()}/api/projects/${encodeURIComponent(projectId)}/documents/upload`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse(res);
  },

  async ingestText(projectId: string, text: string, sourceName?: string): Promise<any> {
    const res = await fetch(`${getApiBase()}/api/projects/${encodeURIComponent(projectId)}/documents/text`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text,
        source_name: sourceName || 'manual_input',
      }),
    });
    return handleResponse(res);
  },

  async listChats(projectId: string): Promise<Chat[]> {
    const res = await fetch(`${getApiBase()}/api/projects/${encodeURIComponent(projectId)}/chats`);
    const data = await handleResponse<{ project_id: string; chats: Chat[] }>(res);
    return data.chats || [];
  },

  async createChat(projectId: string, title?: string, chatId?: string): Promise<Chat> {
    const res = await fetch(`${getApiBase()}/api/projects/${encodeURIComponent(projectId)}/chats`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: title || 'New Chat', chat_id: chatId }),
    });
    return handleResponse<Chat>(res);
  },

  async getMessages(projectId: string, chatId: string): Promise<Message[]> {
    const res = await fetch(`${getApiBase()}/api/projects/${encodeURIComponent(projectId)}/chats/${encodeURIComponent(chatId)}/messages`);
    const data = await handleResponse<{ project_id: string; chat_id: string; messages: any[] }>(res);
    // Parse JSON string fields if necessary
    return (data.messages || []).map((m) => {
      let citations = m.citations;
      if (typeof citations === 'string') {
        try {
          citations = JSON.parse(citations);
        } catch {
          citations = [];
        }
      }
      let grade = m.grade;
      if (typeof grade === 'string') {
        try {
          grade = JSON.parse(grade);
        } catch {
          grade = null;
        }
      }
      return {
        ...m,
        citations,
        grade,
      };
    });
  },

  async queryProject(projectId: string, payload: {
    query: string;
    chat_id?: string;
    top_k?: number;
    grade_response?: boolean;
  }): Promise<QueryResponse> {
    const res = await fetch(`${getApiBase()}/api/projects/${encodeURIComponent(projectId)}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<QueryResponse>(res);
  },
};

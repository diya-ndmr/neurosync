const configuredApiUrl = import.meta.env.VITE_API_URL?.replace(/\/+$/, '');
const apiConfigured = Boolean(configuredApiUrl) || !import.meta.env.PROD;
export const API_BASE = configuredApiUrl
  ? configuredApiUrl.endsWith('/api')
    ? configuredApiUrl
    : `${configuredApiUrl}/api`
  : '/api';

export class ApiUnavailableError extends Error {
  constructor() {
    super(
      'The NeuroSync API is unavailable. Configure VITE_API_URL with the deployed backend URL and allow this frontend origin in backend CORS_ORIGINS.',
    );
    this.name = 'ApiUnavailableError';
  }
}

export function isApiUnavailableError(error: unknown): boolean {
  return error instanceof ApiUnavailableError
    || (error instanceof Error && /failed to fetch|networkerror|load failed/i.test(error.message));
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: unknown;
  token?: string;
}

async function request<T>(path: string, { method = 'GET', body, token }: RequestOptions = {}): Promise<T> {
  if (!apiConfigured) throw new ApiUnavailableError();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined
    });
  } catch (error) {
    if (error instanceof TypeError) throw new ApiUnavailableError();
    throw error;
  }

  if (!res.ok) {
    let message = `Request failed with status ${res.status}`;
    try {
      const data = await res.json();
      if (data.detail) message = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
      else if (data.message) message = data.message;
    } catch {
      // ignore parse errors
    }
    if (res.status === 401 && token) {
      window.dispatchEvent(new CustomEvent('neurosync:session-expired'));
    }
    throw new ApiError(res.status, message);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

async function requestBlob(path: string, token?: string): Promise<Blob> {
  if (!apiConfigured) throw new ApiUnavailableError();
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, { headers });
  } catch (error) {
    if (error instanceof TypeError) throw new ApiUnavailableError();
    throw error;
  }
  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const data = await response.json();
      if (data.detail) message = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
    } catch {
      // Keep the HTTP status message when the server response is not JSON.
    }
    if (response.status === 401 && token) window.dispatchEvent(new CustomEvent('neurosync:session-expired'));
    throw new ApiError(response.status, message);
  }
  return response.blob();
}

async function requestForm<T>(path: string, form: FormData, token?: string): Promise<T> {
  if (!apiConfigured) throw new ApiUnavailableError();
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, { method: 'POST', headers, body: form });
  } catch (error) {
    if (error instanceof TypeError) throw new ApiUnavailableError();
    throw error;
  }
  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const data = await response.json();
      if (data.detail) message = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
    } catch {
      // Keep the HTTP status message when the server response is not JSON.
    }
    if (response.status === 401 && token) window.dispatchEvent(new CustomEvent('neurosync:session-expired'));
    throw new ApiError(response.status, message);
  }
  return response.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string, token?: string) => request<T>(path, { token }),
  getBlob: (path: string, token?: string) => requestBlob(path, token),
  postForm: <T>(path: string, form: FormData, token?: string) => requestForm<T>(path, form, token),
  post: <T>(path: string, body: unknown, token?: string) => request<T>(path, { method: 'POST', body, token }),
  put: <T>(path: string, body: unknown, token?: string) => request<T>(path, { method: 'PUT', body, token }),
  patch: <T>(path: string, body: unknown, token?: string) => request<T>(path, { method: 'PATCH', body, token }),
  delete: <T>(path: string, token?: string) => request<T>(path, { method: 'DELETE', token })
};

const configuredApiUrl = import.meta.env.VITE_API_URL?.replace(/\/+$/, '');
const apiConfigured = Boolean(configuredApiUrl) || !import.meta.env.PROD;
const API_REQUEST_TIMEOUT_MS = 15000;
export const API_BASE = configuredApiUrl
  ? configuredApiUrl.endsWith('/api')
    ? configuredApiUrl
    : `${configuredApiUrl}/api`
  : '/api';

export class ApiUnavailableError extends Error {
  constructor(message = 'The NeuroSync API is unavailable. Configure VITE_API_URL with the deployed backend URL and allow this frontend origin in backend CORS_ORIGINS.') {
    super(message);
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

async function fetchWithTimeout(url: string, init: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), API_REQUEST_TIMEOUT_MS);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } catch (error) {
    if (controller.signal.aborted) {
      throw new ApiUnavailableError(`The NeuroSync API did not respond within ${API_REQUEST_TIMEOUT_MS / 1000} seconds. Check the production backend URL and its availability.`);
    }
    if (error instanceof TypeError) throw new ApiUnavailableError();
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

async function request<T>(path: string, { method = 'GET', body, token }: RequestOptions = {}): Promise<T> {
  if (!apiConfigured) throw new ApiUnavailableError();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetchWithTimeout(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined
  });

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
  const response = await fetchWithTimeout(`${API_BASE}${path}`, { headers });
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
  const response = await fetchWithTimeout(`${API_BASE}${path}`, { method: 'POST', headers, body: form });
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

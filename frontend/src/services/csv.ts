import { API_BASE } from './api';

export type CsvDataset = 'students' | 'modules' | 'attendance' | 'assessments';
export type CsvExportDataset = CsvDataset | 'referrals' | 'interventions' | 'meetings' | 'workbook-intelligence';
export type CsvImportMode = 'create' | 'update' | 'upsert';

export interface CsvCatalog {
  import: Record<CsvDataset, { columns: string[]; modes: CsvImportMode[] }>;
  export: Record<CsvExportDataset, string[]>;
  rules: Record<CsvDataset, string>;
  max_file_bytes: number;
  max_rows: number;
}

export interface CsvRowError {
  row: number;
  field: string | null;
  code: string;
  message: string;
}

export interface CsvImportResult {
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  duplicate_rows: number;
  persisted_rows: number;
  created_rows?: number;
  updated_rows?: number;
  preview: Record<string, string | number>[];
  errors: CsvRowError[];
  errors_truncated: boolean;
}

export class CsvRequestError extends Error {
  result?: CsvImportResult;

  constructor(message: string, result?: CsvImportResult) {
    super(message);
    this.name = 'CsvRequestError';
    this.result = result;
  }
}

async function csvRequest<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set('Authorization', `Bearer ${token}`);
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    let message = `CSV request failed with status ${response.status}`;
    let result: CsvImportResult | undefined;
    try {
      const body = await response.json();
      if (typeof body.detail === 'string') message = body.detail;
      else if (body.detail && typeof body.detail === 'object') {
        result = body.detail as CsvImportResult;
        message = 'Import was rejected. Review the row errors and correct the CSV.';
      }
    } catch {
      // Keep the HTTP status message when the server did not return JSON.
    }
    throw new CsvRequestError(message, result);
  }
  return response.json() as Promise<T>;
}

export function fetchCsvCatalog(token: string): Promise<CsvCatalog> {
  return csvRequest('/admin/csv/datasets', token);
}

export function previewCsv(
  dataset: CsvDataset,
  file: File,
  mode: CsvImportMode,
  token: string
): Promise<CsvImportResult> {
  const form = new FormData();
  form.set('file', file);
  const query = new URLSearchParams({ mode });
  return csvRequest(`/admin/csv/import/${dataset}/preview?${query}`, token, { method: 'POST', body: form });
}

export function importCsv(
  dataset: CsvDataset,
  file: File,
  mode: CsvImportMode,
  token: string
): Promise<CsvImportResult> {
  const form = new FormData();
  form.set('file', file);
  const query = new URLSearchParams({ mode });
  return csvRequest(`/admin/csv/import/${dataset}?${query}`, token, { method: 'POST', body: form });
}

export async function downloadCsv(
  dataset: CsvExportDataset,
  filters: URLSearchParams,
  token: string
): Promise<void> {
  const response = await fetch(`${API_BASE}/admin/csv/export/${dataset}?${filters}`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!response.ok) {
    let message = `CSV export failed with status ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body.detail === 'string') message = body.detail;
    } catch {
      // Keep the HTTP status message when the server did not return JSON.
    }
    throw new CsvRequestError(message);
  }
  const blob = await response.blob();
  const link = document.createElement('a');
  const objectUrl = URL.createObjectURL(blob);
  link.href = objectUrl;
  link.download = `neurosync-${dataset}.csv`;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}

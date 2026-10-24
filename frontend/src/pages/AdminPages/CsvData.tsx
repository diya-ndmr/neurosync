import { useEffect, useState, type ChangeEvent } from 'react';
import { Download, FileUp, RefreshCw } from 'lucide-react';
import NeoButton from '../../components/Buttons/NeoButton';
import { useAuth } from '../../context/AuthContext';
import {
  CsvRequestError,
  downloadCsv,
  fetchCsvCatalog,
  importCsv,
  previewCsv,
  type CsvCatalog,
  type CsvDataset,
  type CsvExportDataset,
  type CsvImportMode,
  type CsvImportResult
} from '../../services/csv';

const DATASETS: { id: CsvDataset; label: string }[] = [
  { id: 'students', label: 'Student records' },
  { id: 'modules', label: 'Modules' },
  { id: 'attendance', label: 'Attendance' },
  { id: 'assessments', label: 'Assessments' }
];

const EXPORT_DATASETS: { id: CsvExportDataset; label: string }[] = [
  ...DATASETS,
  { id: 'referrals', label: 'Referrals' },
  { id: 'interventions', label: 'Interventions' },
  { id: 'meetings', label: 'Meetings' },
  { id: 'workbook-intelligence', label: 'Workbook reports' }
];

function resultFromError(error: unknown): CsvImportResult | undefined {
  return error instanceof CsvRequestError ? error.result : undefined;
}

export default function CsvData() {
  const { token } = useAuth();
  const [catalog, setCatalog] = useState<CsvCatalog | null>(null);
  const [importDataset, setImportDataset] = useState<CsvDataset>('students');
  const [exportDataset, setExportDataset] = useState<CsvExportDataset>('students');
  const [mode, setMode] = useState<CsvImportMode>('create');
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<CsvImportResult | null>(null);
  const [importResult, setImportResult] = useState<CsvImportResult | null>(null);
  const [error, setError] = useState('');
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [previewing, setPreviewing] = useState(false);
  const [importing, setImporting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [studentFilter, setStudentFilter] = useState('');
  const [moduleFilter, setModuleFilter] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [sheetName, setSheetName] = useState('');
  const [selectedColumns, setSelectedColumns] = useState<string[]>([]);

  useEffect(() => {
    if (!token) return;
    let active = true;
    fetchCsvCatalog(token)
      .then((data) => {
        if (active) setCatalog(data);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : 'Could not load CSV options.');
      })
      .finally(() => {
        if (active) setLoadingCatalog(false);
      });
    return () => {
      active = false;
    };
  }, [token]);

  useEffect(() => {
    setSelectedColumns(catalog?.export[exportDataset] ?? []);
    setDateFrom('');
    setDateTo('');
    setSheetName('');
  }, [catalog, exportDataset]);

  const resetImport = () => {
    setPreview(null);
    setImportResult(null);
    setError('');
  };

  const handleDatasetChange = (event: ChangeEvent<HTMLSelectElement>) => {
    setImportDataset(event.target.value as CsvDataset);
    setFile(null);
    setMode('create');
    resetImport();
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const nextFile = event.target.files?.[0] ?? null;
    event.target.value = '';
    setFile(nextFile);
    resetImport();
    if (nextFile && catalog) {
      if (!nextFile.name.toLowerCase().endsWith('.csv')) {
        setError('Choose a CSV file.');
      } else if (nextFile.size > catalog.max_file_bytes) {
        setError(`The file exceeds the ${Math.floor(catalog.max_file_bytes / (1024 * 1024))} MiB limit.`);
      }
    }
  };

  const handlePreview = async () => {
    if (!file || !token) return;
    setPreviewing(true);
    setError('');
    setImportResult(null);
    try {
      setPreview(await previewCsv(importDataset, file, mode, token));
    } catch (reason) {
      setPreview(resultFromError(reason) ?? null);
      setError(reason instanceof Error ? reason.message : 'Could not validate the CSV.');
    } finally {
      setPreviewing(false);
    }
  };

  const handleImport = async () => {
    if (!file || !token || !preview || preview.invalid_rows > 0 || preview.valid_rows === 0) return;
    setImporting(true);
    setError('');
    try {
      const result = await importCsv(importDataset, file, mode, token);
      setImportResult(result);
      setPreview(result);
    } catch (reason) {
      const result = resultFromError(reason);
      if (result) setPreview(result);
      setError(reason instanceof Error ? reason.message : 'The CSV could not be imported.');
    } finally {
      setImporting(false);
    }
  };

  const handleExport = async () => {
    if (!token || !selectedColumns.length) return;
    if (dateFrom && dateTo && dateFrom > dateTo) {
      setError('Start date must be on or before end date.');
      return;
    }
    setExporting(true);
    setError('');
    const filters = new URLSearchParams();
    if (studentFilter.trim() && !['modules', 'workbook-intelligence'].includes(exportDataset)) {
      filters.set(
        ['referrals', 'interventions', 'meetings'].includes(exportDataset) ? 'student_id' : 'student_number',
        studentFilter.trim()
      );
    }
    if (moduleFilter.trim() && ['modules', 'attendance', 'assessments'].includes(exportDataset)) {
      filters.set('module_code', moduleFilter.trim());
    }
    if (dateFrom) filters.set('date_from', dateFrom);
    if (dateTo) filters.set('date_to', dateTo);
    if (sheetName.trim()) filters.set('sheet_name', sheetName.trim());
    if (catalog && selectedColumns.length !== catalog.export[exportDataset].length) {
      filters.set('columns', selectedColumns.join(','));
    }
    try {
      await downloadCsv(exportDataset, filters, token);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not export the selected records.');
    } finally {
      setExporting(false);
    }
  };

  const changeColumn = (column: string, checked: boolean) => {
    setSelectedColumns((current) => checked
      ? [...current, column]
      : current.filter((value) => value !== column));
  };

  const modes = catalog?.import[importDataset].modes ?? ['create'];
  const dateFilterApplies = ['attendance', 'assessments', 'referrals', 'interventions', 'meetings'].includes(exportDataset);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-ink">CSV data management</h1>
        <p className="mt-1 text-sm text-ink-soft">
          Preview and validate records before importing. Exports contain records read from the database.
          CSV access is restricted to administrators.
        </p>
      </header>

      {error && <p role="alert" className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-800">{error}</p>}
      {loadingCatalog && <p role="status" className="text-sm text-ink-soft">Loading CSV options…</p>}

      {catalog && (
        <>
          <section className="neo-card space-y-5 p-6">
            <div>
              <h2 className="text-lg font-bold text-ink">Import a CSV file</h2>
              <p className="mt-1 text-sm text-ink-soft">
                UTF-8 CSV only, up to {Math.floor(catalog.max_file_bytes / (1024 * 1024))} MiB and {catalog.max_rows.toLocaleString()} records.
                Imports are all-or-nothing; invalid or conflicting rows prevent any records from being written.
              </p>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="text-sm font-semibold text-ink">
                Dataset
                <select value={importDataset} onChange={handleDatasetChange} className="neo-input mt-1 block w-full">
                  {DATASETS.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
                </select>
              </label>
              {modes.length > 1 && (
                <label className="text-sm font-semibold text-ink">
                  Import rule
                  <select
                    value={mode}
                    onChange={(event) => {
                      setMode(event.target.value as CsvImportMode);
                      resetImport();
                    }}
                    className="neo-input mt-1 block w-full"
                  >
                    <option value="create">Create only — reject existing identifiers</option>
                    <option value="update">Update only — reject new identifiers</option>
                    <option value="upsert">Create new; update matching identifiers</option>
                  </select>
                </label>
              )}
            </div>
            <div className="rounded bg-slate-50 p-3">
              <p className="text-sm font-semibold text-ink">Required headers, in any order:</p>
              <code className="mt-1 block break-words text-xs text-ink-soft">{catalog.import[importDataset].columns.join(',')}</code>
              <p className="mt-2 text-xs text-ink-soft">{catalog.rules[importDataset]}</p>
            </div>
            <div className="flex flex-wrap items-end gap-3">
              <label className="min-w-56 flex-1 text-sm font-semibold text-ink">
                CSV file
                <input
                  type="file"
                  accept=".csv,text/csv"
                  onChange={handleFileChange}
                  className="mt-1 block w-full text-sm"
                />
              </label>
              <NeoButton type="button" size="md" onClick={handlePreview} disabled={!file || previewing || importing}>
                <span className="inline-flex items-center gap-2"><FileUp size={16} />{previewing ? 'Validating…' : 'Preview and validate'}</span>
              </NeoButton>
            </div>
            {file && <p className="text-xs text-ink-faint">Selected: {file.name} ({file.size.toLocaleString()} bytes)</p>}
          </section>

          {preview && (
            <section className="neo-card space-y-4 p-6" aria-live="polite">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-bold text-ink">Import preview</h2>
                  <p className="text-sm text-ink-soft">{preview.total_rows} rows checked</p>
                </div>
                {preview.valid_rows > 0 && preview.invalid_rows === 0 && !importResult && (
                  <NeoButton type="button" size="md" onClick={handleImport} disabled={importing || previewing}>
                    <span className="inline-flex items-center gap-2"><RefreshCw size={16} />{importing ? 'Importing…' : `Import ${preview.valid_rows} records`}</span>
                  </NeoButton>
                )}
              </div>
              <div className="grid gap-3 sm:grid-cols-4">
                <Count label="Valid" value={preview.valid_rows} />
                <Count label="Invalid" value={preview.invalid_rows} />
                <Count label="Duplicates" value={preview.duplicate_rows} />
                <Count label="Persisted" value={importResult?.persisted_rows ?? preview.persisted_rows} />
              </div>
              {importResult && (
                <p role="status" className="rounded border border-emerald-300 bg-emerald-50 p-3 text-sm text-emerald-800">
                  Imported {importResult.persisted_rows} records ({importResult.created_rows ?? importResult.persisted_rows} created, {importResult.updated_rows ?? 0} updated).
                </p>
              )}
              {preview.preview.length > 0 && (
                <div className="overflow-x-auto">
                  <table className="min-w-full border-collapse text-left text-xs">
                    <thead><tr>{Object.keys(preview.preview[0]).map((column) => <th key={column} className="border-b p-2 font-semibold">{column}</th>)}</tr></thead>
                    <tbody>
                      {preview.preview.map((row, index) => (
                        <tr key={index}>{Object.values(row).map((value, cell) => <td key={cell} className="max-w-64 border-b p-2">{String(value)}</td>)}</tr>
                      ))}
                    </tbody>
                  </table>
                  {preview.valid_rows > preview.preview.length && (
                    <p className="mt-2 text-xs text-ink-faint">Showing {preview.preview.length} preview rows.</p>
                  )}
                </div>
              )}
              {preview.errors.length > 0 && (
                <div className="max-h-72 overflow-auto rounded border border-amber-300 bg-amber-50 p-3">
                  <h3 className="font-semibold text-amber-950">Fix these rows and upload the corrected file</h3>
                  <ul className="mt-2 space-y-1 text-sm text-amber-900">
                    {preview.errors.map((rowError, index) => (
                      <li key={`${rowError.row}-${rowError.code}-${index}`}>
                        Row {rowError.row}{rowError.field ? ` · ${rowError.field}` : ''}: {rowError.message}
                      </li>
                    ))}
                  </ul>
                  {preview.errors_truncated && <p className="mt-2 text-xs">Additional validation errors are not shown.</p>}
                </div>
              )}
              {preview.invalid_rows > 0 && <p className="text-sm text-amber-800">Nothing was imported. Correct the errors and preview again.</p>}
            </section>
          )}

          <section className="neo-card space-y-5 p-6">
            <div>
              <h2 className="text-lg font-bold text-ink">Export database records</h2>
              <p className="mt-1 text-sm text-ink-soft">Choose filters and columns. Downloads are generated from authorized database queries.</p>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="text-sm font-semibold text-ink">
                Dataset
                <select
                  value={exportDataset}
                  onChange={(event) => setExportDataset(event.target.value as CsvExportDataset)}
                  className="neo-input mt-1 block w-full"
                >
                  {EXPORT_DATASETS.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
                </select>
              </label>
              {!['modules', 'workbook-intelligence'].includes(exportDataset) && (
                <label className="text-sm font-semibold text-ink">
                  {['referrals', 'interventions', 'meetings'].includes(exportDataset) ? 'LMS student ID (optional)' : 'Student number (optional)'}
                  <input value={studentFilter} onChange={(event) => setStudentFilter(event.target.value)} className="neo-input mt-1 block w-full" />
                </label>
              )}
              {['modules', 'attendance', 'assessments'].includes(exportDataset) && (
                <label className="text-sm font-semibold text-ink">
                  Module code (optional)
                  <input value={moduleFilter} onChange={(event) => setModuleFilter(event.target.value)} className="neo-input mt-1 block w-full" />
                </label>
              )}
              {exportDataset === 'workbook-intelligence' && (
                <label className="text-sm font-semibold text-ink">
                  Sheet name (optional)
                  <input value={sheetName} onChange={(event) => setSheetName(event.target.value)} className="neo-input mt-1 block w-full" />
                </label>
              )}
              {dateFilterApplies && (
                <>
                  <label className="text-sm font-semibold text-ink">
                    From date
                    <input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} className="neo-input mt-1 block w-full" />
                  </label>
                  <label className="text-sm font-semibold text-ink">
                    To date
                    <input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} className="neo-input mt-1 block w-full" />
                  </label>
                </>
              )}
            </div>
            <fieldset>
              <legend className="text-sm font-semibold text-ink">Include columns</legend>
              <div className="mt-2 flex flex-wrap gap-x-5 gap-y-2">
                {(catalog.export[exportDataset] ?? []).map((column) => (
                  <label key={column} className="inline-flex items-center gap-2 text-sm text-ink-soft">
                    <input
                      type="checkbox"
                      checked={selectedColumns.includes(column)}
                      onChange={(event) => changeColumn(column, event.target.checked)}
                    />
                    {column}
                  </label>
                ))}
              </div>
            </fieldset>
            <NeoButton type="button" size="md" onClick={handleExport} disabled={exporting || !selectedColumns.length}>
              <span className="inline-flex items-center gap-2"><Download size={16} />{exporting ? 'Preparing CSV…' : 'Download CSV'}</span>
            </NeoButton>
          </section>
        </>
      )}
    </div>
  );
}

function Count({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded border border-slate-200 p-3">
      <p className="text-xs text-ink-faint">{label}</p>
      <p className="text-xl font-bold text-ink">{value.toLocaleString()}</p>
    </div>
  );
}

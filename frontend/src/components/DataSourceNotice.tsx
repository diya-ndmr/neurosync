interface DataSourceNoticeProps {
  source: 'live' | 'offline-demo' | null;
}

export default function DataSourceNotice({ source }: DataSourceNoticeProps) {
  if (source !== 'offline-demo') return null;

  return (
    <aside role="status" className="rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950">
      Demo data only. The backend is unavailable, so these values are not live institutional records.
    </aside>
  );
}

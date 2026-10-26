interface DataSourceNoticeProps {
  source: 'live' | 'offline-demo' | 'demo-sample' | null;
}

export default function DataSourceNotice({ source }: DataSourceNoticeProps) {
  if (source === 'live' || source === null) return null;

  return (
    <aside role="status" className="rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950">
      {source === 'offline-demo'
        ? 'Demo data only. The backend is unavailable, so these values are not live institutional records.'
        : 'Demo examples are shown because this section has no recorded entries yet. They are not live student records.'}
    </aside>
  );
}

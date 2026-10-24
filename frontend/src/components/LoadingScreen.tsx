import Logo from './Logo';

export default function LoadingScreen() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-ns-background">
      <Logo size="md" />
      <p className="text-sm text-ns-text-secondary">Loading NeuroSync…</p>
    </div>
  );
}

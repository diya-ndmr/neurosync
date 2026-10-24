import Logo from '../Logo';

export default function SplashScreen() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-ns-background">
      <Logo size="lg" />
      <p className="text-sm text-ns-text-secondary">Loading your workspace…</p>
    </div>
  );
}

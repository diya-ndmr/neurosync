import type { ReactNode } from 'react';
import { useAuth } from '../context/AuthContext';
import { greeting } from '../utils/helpers';

interface DashboardHeroProps {
  icon: ReactNode;
}

export default function DashboardHero({ icon }: DashboardHeroProps) {
  const { user } = useAuth();
  const firstName = user?.name.trim().split(/\s+/)[0] || 'there';

  return (
    <section className="dashboard-page-hero" aria-label="Dashboard overview">
      <div className="dashboard-page-hero-copy">
        <h1>{greeting()}, {firstName}.</h1>
      </div>
      <div className="dashboard-page-hero-art" aria-hidden="true">
        <span className="dashboard-page-hero-orbit dashboard-page-hero-orbit-outer" />
        <span className="dashboard-page-hero-orbit dashboard-page-hero-orbit-inner" />
        <span className="dashboard-page-hero-icon">{icon}</span>
      </div>
    </section>
  );
}

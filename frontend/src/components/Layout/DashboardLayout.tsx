import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from '../Sidebar/Sidebar';
import Navbar from '../Navbar/Navbar';
import DemoEnvironmentNotice from '../DemoEnvironmentNotice';
import { useAuth } from '../../context/AuthContext';
import { Navigate } from 'react-router-dom';
import type { Role } from '../../types';
import { useAccessibility } from '../../context/AccessibilityContext';

interface DashboardLayoutProps {
  allowedRoles: Role[];
}

export default function DashboardLayout({ allowedRoles }: DashboardLayoutProps) {
  const { user } = useAuth();
  const { t } = useAccessibility();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  if (!user) return <Navigate to="/login" replace />;
  if (!allowedRoles.includes(user.role)) return <Navigate to="/login" replace />;

  return (
    <div className="flex min-h-screen bg-ai-gradient">
      <a className="skip-link" href="#main-content">{t('common.skipToContent')}</a>
      <Sidebar
        collapsed={collapsed}
        onToggle={() => setCollapsed((v) => !v)}
        mobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
      />
      <div className="flex-1 flex flex-col min-w-0">
        <Navbar onMenuClick={() => setMobileOpen(true)} mobileMenuOpen={mobileOpen} />
        <main id="main-content" tabIndex={-1} className="flex-1 px-4 md:px-6 py-5 md:py-6 pb-20 md:pb-6 focus:outline-none">
          <div className="page-content">
            <Outlet />
          </div>
          <DemoEnvironmentNotice />
        </main>
      </div>
    </div>
  );
}

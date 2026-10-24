import { NavLink, useNavigate } from 'react-router-dom';
import { useEffect, useRef } from 'react';
import { ChevronLeft } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import Logo from '../Logo';
import { cn, initials } from '../../utils/helpers';
import type { Role } from '../../types';
import { useAccessibility } from '../../context/AccessibilityContext';

interface NavItem {
  label: string;
  translationKey?: string;
  path: string;
}

const roleNav: Record<Role, NavItem[]> = {
  student: [
    { label: 'Dashboard', translationKey: 'navigation.dashboard', path: '/student/dashboard' },
    { label: 'Academics', translationKey: 'navigation.academics', path: '/student/academics' },
    { label: 'Attendance', translationKey: 'navigation.attendance', path: '/student/attendance' },
    { label: 'Wellbeing', translationKey: 'navigation.wellbeing', path: '/student/wellbeing' },
    { label: 'Support plan', translationKey: 'navigation.supportPlan', path: '/student/recommendations' },
    { label: 'Profile', translationKey: 'navigation.profile', path: '/student/profile' }
  ],
  lecturer: [
    { label: 'Dashboard', translationKey: 'navigation.dashboard', path: '/lecturer/dashboard' },
    { label: 'Students needing support', translationKey: 'navigation.students', path: '/lecturer/students' },
    { label: 'Class performance', translationKey: 'navigation.analytics', path: '/lecturer/analytics' }
  ],
  advisor: [
    { label: 'Dashboard', translationKey: 'navigation.dashboard', path: '/advisor/dashboard' },
    { label: 'Student Cases', translationKey: 'navigation.cases', path: '/advisor/cases' },
    { label: 'Interventions', translationKey: 'navigation.interventions', path: '/advisor/interventions' }
  ],
  admin: [
    { label: 'Dashboard', translationKey: 'navigation.dashboard', path: '/admin/dashboard' },
    { label: 'University overview', translationKey: 'navigation.universityOverview', path: '/admin/analytics' },
    { label: 'User Management', translationKey: 'navigation.userManagement', path: '/admin/users' },
    { label: 'CSV data', path: '/admin/csv-data' },
    { label: 'System Configuration', translationKey: 'navigation.systemConfiguration', path: '/admin/settings' }
  ]
};

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  mobileOpen: boolean;
  onMobileClose: () => void;
}

export default function Sidebar({ collapsed, onToggle, mobileOpen, onMobileClose }: SidebarProps) {
  const { user, logout } = useAuth();
  const { t } = useAccessibility();
  const navigate = useNavigate();
  const drawerRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!mobileOpen || !drawerRef.current) return;
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const drawer = drawerRef.current;
    const focusable = Array.from(drawer.querySelectorAll<HTMLElement>('a[href], button:not([disabled])')).filter((element) => element.getClientRects().length > 0);
    focusable[0]?.focus();
    return () => previousFocus?.focus();
  }, [mobileOpen]);

  if (!user) return null;

  const items = roleNav[user.role];
  const preferencesPath = `/${user.role}/preferences`;

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const content = (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className={cn('flex items-center gap-2 py-4', collapsed ? 'justify-between px-3' : 'justify-between px-5')}>
        <Logo size="sm" showText={!collapsed} inverse />
        <button
          onClick={onToggle}
          className="hidden md:flex min-h-11 min-w-11 items-center justify-center rounded bg-ns-black border border-white/20 text-white hover:bg-brand-700"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <ChevronLeft size={16} className={cn('transition-transform', collapsed && 'rotate-180')} />
        </button>
      </div>

      {/* User profile */}
      <div className="mx-3 mb-4">
        <div className={cn('p-3 flex items-center gap-3 rounded-lg bg-white/5 border border-white/10', collapsed ? 'justify-center' : '')}>
          <div className="w-10 h-10 rounded bg-white/10 text-white font-semibold flex items-center justify-center shrink-0">
            {initials(user.name)}
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <p className="text-sm font-bold text-white truncate">{user.name}</p>
              <p className="text-[11px] text-white/60 capitalize">{user.role}</p>
            </div>
          )}
        </div>
      </div>

      {/* Nav */}
      <nav aria-label="Primary navigation" className="flex-1 px-3 space-y-1 overflow-y-auto">
        {items.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path.endsWith('/dashboard')}
            onClick={onMobileClose}
            className={({ isActive }) =>
              cn(
                'flex items-center px-3 py-3 rounded text-sm font-medium transition-colors',
                isActive
                  ? 'border-l-2 border-brand-300 bg-white/10 text-white'
                  : 'text-white/75 hover:bg-white/5 hover:text-white',
                collapsed && 'px-2 text-xs'
              )
            }
            title={collapsed ? (item.translationKey ? t(item.translationKey) : item.label) : undefined}
          >
            <span>{item.translationKey ? t(item.translationKey) : item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Bottom */}
      <div className="px-3 py-4 space-y-1 border-t border-white/10">
        <button
          onClick={() => navigate(preferencesPath)}
          className={cn('w-full min-h-11 flex items-center px-4 py-3 rounded text-sm font-medium text-white/75 hover:bg-white/5 hover:text-white transition-colors', collapsed && 'px-2 text-xs')}
          aria-label={t('navigation.preferences')}
        >
          <span>{t('navigation.preferences')}</span>
        </button>
        {user.role === 'student' && <button
          onClick={() => navigate('/student/settings')}
          className={cn(
            'w-full flex items-center px-4 py-3 rounded text-sm font-medium text-white/75 hover:bg-white/5 hover:text-white transition-colors',
            collapsed && 'px-2 text-xs'
          )}
        >
          <span>{t('navigation.settings')}</span>
        </button>}
        <button
          onClick={handleLogout}
          className={cn(
            'w-full min-h-11 flex items-center px-4 py-3 rounded text-sm font-medium text-white/75 hover:bg-white/5 hover:text-white transition-colors',
            collapsed && 'px-2 text-xs'
          )}
        >
          <span>{t('navigation.logout')}</span>
        </button>
      </div>

    </div>
  );
  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className={cn(
          'hidden md:flex flex-col sticky top-0 h-screen bg-ns-black border-r border-white/10 shrink-0',
          collapsed ? 'w-[184px]' : 'w-[256px]'
        )}
      >
        {content}
      </aside>

      {/* Mobile bottom nav */}
      <nav aria-label="Mobile primary navigation" className="md:hidden fixed bottom-0 left-0 right-0 z-40 glass border-t border-ns-border px-2 pb-[env(safe-area-inset-bottom)]">
        <div className="flex justify-around items-center py-2">
          {items.slice(0, 5).map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path.endsWith('/dashboard')}
              className={({ isActive }) =>
                cn(
                  'flex min-h-11 min-w-11 flex-col items-center justify-center px-2 py-1.5 rounded text-xs font-medium transition-colors',
                  isActive ? 'text-brand-800' : 'text-ns-text-muted'
                )
              }
            >
              {item.translationKey ? t(item.translationKey).split(' ')[0] : item.label.split(' ')[0]}
            </NavLink>
          ))}
        </div>
      </nav>

      {/* Mobile drawer */}
      {mobileOpen && <>
        <button
          type="button"
          aria-label={t('navigation.closeMenu')}
          onClick={onMobileClose}
          className="md:hidden fixed inset-0 z-40 bg-ink/40"
        />
        <aside
          id="mobile-navigation-drawer"
          ref={drawerRef}
          className="md:hidden fixed left-0 top-0 bottom-0 z-50 w-[280px] bg-ns-black shadow-xl"
          role="dialog"
          aria-modal="true"
          aria-label={t('navigation.primary')}
          onKeyDown={(event) => {
            if (event.key === 'Escape') onMobileClose();
            if (event.key === 'Tab' && drawerRef.current) {
              const focusable = Array.from(drawerRef.current.querySelectorAll<HTMLElement>('a[href], button:not([disabled])')).filter((element) => element.getClientRects().length > 0);
              const first = focusable[0];
              const last = focusable[focusable.length - 1];
              if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
              else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
            }
          }}
        >
          {content}
        </aside>
      </>}
    </>
  );
}

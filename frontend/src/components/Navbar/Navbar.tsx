import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Logo from '../Logo';
import { initials } from '../../utils/helpers';
import { useAccessibility } from '../../context/AccessibilityContext';

interface NavbarProps {
  onMenuClick: () => void;
  mobileMenuOpen: boolean;
}

export default function Navbar({ onMenuClick, mobileMenuOpen }: NavbarProps) {
  const { user, logout } = useAuth();
  const { t } = useAccessibility();
  const navigate = useNavigate();
  const [profileOpen, setProfileOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const profileButtonRef = useRef<HTMLButtonElement>(null);
  const profileMenuRef = useRef<HTMLDivElement>(null);

  if (!user) return null;

  const settingsPath = user.role === 'student' ? '/student/settings' : user.role === 'admin' ? '/admin/settings' : null;
  const searchPath = user.role === 'admin' ? '/admin/users' : user.role === 'lecturer' ? '/lecturer/students' : user.role === 'advisor' ? '/advisor/cases' : null;
  const preferencesPath = `/${user.role}/preferences`;
  const portalLabel = user.role === 'student' ? 'Student portal' : 'University staff portal';

  useEffect(() => {
    if (!profileOpen) return;
    profileMenuRef.current?.querySelector<HTMLButtonElement>('button')?.focus();
  }, [profileOpen]);

  const submitSearch = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!searchPath || !searchQuery.trim()) return;
    navigate(searchPath, { state: { globalSearch: searchQuery.trim() } });
    setSearchOpen(false);
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <header className="sticky top-0 z-30 glass border-b border-ns-border px-4 md:px-6 py-3">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <button
            onClick={onMenuClick}
            className="md:hidden min-h-11 rounded bg-white border border-ns-border px-3 text-sm text-ns-text-secondary hover:text-brand-800 focus-visible:ring-2 focus-visible:ring-brand-500"
            aria-label={t('navigation.openMenu')}
            aria-expanded={mobileMenuOpen}
            aria-controls="mobile-navigation-drawer"
          >
            Menu
          </button>

          {/* Mobile logo */}
          <div className="md:hidden">
            <Logo size="sm" showText={false} />
          </div>

          <p className="hidden sm:block text-sm font-semibold tracking-tight text-ns-primary-dark">
            {portalLabel}
          </p>

          {/* Search */}
          {searchPath && <form onSubmit={submitSearch} className="hidden md:flex items-center gap-2 rounded-xl bg-white border border-ns-border px-4 py-2.5 w-64 lg:w-80 focus-within:ring-2 focus-within:ring-brand-500/30 focus-within:border-brand-500">
            <input value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} aria-label={t('common.search')} placeholder={t('common.search')} className="bg-transparent text-sm text-ink placeholder:text-ink-faint/60 focus:outline-none w-full" />
          </form>}
        </div>

        <div className="flex items-center gap-2 md:gap-3">
          {/* Mobile search */}
          {searchPath && <button
            onClick={() => setSearchOpen((v) => !v)}
            className="md:hidden min-h-11 rounded bg-white border border-ns-border px-3 text-sm text-ns-text-secondary hover:text-brand-800 focus-visible:ring-2 focus-visible:ring-brand-500"
            aria-label={t('common.search')}
            aria-expanded={searchOpen}
            aria-controls="mobile-search-panel"
          >
            Search
          </button>}

          {/* Profile menu */}
          <div className="relative">
            <button
              ref={profileButtonRef}
              onClick={() => setProfileOpen((v) => !v)}
              className="flex items-center gap-2 rounded-xl bg-white border border-ns-border pl-1.5 pr-2.5 py-1.5 hover:bg-ns-surface-secondary transition-colors focus-visible:ring-2 focus-visible:ring-brand-500"
              aria-expanded={profileOpen}
              aria-controls="profile-menu"
              aria-label={`${user.name} profile menu`}
            >
              <div className="w-8 h-8 rounded-lg bg-brand-700 text-white font-bold text-xs flex items-center justify-center">
                {initials(user.name)}
              </div>
              <span className="hidden lg:block text-sm font-semibold text-ink">{user.name}</span>
            </button>

              {profileOpen && (
                <>
                  <button type="button" className="fixed inset-0 z-10 cursor-default" aria-label={t('navigation.closeProfileMenu')} onClick={() => setProfileOpen(false)} />
                  <div
                    id="profile-menu"
                    ref={profileMenuRef}
                    className="absolute right-0 top-14 z-20 w-64 neo-card p-3"
                    onKeyDown={(event) => { if (event.key === 'Escape') { setProfileOpen(false); profileButtonRef.current?.focus(); } }}
                  >
                    <div className="flex items-center gap-3 px-3 py-2 mb-2">
                      <div className="w-11 h-11 rounded-lg bg-brand-700 text-white font-bold flex items-center justify-center">
                        {initials(user.name)}
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-bold text-ink truncate">{user.name}</p>
                        <p className="text-xs text-ink-faint truncate">{user.email}</p>
                      </div>
                    </div>

                    <div className="mx-3 mb-2 rounded border border-ns-border bg-ns-surface-secondary px-2 py-1 text-xs text-ns-text-secondary w-fit">
                      <span className="capitalize">{user.role}</span>
                    </div>

                    <div className="border-t border-ns-divider my-2" />

                    <button
                      onClick={() => { setProfileOpen(false); navigate(preferencesPath); }}
                      className="min-h-11 w-full px-3 py-2.5 rounded text-left text-sm text-ns-text-secondary hover:bg-ns-surface-secondary transition-colors"
                    >
                      {t('navigation.preferences')}
                    </button>

                    {settingsPath && <button
                      onClick={() => {
                        setProfileOpen(false);
                        navigate(settingsPath);
                      }}
                      className="w-full px-3 py-2.5 rounded text-left text-sm text-ns-text-secondary hover:bg-ns-surface-secondary transition-colors"
                    >
                      {t('navigation.settings')}
                    </button>}
                    {user.role === 'student' && <button
                      onClick={() => {
                        setProfileOpen(false);
                        navigate('/student/profile');
                      }}
                      className="w-full px-3 py-2.5 rounded text-left text-sm text-ns-text-secondary hover:bg-ns-surface-secondary transition-colors"
                    >
                      {t('navigation.myProfile')}
                    </button>}
                    <button
                      onClick={handleLogout}
                      className="w-full px-3 py-2.5 rounded text-left text-sm text-ns-danger hover:bg-ns-surface-secondary transition-colors"
                    >
                      {t('navigation.logout')}
                    </button>
                  </div>
                </>
              )}
          </div>
        </div>
      </div>

      {/* Mobile search bar */}
        {searchOpen && (
          <div
            id="mobile-search-panel"
            className="md:hidden overflow-hidden"
          >
            <form onSubmit={submitSearch} className="mt-3 flex items-center gap-2 rounded-lg bg-white border border-ns-border px-4 py-2.5">
              <input
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                aria-label={t('common.search')}
                placeholder={t('common.search')}
                className="bg-transparent text-sm text-ink placeholder:text-ink-faint/60 focus:outline-none w-full"
              />
            </form>
          </div>
        )}
    </header>
  );
}

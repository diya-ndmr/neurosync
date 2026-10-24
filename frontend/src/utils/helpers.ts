export const riskColor = (level: 'LOW' | 'MEDIUM' | 'HIGH'): string => {
  switch (level) {
    case 'LOW':
      return 'var(--ns-success)';
    case 'MEDIUM':
      return 'var(--ns-warning)';
    case 'HIGH':
      return 'var(--ns-danger)';
  }
};

export const riskBg = (level: 'LOW' | 'MEDIUM' | 'HIGH'): string => {
  switch (level) {
    case 'LOW':
      return 'bg-emerald-100 text-emerald-700';
    case 'MEDIUM':
      return 'bg-amber-100 text-amber-700';
    case 'HIGH':
      return 'bg-red-100 text-red-700';
  }
};

export const riskScoreLabel = (score: number): 'LOW' | 'MEDIUM' | 'HIGH' => {
  if (score <= 40) return 'LOW';
  if (score <= 70) return 'MEDIUM';
  return 'HIGH';
};

export const formatDate = (iso?: string): string => {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  });
};

export const timeAgo = (iso: string): string => {
  const seconds = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
  const days = Math.floor(hours / 24);
  return `${days} day${days > 1 ? 's' : ''} ago`;
};

export const greeting = (): string => {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
};

export const initials = (name: string): string =>
  name
    .split(' ')
    .map((n) => n[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();

export const firstName = (name: string): string => name.split(' ')[0];

export const cn = (...classes: (string | false | undefined)[]): string =>
  classes.filter(Boolean).join(' ');


import { cn } from '../../utils/helpers';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  index?: number;
}

const trendColors = {
  up: 'text-emerald-600',
  down: 'text-red-500',
  neutral: 'text-ink-faint'
};

const trendArrows = { up: '↑', down: '↓', neutral: '•' };

export default function StatCard({
  title,
  value,
  subtitle,
  trend = 'neutral',
  trendValue,
}: StatCardProps) {
  return (
    <div className="neo-card p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-ns-text-secondary">{title}</p>
          <p className="mt-1 text-2xl font-semibold text-ns-text-primary">{value}</p>
          {(subtitle || trendValue) && (
            <p className="mt-1 text-xs text-ns-text-muted flex items-center gap-1.5">
              {trendValue && (
                <span className={cn('font-bold', trendColors[trend])}>
                  {trendArrows[trend]} {trendValue}
                </span>
              )}
              {subtitle}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

import { cn } from '@/lib/utils';
import type { Severity } from '@/types';

const config: Record<Severity, { bg: string; text: string; dot: string }> = {
  P1: { bg: 'bg-severity-p1-bg', text: 'text-severity-p1', dot: 'bg-severity-p1' },
  P2: { bg: 'bg-severity-p2-bg', text: 'text-severity-p2', dot: 'bg-severity-p2' },
  P3: { bg: 'bg-severity-info-bg', text: 'text-severity-info', dot: 'bg-severity-info' },
};

export function SeverityBadge({ severity, className }: { severity: Severity; className?: string }) {
  const c = config[severity];
  return (
    <span className={cn('inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold', c.bg, c.text, className)}>
      <span className={cn('w-1.5 h-1.5 rounded-full', c.dot, severity === 'P1' && 'animate-pulse-slow')} />
      {severity}
    </span>
  );
}

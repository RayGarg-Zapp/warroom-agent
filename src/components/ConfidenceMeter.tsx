import { cn } from '@/lib/utils';

interface Props {
  score: number;
  label?: string;
  size?: 'sm' | 'md';
}

export function ConfidenceMeter({ score, label = 'confidence', size = 'md' }: Props) {
  const pct = Math.round(score * 100);
  const color = pct >= 90 ? 'text-severity-success' : pct >= 70 ? 'text-severity-p2' : 'text-severity-p1';

  return (
    <div className={cn('flex items-center gap-1.5', size === 'sm' ? 'text-xs' : 'text-sm')}>
      <div className={cn('relative rounded-full bg-muted overflow-hidden', size === 'sm' ? 'w-8 h-1.5' : 'w-12 h-2')}>
        <div
          className={cn('absolute inset-y-0 left-0 rounded-full', pct >= 90 ? 'bg-severity-success' : pct >= 70 ? 'bg-severity-p2' : 'bg-severity-p1')}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={cn('font-medium tabular-nums', color)}>{pct}%</span>
      {size === 'md' && <span className="text-muted-foreground">{label}</span>}
    </div>
  );
}

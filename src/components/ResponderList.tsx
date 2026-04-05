import type { Responder } from '@/types';
import { cn } from '@/lib/utils';
import { ConfidenceMeter } from './ConfidenceMeter';

const domainColors: Record<string, string> = {
  identity: 'bg-severity-info-bg text-severity-info',
  security: 'bg-severity-p1-bg text-severity-p1',
  cloud: 'bg-severity-p2-bg text-severity-p2',
  application: 'bg-severity-success-bg text-severity-success',
  network: 'bg-muted text-muted-foreground',
  infrastructure: 'bg-muted text-muted-foreground',
};

export function ResponderList({ responders }: { responders: Responder[] }) {
  return (
    <div className="space-y-2">
      {responders.map(r => (
        <div key={r.id} className="flex items-center gap-3 p-3 rounded-lg bg-muted/40 hover:bg-muted/70 transition-colors">
          <div className="w-9 h-9 rounded-full bg-primary/10 flex items-center justify-center text-sm font-semibold text-primary">
            {r.name.split(' ').map(n => n[0]).join('')}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium truncate">{r.name}</span>
              {!r.available && <span className="text-xs text-severity-p2 font-medium">Unavailable</span>}
            </div>
            <p className="text-xs text-muted-foreground">{r.role}</p>
          </div>
          <span className={cn('text-xs font-medium px-2 py-0.5 rounded-full', domainColors[r.domain])}>
            {r.domain}
          </span>
          <ConfidenceMeter score={r.confidence} size="sm" />
        </div>
      ))}
    </div>
  );
}

type StatusBadgeProps = {
  status?: string | null;
};

type RiskBadgeProps = {
  risk?: string | null;
};

const STATUS_STYLES: Record<string, string> = {
  pending: 'bg-yellow-500/10 text-yellow-700 border-yellow-500/20',
  approved: 'bg-blue-500/10 text-blue-700 border-blue-500/20',
  denied: 'bg-red-500/10 text-red-700 border-red-500/20',
  executed: 'bg-green-500/10 text-green-700 border-green-500/20',
  failed: 'bg-red-500/10 text-red-700 border-red-500/20',
  connected: 'bg-green-500/10 text-green-700 border-green-500/20',
  disconnected: 'bg-zinc-500/10 text-zinc-700 border-zinc-500/20',
  error: 'bg-red-500/10 text-red-700 border-red-500/20',
  resolved: 'bg-green-500/10 text-green-700 border-green-500/20',
  in_progress: 'bg-blue-500/10 text-blue-700 border-blue-500/20',
  awaiting_approval: 'bg-yellow-500/10 text-yellow-700 border-yellow-500/20',
  default: 'bg-muted text-muted-foreground border-border',
};

const RISK_STYLES: Record<string, string> = {
  low: 'bg-green-500/10 text-green-700 border-green-500/20',
  medium: 'bg-yellow-500/10 text-yellow-700 border-yellow-500/20',
  high: 'bg-orange-500/10 text-orange-700 border-orange-500/20',
  critical: 'bg-red-500/10 text-red-700 border-red-500/20',
  default: 'bg-muted text-muted-foreground border-border',
};

function normalize(value?: string | null): string {
  if (!value || typeof value !== 'string') return 'default';
  return value.trim().toLowerCase();
}

function formatLabel(value: string): string {
  if (value === 'default') return 'Unknown';
  return value.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const key = normalize(status);
  const className = STATUS_STYLES[key] || STATUS_STYLES.default;
  const label = formatLabel(key);

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${className}`}
    >
      {label}
    </span>
  );
}

export function RiskBadge({ risk }: RiskBadgeProps) {
  const key = normalize(risk);
  const className = RISK_STYLES[key] || RISK_STYLES.default;
  const label = key === 'default' ? 'Unknown Risk' : `${formatLabel(key)} Risk`;

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${className}`}
    >
      {label}
    </span>
  );
}
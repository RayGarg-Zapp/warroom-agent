import type { Incident } from '@/types';
import { SeverityBadge } from './SeverityBadge';
import { StatusBadge } from './StatusBadge';
import { Clock, Hash, Users } from 'lucide-react';
import { Link } from 'react-router-dom';

function timeAgo(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function IncidentCard({ incident }: { incident: Incident }) {
  const pendingActions = incident.plannedActions.filter(a => a.status === 'pending').length;

  return (
    <Link to={`/incidents/${incident.id}`} className="block glass-panel p-5 hover:shadow-md transition-shadow group">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <SeverityBadge severity={incident.severity} />
          <span className="font-mono text-xs text-muted-foreground">{incident.id}</span>
        </div>
        <StatusBadge status={incident.status === 'awaiting_approval' ? 'pending' : incident.status === 'resolved' ? 'executed' : incident.status === 'failed' ? 'failed' : 'approved'} />
      </div>
      <h3 className="font-semibold text-foreground group-hover:text-primary transition-colors mb-2 line-clamp-2">
        {incident.title}
      </h3>
      <p className="text-sm text-muted-foreground line-clamp-2 mb-4">{incident.aiSummary}</p>
      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1"><Hash className="w-3 h-3" />{incident.source}</span>
        <span className="flex items-center gap-1"><Users className="w-3 h-3" />{incident.responders.length} responders</span>
        <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{timeAgo(incident.detectedAt)}</span>
        {pendingActions > 0 && (
          <span className="ml-auto text-status-pending font-medium">{pendingActions} pending</span>
        )}
      </div>
    </Link>
  );
}

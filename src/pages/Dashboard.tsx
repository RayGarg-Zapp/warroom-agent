import { useEffect, useState } from 'react';
import { AppLayout } from '@/components/AppLayout';
import { IncidentCard } from '@/components/IncidentCard';
import { Input } from '@/components/ui/input';
import { AlertTriangle, CheckSquare, Video, Bell, Search } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getIncidents } from '@/lib/api';
import type { Incident } from '@/types';

const filters = ['All', 'P1', 'P2', 'Awaiting Approval', 'In Progress', 'Resolved', 'Failed'] as const;
type Filter = typeof filters[number];

function filterMatch(incident: Incident, filter: Filter) {
  if (filter === 'All') return true;
  if (filter === 'P1') return incident.severity === 'P1';
  if (filter === 'P2') return incident.severity === 'P2';
  if (filter === 'Awaiting Approval') return incident.status === 'awaiting_approval';
  if (filter === 'In Progress') return incident.status === 'in_progress';
  if (filter === 'Resolved') return incident.status === 'resolved';
  if (filter === 'Failed') return incident.status === 'failed';
  return true;
}

export default function DashboardPage() {
  const [filter, setFilter] = useState<Filter>('All');
  const [search, setSearch] = useState('');
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await getIncidents();
      setIncidents(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load incidents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, []);

  const filtered = incidents
    .filter(i => filterMatch(i, filter))
    .filter(i => !search || i.title.toLowerCase().includes(search.toLowerCase()) || i.id.toLowerCase().includes(search.toLowerCase()));

  const activeCount = incidents.filter(i => i.status !== 'resolved').length;
  const pendingApprovals = incidents.flatMap(i => i.plannedActions).filter(a => a.status === 'pending').length;
  const warRooms = incidents.flatMap(i => i.plannedActions).filter(a => a.type === 'zoom_meeting' && a.status === 'executed').length;
  const notifsSent = incidents.flatMap(i => i.plannedActions).filter(a => (a.type === 'slack_dm' || a.type === 'email_notification') && a.status === 'executed').length;

  const summaryCards = [
    { label: 'Active Incidents', value: activeCount, icon: AlertTriangle, color: 'text-severity-p1' },
    { label: 'Pending Approvals', value: pendingApprovals, icon: CheckSquare, color: 'text-status-pending' },
    { label: 'War Rooms Created', value: warRooms, icon: Video, color: 'text-primary' },
    { label: 'Notifications Sent', value: notifsSent, icon: Bell, color: 'text-severity-success' },
  ];

  return (
    <AppLayout>
      <div className="p-6 max-w-6xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold mb-1">Incident Dashboard</h1>
          <p className="text-sm text-muted-foreground">Real-time incident monitoring and coordination.</p>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {summaryCards.map(c => (
            <div key={c.label} className="glass-panel p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-muted-foreground">{c.label}</span>
                <c.icon className={cn('w-4 h-4', c.color)} />
              </div>
              <p className="text-2xl font-bold">{c.value}</p>
            </div>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-3 mb-6">
          <div className="flex items-center gap-1 flex-wrap">
            {filters.map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={cn(
                  'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                  filter === f ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-accent'
                )}
              >
                {f}
              </button>
            ))}
          </div>
          <div className="relative ml-auto">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search incidents..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="pl-9 w-64"
            />
          </div>
        </div>

        {loading && (
          <div className="text-center py-12 text-muted-foreground">Loading incidents...</div>
        )}

        {error && !loading && (
          <div className="text-center py-12 text-red-500">{error}</div>
        )}

        {!loading && !error && (
          <div className="space-y-3">
            {filtered.map(i => <IncidentCard key={i.id} incident={i} />)}
            {filtered.length === 0 && (
              <div className="text-center py-12 text-muted-foreground">No incidents match this filter.</div>
            )}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
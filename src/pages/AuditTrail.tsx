import { useEffect, useMemo, useState } from 'react';
import { AppLayout } from '@/components/AppLayout';
import { AuditTimeline } from '@/components/AuditTimeline';
import { Input } from '@/components/ui/input';
import { Search } from 'lucide-react';
import { getAuditEntries } from '@/lib/api';
import type { AuditEntry } from '@/types';

function safeLower(value: unknown): string {
  return typeof value === 'string' ? value.toLowerCase() : '';
}

export default function AuditTrailPage() {
  const [search, setSearch] = useState('');
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let mounted = true;

    async function load() {
      try {
        setLoading(true);
        setError('');
        const data = await getAuditEntries();
        if (mounted) setEntries(Array.isArray(data) ? data : []);
      } catch (err) {
        if (mounted) setError(err instanceof Error ? err.message : 'Failed to load audit entries');
      } finally {
        if (mounted) setLoading(false);
      }
    }

    load();

    return () => {
      mounted = false;
    };
  }, []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return entries;

    return (Array.isArray(entries) ? entries : []).filter((e: any) => {
      return (
        safeLower(e?.event).includes(q) ||
        safeLower(e?.incidentId).includes(q) ||
        safeLower(e?.actorName).includes(q) ||
        safeLower(e?.targetSystem).includes(q)
      );
    });
  }, [entries, search]);

  return (
    <AppLayout>
      <div className="p-6 max-w-4xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold mb-1">Audit Trail</h1>
          <p className="text-sm text-muted-foreground">
            Complete event log for all incidents and actions.
          </p>
        </div>

        <div className="relative mb-6">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search events, incidents, actors..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>

        {loading && <div className="text-center py-12 text-muted-foreground">Loading audit trail...</div>}
        {error && !loading && <div className="text-center py-12 text-red-500">{error}</div>}

        {!loading && !error && (
          <div className="glass-panel p-6">
            <AuditTimeline entries={filtered} />
            {filtered.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">No matching entries.</div>
            )}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
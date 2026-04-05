import { useEffect, useState } from 'react';
import { AppLayout } from '@/components/AppLayout';
import { ApprovalCard } from '@/components/ApprovalCard';
import { StepUpAuthNotice } from '@/components/StepUpAuthNotice';
import { toast } from 'sonner';
import type { PlannedAction } from '@/types';
import { Shield } from 'lucide-react';
import { cn } from '@/lib/utils';
import { approveAction, denyAction, getAllActions } from '@/lib/api';

const tabs = ['Pending', 'Approved', 'Denied', 'Executed', 'All'] as const;

export default function ApprovalCenterPage() {
  const [actions, setActions] = useState<PlannedAction[]>([]);
  const [tab, setTab] = useState<string>('Pending');
  const [loading, setLoading] = useState(true);
  const [mutating, setMutating] = useState(false);
  const [error, setError] = useState('');

  const loadActions = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await getAllActions();
      setActions(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load actions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadActions();
    const interval = setInterval(loadActions, 5000);
    return () => clearInterval(interval);
  }, []);

  const filtered = tab === 'All' ? actions : actions.filter(a => a.status === tab.toLowerCase());
  const pendingCount = actions.filter(a => a.status === 'pending').length;
  const hasHighRisk = actions.some(a => (a.riskLevel === 'high' || a.riskLevel === 'critical') && a.status === 'pending');

  const handleApprove = async (id: string) => {
    try {
      setMutating(true);
      await approveAction(id);
      toast.success('Action approved');
      await loadActions();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to approve action');
    } finally {
      setMutating(false);
    }
  };

  const handleDeny = async (id: string) => {
    try {
      setMutating(true);
      await denyAction(id);
      toast.error('Action denied');
      await loadActions();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to deny action');
    } finally {
      setMutating(false);
    }
  };

  return (
    <AppLayout>
      <div className="p-6 max-w-5xl mx-auto">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold mb-1">Approval Center</h1>
            <p className="text-sm text-muted-foreground">Review and authorize AI-proposed actions.</p>
          </div>
          {pendingCount > 0 && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-status-pending-bg text-status-pending text-sm font-semibold">
              <Shield className="w-4 h-4" />
              {pendingCount} pending
            </div>
          )}
        </div>

        {hasHighRisk && <div className="mb-6"><StepUpAuthNotice /></div>}

        <div className="flex items-center gap-1 mb-6">
          {tabs.map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                tab === t ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-accent'
              )}
            >
              {t}
            </button>
          ))}
        </div>

        {loading && <div className="text-center py-12 text-muted-foreground">Loading actions...</div>}
        {error && !loading && <div className="text-center py-12 text-red-500">{error}</div>}

        {!loading && !error && (
          <div className="space-y-3">
            {filtered.map(a => (
              <ApprovalCard
                key={a.id}
                action={a}
                onApprove={handleApprove}
                onDeny={handleDeny}
                disabled={mutating}
              />
            ))}
            {filtered.length === 0 && <div className="text-center py-12 text-muted-foreground">No actions in this category.</div>}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
import type { PlannedAction } from '@/types';
import { StatusBadge, RiskBadge } from './StatusBadge';
import { SecurityScopePill } from './SecurityScopePill';
import { Button } from './ui/button';
import { Check, X, Video, Calendar, MessageSquare, Mail, Github, Play } from 'lucide-react';
import { motion } from 'framer-motion';

const actionIcons: Record<string, React.ElementType> = {
  zoom_meeting: Video,
  calendar_event: Calendar,
  slack_dm: MessageSquare,
  email_notification: Mail,
  github_app_repo_update: Github,
  github_network_repo_update: Github,
};

interface Props {
  action: PlannedAction;
  onApprove?: (id: string) => void;
  onDeny?: (id: string) => void;
  onExecute?: (id: string) => void;
  disabled?: boolean;
  busy?: boolean;
  statusMessage?: string;
}

function isGitHubRemediation(type: string): boolean {
  return type === 'github_app_repo_update' || type === 'github_network_repo_update';
}

export function ApprovalCard({
  action,
  onApprove,
  onDeny,
  onExecute,
  disabled,
  busy,
  statusMessage,
}: Props) {
  const Icon = actionIcons[action.type] || MessageSquare;
  const isPending = action.status === 'pending';
  const isApproved = action.status === 'approved';
  const isExecutionPending = !action.executionStatus || action.executionStatus === 'pending';
  const githubRemediation = isGitHubRemediation(action.type);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-panel p-5"
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
            <Icon className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h4 className="font-semibold text-sm">{action.title}</h4>
            <p className="text-xs text-muted-foreground">{action.provider}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <RiskBadge level={action.riskLevel} />
          <StatusBadge status={action.status} />
        </div>
      </div>

      <p className="text-sm text-muted-foreground mb-3">{action.description}</p>

      <div className="flex flex-wrap gap-1.5 mb-3">
        {action.scopesUsed.map(s => <SecurityScopePill key={s} scope={s} />)}
      </div>

      <div className="text-xs text-muted-foreground mb-4">
        <span className="font-medium">
          {githubRemediation ? 'Target:' : 'Recipients:'}
        </span>{' '}
        {action.recipients.join(', ')}
      </div>

      {githubRemediation && (
        <div className="text-xs text-muted-foreground mb-4 p-2 rounded-md bg-muted/40">
          Sensitive GitHub remediation stays separate from workflow approval. Execution uses external privileged authorization first, then the existing Token Vault path.
        </div>
      )}

      {statusMessage && (
        <div className="text-xs text-muted-foreground mb-4 p-2 rounded-md bg-muted/40">
          {statusMessage}
        </div>
      )}

      {isPending && (
        <div className="flex items-center gap-2 pt-3 border-t border-border">
          <Button
            size="sm"
            onClick={() => onApprove?.(action.id)}
            disabled={disabled}
            className="gap-1.5 bg-severity-success hover:bg-severity-success/90 text-severity-success-bg"
          >
            <Check className="w-3.5 h-3.5" /> Approve
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => onDeny?.(action.id)}
            disabled={disabled}
            className="gap-1.5 text-severity-p1 border-severity-p1/30 hover:bg-severity-p1-bg"
          >
            <X className="w-3.5 h-3.5" /> Deny
          </Button>
          {action.riskLevel === 'high' || action.riskLevel === 'critical' ? (
            <span className="ml-auto text-xs text-status-pending font-medium">⚠ Step-up auth may be required</span>
          ) : null}
        </div>
      )}

      {isApproved && githubRemediation && isExecutionPending && (
        <div className="flex items-center gap-2 pt-3 border-t border-border">
          <Button
            size="sm"
            onClick={() => onExecute?.(action.id)}
            disabled={disabled}
            className="gap-1.5"
          >
            <Play className="w-3.5 h-3.5" />
            {busy ? 'Waiting For Approval...' : 'Execute Remediation'}
          </Button>
          <span className="ml-auto text-xs text-muted-foreground">
            Run individually with the correct linked operator account.
          </span>
        </div>
      )}
    </motion.div>
  );
}

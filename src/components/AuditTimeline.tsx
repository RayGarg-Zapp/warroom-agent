import { useState } from 'react';
import type { AuditEntry } from '@/types';
import { StatusBadge } from './StatusBadge';
import {
  Bot, User, Cog, Plug, ShieldAlert,
  ChevronDown, ChevronRight, Copy, Check,
  Radio, Brain, Users, BookOpen, Zap, Play, Flag, MessageSquare,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';

// Map stage names from details_json to icons and colors
const stageConfig: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  ingest: { icon: Radio, color: 'text-blue-400', label: 'Ingestion' },
  classify: { icon: Brain, color: 'text-purple-400', label: 'AI Classification' },
  resolve_responders: { icon: Users, color: 'text-cyan-400', label: 'Responder Selection' },
  known_issue_match: { icon: BookOpen, color: 'text-yellow-400', label: 'Knowledge Base' },
  plan_actions: { icon: Zap, color: 'text-orange-400', label: 'Action Planning' },
  execute: { icon: Play, color: 'text-green-400', label: 'Execution' },
  finalize: { icon: Flag, color: 'text-emerald-400', label: 'Finalized' },
  chat: { icon: MessageSquare, color: 'text-indigo-400', label: 'AI Chat' },
};

const actorIcons: Record<string, React.ElementType> = {
  ai_agent: Bot,
  human: User,
  system: Cog,
  integration: Plug,
  operator: ShieldAlert,
};

function safeString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback;
}

function formatTime(ts: string) {
  const date = new Date(ts);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function formatDate(ts: string) {
  const date = new Date(ts);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function CopyBtn({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button onClick={handleCopy} className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors" title="Copy">
      {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
    </button>
  );
}

function DetailValue({ label, value }: { label: string; value: string | number | undefined | null }) {
  if (value === undefined || value === null || value === '') return null;
  return (
    <div className="flex items-start gap-2 text-xs">
      <span className="text-muted-foreground font-medium min-w-[100px]">{label}:</span>
      <span className="text-foreground">{String(value)}</span>
    </div>
  );
}

function CodeBlock({ code, lang }: { code: string; lang?: string }) {
  return (
    <div className="relative mt-1 group">
      <pre className="bg-muted/40 p-2 rounded text-[11px] font-mono overflow-x-auto whitespace-pre-wrap">
        <code>{code}</code>
      </pre>
      <div className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <CopyBtn text={code} />
      </div>
    </div>
  );
}

function renderDetailContent(metadata: Record<string, any>) {
  const stage = metadata?.stage;
  const description = metadata?.description;

  return (
    <div className="space-y-2 mt-2">
      {description && (
        <p className="text-xs text-muted-foreground italic">{description}</p>
      )}

      {/* Ingest stage */}
      {stage === 'ingest' && metadata.raw_message && (
        <div>
          <p className="text-[11px] font-medium text-muted-foreground mb-1">Original Message</p>
          <CodeBlock code={metadata.raw_message} />
        </div>
      )}

      {/* Classify stage */}
      {stage === 'classify' && (
        <div className="space-y-1.5">
          <DetailValue label="Severity" value={metadata.severity} />
          <DetailValue label="Confidence" value={metadata.confidence != null ? `${(metadata.confidence * 100).toFixed(0)}%` : undefined} />
          <DetailValue label="Title" value={metadata.title} />
          <DetailValue label="Summary" value={metadata.summary} />
          <DetailValue label="Reasoning" value={metadata.severity_reasoning} />
          {metadata.probable_domains?.length > 0 && (
            <DetailValue label="Domains" value={metadata.probable_domains.join(', ')} />
          )}
          {metadata.impacted_systems?.length > 0 && (
            <DetailValue label="Systems" value={metadata.impacted_systems.join(', ')} />
          )}
        </div>
      )}

      {/* Responder stage */}
      {stage === 'resolve_responders' && metadata.responders && (
        <div className="space-y-1">
          <p className="text-[11px] font-medium text-muted-foreground">Selected Responders</p>
          {metadata.responders.map((r: any, i: number) => (
            <div key={i} className="text-xs bg-muted/30 rounded px-2 py-1.5 flex items-center justify-between">
              <div>
                <span className="font-medium">{r.name}</span>
                <span className="text-muted-foreground"> — {r.role} ({r.domain})</span>
              </div>
              {r.confidence != null && (
                <span className="text-[10px] text-muted-foreground">{(r.confidence * 100).toFixed(0)}% match</span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Known issue match stage */}
      {stage === 'known_issue_match' && metadata.matches && (
        <div className="space-y-1">
          <p className="text-[11px] font-medium text-muted-foreground">Matched Issues</p>
          {metadata.matches.map((m: any, i: number) => (
            <div key={i} className="text-xs bg-muted/30 rounded px-2 py-1.5">
              <div className="flex items-center justify-between">
                <span className="font-medium">{m.title}</span>
                {m.match_score != null && (
                  <span className="text-[10px] text-muted-foreground">{(m.match_score * 100).toFixed(0)}% match</span>
                )}
              </div>
              {m.matched_symptoms?.length > 0 && (
                <p className="text-muted-foreground mt-0.5">Symptoms: {m.matched_symptoms.join(', ')}</p>
              )}
              {m.recommended_actions?.length > 0 && (
                <p className="text-muted-foreground mt-0.5">Actions: {m.recommended_actions.join(', ')}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Action plan stage */}
      {stage === 'plan_actions' && metadata.actions && (
        <div className="space-y-1">
          <p className="text-[11px] font-medium text-muted-foreground">Proposed Actions</p>
          {metadata.actions.map((a: any, i: number) => (
            <div key={i} className="text-xs bg-muted/30 rounded px-2 py-1.5">
              <div className="flex items-center justify-between">
                <span className="font-medium">{a.title}</span>
                <span className={cn(
                  'text-[10px] px-1.5 py-0.5 rounded',
                  a.risk_level === 'high' || a.risk_level === 'critical'
                    ? 'bg-red-500/10 text-red-400'
                    : 'bg-green-500/10 text-green-400'
                )}>
                  {a.risk_level}
                </span>
              </div>
              <p className="text-muted-foreground mt-0.5">{a.description}</p>
              {a.recipients?.length > 0 && (
                <p className="text-muted-foreground mt-0.5">Recipients: {a.recipients.join(', ')}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Execution stage */}
      {stage === 'execute' && (
        <div className="space-y-1">
          <div className="flex gap-3 text-xs">
            <span className="text-green-400">Succeeded: {metadata.succeeded || 0}</span>
            <span className="text-red-400">Failed: {metadata.failed || 0}</span>
          </div>
          {metadata.results && (
            <CodeBlock code={JSON.stringify(metadata.results, null, 2)} lang="json" />
          )}
        </div>
      )}

      {/* Chat stage */}
      {stage === 'chat' && (
        <div className="space-y-1.5">
          {metadata.user_message && (
            <div>
              <p className="text-[11px] font-medium text-muted-foreground">Operator Question</p>
              <div className="text-xs bg-primary/10 rounded px-2 py-1.5 mt-0.5">{metadata.user_message}</div>
            </div>
          )}
          {metadata.ai_reply && (
            <div>
              <p className="text-[11px] font-medium text-muted-foreground">AI Response</p>
              <CodeBlock code={metadata.ai_reply} />
            </div>
          )}
          {metadata.model && (
            <DetailValue label="Model" value={metadata.model} />
          )}
        </div>
      )}

      {/* Finalize stage */}
      {stage === 'finalize' && (
        <div className="space-y-1">
          <DetailValue label="Incident" value={metadata.incident_id} />
          <DetailValue label="Final Severity" value={metadata.final_severity} />
          <DetailValue label="Responders" value={metadata.responder_count} />
          <DetailValue label="Actions" value={metadata.action_count} />
        </div>
      )}

      {/* Approval/denial details (from actions API) */}
      {!stage && metadata.approvedBy && (
        <DetailValue label="Approved by" value={`${metadata.approvedBy} (${metadata.approvedByEmail || ''})`} />
      )}
      {!stage && metadata.deniedBy && (
        <DetailValue label="Denied by" value={`${metadata.deniedBy} (${metadata.deniedByEmail || ''})`} />
      )}
      {!stage && metadata.result && (
        <div>
          <p className="text-[11px] font-medium text-muted-foreground">Execution Result</p>
          <CodeBlock code={JSON.stringify(metadata.result, null, 2)} lang="json" />
        </div>
      )}
    </div>
  );
}

function AuditEntryRow({ entry, index, total }: { entry: any; index: number; total: number }) {
  const [expanded, setExpanded] = useState(false);

  const actorType = safeString(entry?.actorType, 'system') as keyof typeof actorIcons;
  const event = safeString(entry?.event, 'Unknown event');
  const timestamp = safeString(entry?.timestamp, '');
  const actorName = safeString(entry?.actorName, 'Unknown');
  const targetSystem = safeString(entry?.targetSystem, '');
  const executionStatus = safeString(entry?.executionStatus, '');
  const approvalStatus = safeString(entry?.approvalStatus, '');
  const metadata = entry?.metadata;
  const stage = metadata?.stage;

  const stageInfo = stage ? stageConfig[stage] : null;
  const StageIcon = stageInfo?.icon || actorIcons[actorType] || Cog;
  const iconColor = stageInfo?.color || 'text-muted-foreground';
  const hasDetails = metadata && Object.keys(metadata).length > 0;

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.03 }}
      className="relative flex gap-3 pb-4 last:pb-0"
    >
      {index < total - 1 && (
        <div className="absolute left-[15px] top-9 bottom-0 w-px bg-border" />
      )}

      <div className={cn(
        'w-[30px] h-[30px] rounded-full flex items-center justify-center shrink-0 z-10',
        stageInfo ? 'bg-muted/80' : 'bg-muted',
      )}>
        <StageIcon className={cn('w-3.5 h-3.5', iconColor)} />
      </div>

      <div className="flex-1 min-w-0">
        <div
          className={cn(
            'flex items-start justify-between gap-2',
            hasDetails && 'cursor-pointer'
          )}
          onClick={() => hasDetails && setExpanded(!expanded)}
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5">
              {stageInfo && (
                <span className={cn('text-[10px] font-bold uppercase tracking-wider', iconColor)}>
                  {stageInfo.label}
                </span>
              )}
            </div>
            <p className="text-xs font-medium break-words mt-0.5">{event}</p>

            <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 mt-1">
              <span className="text-[10px] text-muted-foreground">
                {formatDate(timestamp)} {formatTime(timestamp)}
              </span>
              <span className="text-[10px] text-muted-foreground">· {actorName}</span>
              {targetSystem && (
                <span className="text-[10px] text-muted-foreground">→ {targetSystem}</span>
              )}
              {executionStatus && <StatusBadge status={executionStatus} />}
              {!executionStatus && approvalStatus && <StatusBadge status={approvalStatus} />}
            </div>
          </div>

          {hasDetails && (
            <div className="mt-1 text-muted-foreground">
              {expanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
            </div>
          )}
        </div>

        <AnimatePresence>
          {expanded && hasDetails && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <div className="mt-2 pl-2 border-l-2 border-border/50">
                {renderDetailContent(metadata)}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

export function AuditTimeline({ entries }: { entries: AuditEntry[] }) {
  const safeEntries = Array.isArray(entries) ? entries : [];

  if (safeEntries.length === 0) {
    return <div className="text-sm text-muted-foreground">No audit entries yet.</div>;
  }

  return (
    <div className="space-y-0">
      {safeEntries.map((entry: any, i) => (
        <AuditEntryRow
          key={safeString(entry?.id, `entry-${i}`)}
          entry={entry}
          index={i}
          total={safeEntries.length}
        />
      ))}
    </div>
  );
}

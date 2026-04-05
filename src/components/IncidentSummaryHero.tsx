import type { Incident } from '@/types';
import { SeverityBadge } from './SeverityBadge';
import { ConfidenceMeter } from './ConfidenceMeter';
import { Bot, Clock, Hash, Server } from 'lucide-react';

export function IncidentSummaryHero({ incident }: { incident: Incident }) {
  return (
    <div className="glass-panel p-6">
      <div className="flex flex-wrap items-center gap-3 mb-3">
        <SeverityBadge severity={incident.severity} />
        <span className="font-mono text-xs text-muted-foreground">{incident.id}</span>
        <span className="flex items-center gap-1 text-xs text-muted-foreground"><Hash className="w-3 h-3" />{incident.source}</span>
        <span className="flex items-center gap-1 text-xs text-muted-foreground"><Clock className="w-3 h-3" />{new Date(incident.detectedAt).toLocaleString()}</span>
      </div>
      <h1 className="text-xl font-bold mb-4">{incident.title}</h1>

      {/* Original Slack message */}
      <div className="p-4 rounded-lg bg-muted/50 border-l-4 border-primary mb-4">
        <p className="text-xs font-medium text-muted-foreground mb-1">Original Slack Message</p>
        <p className="text-sm">{incident.slackMessage}</p>
      </div>

      {/* AI Summary */}
      <div className="ai-surface rounded-lg p-4 mb-4">
        <div className="flex items-center gap-2 mb-2">
          <Bot className="w-4 h-4 text-ai-accent" />
          <span className="text-xs font-semibold text-ai-accent">AI Analysis</span>
          <ConfidenceMeter score={incident.confidenceScore} />
        </div>
        <p className="text-sm">{incident.aiSummary}</p>
      </div>

      {/* Severity reasoning */}
      <div className="p-4 rounded-lg bg-muted/30">
        <p className="text-xs font-medium text-muted-foreground mb-1">Classification Reasoning</p>
        <p className="text-sm">{incident.severityReasoning}</p>
      </div>

      {/* Impacted systems */}
      <div className="mt-4">
        <p className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1.5"><Server className="w-3 h-3" />Impacted Systems</p>
        <div className="flex flex-wrap gap-1.5">
          {incident.impactedSystems.map(s => (
            <span key={s} className="px-2.5 py-1 rounded-md bg-severity-p1-bg text-severity-p1 text-xs font-medium">{s}</span>
          ))}
        </div>
      </div>
    </div>
  );
}

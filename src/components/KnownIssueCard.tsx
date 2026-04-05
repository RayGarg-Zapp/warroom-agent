import type { KnownIssue } from '@/types';
import { ConfidenceMeter } from './ConfidenceMeter';
import { BookOpen, Clock } from 'lucide-react';

export function KnownIssueCard({ issue }: { issue: KnownIssue }) {
  return (
    <div className="ai-surface rounded-lg p-4">
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-ai-accent" />
          <h4 className="text-sm font-semibold">{issue.title}</h4>
        </div>
        <ConfidenceMeter score={issue.matchScore} label="match" />
      </div>
      <p className="text-sm text-muted-foreground mb-3">{issue.description}</p>
      <div className="p-3 rounded-md bg-card border border-border">
        <p className="text-xs font-medium text-foreground mb-1">Suggested Resolution</p>
        <p className="text-xs text-muted-foreground">{issue.resolution}</p>
      </div>
      <div className="flex items-center gap-1.5 mt-2 text-xs text-muted-foreground">
        <Clock className="w-3 h-3" />
        Last occurred: {issue.lastOccurrence}
      </div>
    </div>
  );
}

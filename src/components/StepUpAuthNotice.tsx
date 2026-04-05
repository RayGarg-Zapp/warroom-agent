import { ShieldAlert } from 'lucide-react';

export function StepUpAuthNotice() {
  return (
    <div className="flex items-start gap-3 p-4 rounded-lg bg-severity-p2-bg border border-severity-p2/20">
      <ShieldAlert className="w-5 h-5 text-severity-p2 mt-0.5 shrink-0" />
      <div>
        <p className="text-sm font-semibold text-severity-p2">Privileged Authorization Required</p>
        <p className="text-xs text-muted-foreground mt-0.5">High-risk actions require a second privileged authorization step before execution. Depending on the action, that may happen through redirect-based step-up or external backchannel approval.</p>
      </div>
    </div>
  );
}

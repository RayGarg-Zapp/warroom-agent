import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AppLayout } from '@/components/AppLayout';
import { Button } from '@/components/ui/button';
import { Zap, Play } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { injectIncident } from '@/lib/api';

const sampleIncidents = [
  {
    label: 'P1 — North America Login Outage',
    value: 'p1-login-outage',
    payload: {
      slackMessage:
        "P1 incident: users across North America cannot log in to the customer portal after this morning's IAM certificate update. MFA also appears impacted for some tenants. Multiple enterprise customers reporting outage.",
      source: '#incidents-prod',
    },
  },
  {
    label: 'P2 — EU Payment Latency',
    value: 'p2-payment-latency',
    payload: {
      slackMessage:
        'P2: EU payment gateway latency is 4x normal. Checkout completion rates dropping. No errors yet but trending toward SLA breach.',
      source: '#incidents-prod',
    },
  },
  {
    label: 'P2 — CDN Cache Stale Assets',
    value: 'p2-cdn-cache',
    payload: {
      slackMessage:
        "P2: CDN cache invalidation not propagating. Users seeing old static assets after deploy. Marketing launch page showing yesterday's content.",
      source: '#incidents-prod',
    },
  },
  {
    label: 'P1 — Suspicious Admin Activity',
    value: 'p1-suspicious-admin',
    payload: {
      slackMessage:
        'P1 security incident: suspicious admin activity detected after a privileged support session. Multiple enterprise tenants report forced MFA resets and anomalous login failures. Possible misuse of identity admin privileges or support workflow token.',
      source: '#incidents-prod',
    },
  },
  {
    label: 'P1 — Config Drift Outage (Port 81 vs Policy 80)',
    value: 'p1-config-drift-port-mismatch',
    payload: {
      slackMessage:
        'P1 incident: customer portal outage after application config drift. Service now listens on port 81, but network policy still permits only port 80. Requests are timing out across production.',
      source: '#incidents-prod',
    },
  },
];

export default function DemoConsolePage() {
  const [selected, setSelected] = useState(sampleIncidents[0].value);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleInject = async () => {
    const selectedIncident = sampleIncidents.find((s) => s.value === selected);
    if (!selectedIncident) return;

    try {
      setLoading(true);
      const incident = await injectIncident(selectedIncident.payload);
      toast.success('Incident injected — redirecting to detail view...');
      navigate(`/incidents/${incident.id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to inject incident');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppLayout>
      <div className="p-6 max-w-2xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
            <Zap className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Demo Console</h1>
            <p className="text-sm text-muted-foreground">
              Inject a seed incident to demonstrate the full workflow.
            </p>
          </div>
        </div>

        <div className="glass-panel p-6 space-y-6">
          <div>
            <label className="text-sm font-medium mb-3 block">Select Sample Incident</label>
            <div className="space-y-2">
              {sampleIncidents.map((s) => (
                <button
                  key={s.value}
                  onClick={() => setSelected(s.value)}
                  className={cn(
                    'w-full text-left px-4 py-3 rounded-lg border transition-colors text-sm',
                    selected === s.value
                      ? 'border-primary bg-primary/5 font-medium'
                      : 'border-border hover:bg-muted/50'
                  )}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          <Button onClick={handleInject} size="lg" className="w-full gap-2" disabled={loading}>
            <Play className="w-4 h-4" />
            {loading ? 'Injecting…' : 'Inject Incident & View'}
          </Button>
        </div>
      </div>
    </AppLayout>
  );
}
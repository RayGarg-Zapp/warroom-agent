import { AppLayout } from '@/components/AppLayout';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Settings, Hash, AlertTriangle, Users, BookOpen, Clock, Mail } from 'lucide-react';

const sections = [
  {
    icon: Hash,
    title: 'Monitored Slack Channel',
    fields: [{ label: 'Channel Name', value: '#incidents-prod' }, { label: 'Workspace', value: 'acme-corp.slack.com' }],
  },
  {
    icon: AlertTriangle,
    title: 'Severity Keywords',
    fields: [{ label: 'P1 Keywords', value: 'outage, down, critical, emergency' }, { label: 'P2 Keywords', value: 'degraded, slow, latency, elevated' }],
  },
  {
    icon: Users,
    title: 'Responder Directory',
    fields: [{ label: 'Directory Source', value: 'PagerDuty + Internal LDAP' }, { label: 'Auto-refresh', value: 'Every 6 hours' }],
  },
  {
    icon: BookOpen,
    title: 'Known Issue Catalog',
    fields: [{ label: 'Catalog Source', value: 'Confluence Knowledge Base' }, { label: 'Match Threshold', value: '70%' }],
  },
  {
    icon: Clock,
    title: 'Default Settings',
    fields: [{ label: 'War Room Duration', value: '60 minutes' }, { label: 'Calendar Buffer', value: '5 minutes' }],
  },
  {
    icon: Mail,
    title: 'Notification Templates',
    fields: [{ label: 'P1 Template', value: 'p1-executive-briefing' }, { label: 'P2 Template', value: 'p2-team-notification' }],
  },
];

export default function AdminPage() {
  return (
    <AppLayout>
      <div className="p-6 max-w-4xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <Settings className="w-6 h-6 text-primary" />
          <div>
            <h1 className="text-2xl font-bold">Configuration</h1>
            <p className="text-sm text-muted-foreground">Manage agent behavior, responders, and integrations.</p>
          </div>
        </div>

        <div className="space-y-4">
          {sections.map(s => (
            <div key={s.title} className="glass-panel p-5">
              <div className="flex items-center gap-2 mb-4">
                <s.icon className="w-4 h-4 text-primary" />
                <h2 className="font-semibold">{s.title}</h2>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {s.fields.map(f => (
                  <div key={f.label}>
                    <label className="text-xs font-medium text-muted-foreground mb-1.5 block">{f.label}</label>
                    <Input defaultValue={f.value} className="text-sm" />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="flex justify-end mt-6">
          <Button className="px-6">Save Configuration</Button>
        </div>
      </div>
    </AppLayout>
  );
}

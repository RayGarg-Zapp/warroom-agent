import type { IntegrationConnection } from '@/types';
import { SecurityScopePill } from './SecurityScopePill';
import { Button } from './ui/button';
import {
  CheckCircle2,
  XCircle,
  AlertCircle,
  Settings,
  MessageSquare,
  Video,
  Calendar,
  Mail,
  Shield,
  PlugZap,
  RefreshCw,
  Loader2,
  Github,
} from 'lucide-react';
import { toast } from 'sonner';

const icons: Record<string, React.ElementType> = {
  MessageSquare,
  Video,
  Calendar,
  Mail,
  Shield,
  Github,
};

const statusUI = {
  connected: { icon: CheckCircle2, color: 'text-severity-success', label: 'Connected' },
  disconnected: { icon: XCircle, color: 'text-muted-foreground', label: 'Disconnected' },
  error: { icon: AlertCircle, color: 'text-severity-p1', label: 'Error' },
};

type Props = {
  connection: IntegrationConnection;
  busy?: boolean;
  onConnect?: (connection: IntegrationConnection) => Promise<void> | void;
  onRefresh?: () => Promise<void> | void;
};

function isVaultBackedProvider(provider: string): boolean {
  const normalized = provider.trim().toLowerCase();
  return (
    normalized === 'slack' ||
    normalized === 'google calendar' ||
    normalized === 'google' ||
    normalized === 'github'
  );
}

export function IntegrationStatusCard({ connection, busy = false, onConnect, onRefresh }: Props) {
  const Icon = icons[connection.icon] || Shield;
  const s = statusUI[connection.status] || statusUI.disconnected;
  const SIcon = s.icon;

  const isVaultBacked = isVaultBackedProvider(connection.provider);

  const handlePrimaryAction = async () => {
    if (isVaultBacked && onConnect) {
      await onConnect(connection);
      return;
    }

    toast.info('System-owned integration is managed through secure admin configuration in this MVP.');
  };

  const helperText = isVaultBacked
    ? 'Token Vault requires this signed-in operator to complete a linked connected-account consent flow before delegated tool calls will succeed.'
    : connection.securityNote || 'Integration managed through secure admin configuration.';

  const primaryLabel = isVaultBacked
    ? connection.status === 'connected'
      ? 'Re-consent'
      : 'Connect'
    : 'Manage';

  return (
    <div className="glass-panel p-5">
      <div className="flex items-start justify-between mb-4 gap-3">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-lg bg-primary/10 flex items-center justify-center">
            <Icon className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h3 className="font-semibold">{connection.provider}</h3>
            <div className="flex items-center gap-1.5 mt-0.5">
              <SIcon className={`w-3.5 h-3.5 ${s.color}`} />
              <span className={`text-xs font-medium ${s.color}`}>{s.label}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isVaultBacked && (
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs"
              onClick={handlePrimaryAction}
              disabled={busy}
            >
              {busy ? <Loader2 className="w-3 h-3 animate-spin" /> : <PlugZap className="w-3 h-3" />}
              {primaryLabel}
            </Button>
          )}

          <Button
            variant="outline"
            size="sm"
            className="gap-1.5 text-xs"
            onClick={async () => {
              if (onRefresh) {
                await onRefresh();
              } else {
                toast.info('Refresh not available yet.');
              }
            }}
            disabled={busy}
          >
            <RefreshCw className="w-3 h-3" />
            Refresh
          </Button>

          {!isVaultBacked && (
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs"
              onClick={handlePrimaryAction}
              disabled={busy}
            >
              <Settings className="w-3 h-3" />
              Manage
            </Button>
          )}
        </div>
      </div>

      <div className="space-y-3">
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-1.5">Scopes Granted</p>
          <div className="flex flex-wrap gap-1.5">
            {connection.scopesGranted.map((scope) => (
              <SecurityScopePill key={scope} scope={scope} />
            ))}
          </div>
        </div>

        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>Last used: {connection.lastUsed}</span>
        </div>

        <div className="flex items-start gap-1.5 p-2.5 rounded-md bg-muted/50">
          <Shield className="w-3.5 h-3.5 text-muted-foreground mt-0.5 shrink-0" />
          <p className="text-xs text-muted-foreground">{helperText}</p>
        </div>
      </div>
    </div>
  );
}
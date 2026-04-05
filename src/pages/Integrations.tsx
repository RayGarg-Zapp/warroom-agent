import { useEffect, useMemo, useState } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import { AppLayout } from '@/components/AppLayout';
import { IntegrationStatusCard } from '@/components/IntegrationStatusCard';
import { Shield } from 'lucide-react';
import { getIntegrations } from '@/lib/api';
import { listConnectedAccounts } from '@/lib/myAccount';
import { toast } from 'sonner';
import type { IntegrationConnection } from '@/types';

type BackendIntegration = {
  id: string;
  providerName: string;
  icon?: string;
  connectionStatus: string;
  scopes: string[];
  lastUsedAt: string | null;
  securityNote?: string;
};

type UiStatus = 'connected' | 'disconnected' | 'error';

function normalizeStatus(value: string): UiStatus {
  if (value === 'connected' || value === 'disconnected' || value === 'error') {
    return value;
  }
  return 'disconnected';
}

function normalizeIntegration(raw: BackendIntegration): IntegrationConnection {
  return {
    id: raw.id,
    provider: raw.providerName,
    icon: raw.icon || 'Shield',
    status: normalizeStatus(raw.connectionStatus),
    scopesGranted: Array.isArray(raw.scopes) ? raw.scopes : [],
    lastUsed: raw.lastUsedAt ? new Date(raw.lastUsedAt).toLocaleString() : 'Not yet used',
    securityNote: raw.securityNote || '',
  };
}

function getVaultConnectionName(provider: string): string | null {
  const normalized = provider.trim().toLowerCase();

  if (normalized === 'google calendar' || normalized === 'google') {
    return 'google-oauth2';
  }

  if (normalized === 'slack') {
    return 'sign-in-with-slack';
  }

  if (normalized === 'github') {
    return 'github';
  }

  return null;
}

function isVaultBacked(provider: string): boolean {
  return getVaultConnectionName(provider) !== null;
}

export default function IntegrationsPage() {
  const {
    isAuthenticated,
    isLoading,
    getAccessTokenWithPopup,
    connectAccountWithRedirect,
  } = useAuth0();

  const [integrations, setIntegrations] = useState<IntegrationConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState<string | null>(null);
  const [checkingConnections, setCheckingConnections] = useState(false);
  const [connectedAccounts, setConnectedAccounts] = useState<any[]>([]);

  const auth0Domain = useMemo(() => {
    const raw = import.meta.env.VITE_AUTH0_DOMAIN as string | undefined;
    if (!raw) return '';
    return raw.replace(/^https?:\/\//, '').replace(/\/+$/, '');
  }, []);

  const loadBackendIntegrations = async () => {
    const data = await getIntegrations();
    const normalized = Array.isArray(data)
      ? (data as BackendIntegration[]).map(normalizeIntegration)
      : [];
    return normalized;
  };

  const enrichWithConnectedAccounts = (
    backendRows: IntegrationConnection[],
    accounts: any[]
  ): IntegrationConnection[] => {
    return backendRows.map((row) => {
      const connectionName = getVaultConnectionName(row.provider);

      if (!connectionName) {
        return row;
      }

      const hasLinkedAccount = accounts.some((account: any) => {
        const providerConnection =
          account?.connection ||
          account?.provider ||
          account?.name;

        return providerConnection === connectionName;
      });

      return {
        ...row,
        status: hasLinkedAccount ? 'connected' : 'disconnected',
        securityNote: hasLinkedAccount
          ? `${row.provider} is linked for this operator through Connected Accounts and Token Vault.`
          : `${row.provider} still needs a linked Connected Account for this operator before delegated Token Vault actions will succeed.`,
      };
    });
  };

  const loadBackendOnly = async () => {
    try {
      setLoading(true);
      setError('');
      const backendRows = await loadBackendIntegrations();
      setIntegrations(backendRows);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load integrations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!isLoading) {
      loadBackendOnly();
    }
  }, [isLoading]);

  const getMyAccountToken = async (forceConsent = false) => {
    const token = await getAccessTokenWithPopup({
      authorizationParams: {
        audience: `https://${auth0Domain}/me/`,
        scope:
          'read:me:connected_accounts create:me:connected_accounts delete:me:connected_accounts',
        ...(forceConsent ? { prompt: 'consent' } : {}),
      },
    });

    if (!token) {
      throw new Error('No My Account API token was returned.');
    }

    return token;
  };

  const handleCheckLinkedAccounts = async () => {
    if (!auth0Domain || !isAuthenticated) {
      toast.error('You must be signed in first.');
      return;
    }

    try {
      setCheckingConnections(true);

      const popupTokenGetter = async () => getMyAccountToken(false);

      const accounts = await listConnectedAccounts({
        domain: auth0Domain,
        getAccessTokenSilently: popupTokenGetter,
      });

      setConnectedAccounts(accounts);
      setIntegrations((current) => enrichWithConnectedAccounts(current, accounts));

      toast.success(
        accounts.length > 0
          ? `Found ${accounts.length} linked connected account(s).`
          : 'No linked connected accounts found yet.'
      );
    } catch (err) {
      toast.error(
        err instanceof Error
          ? err.message
          : 'Failed to check linked accounts'
      );
    } finally {
      setCheckingConnections(false);
    }
  };

  const handleVaultConnect = async (connection: IntegrationConnection) => {
    try {
      setBusyId(connection.id);

      const targetConnection = getVaultConnectionName(connection.provider);
      if (!targetConnection) {
        toast.info(
          `${connection.provider} is not using the Token Vault connected-account path in this MVP.`
        );
        return;
      }

      await getMyAccountToken(true);

      await connectAccountWithRedirect({
        connection: targetConnection,
        appState: { returnTo: '/integrations' },
      });
    } catch (err) {
      toast.error(
        err instanceof Error
          ? err.message
          : `Failed to start ${connection.provider} connected-account flow`
      );
    } finally {
      setBusyId(null);
    }
  };

  const linkedCount = connectedAccounts.length;

  return (
    <AppLayout>
      <div className="p-6 max-w-5xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold mb-1">Integrations</h1>
          <p className="text-sm text-muted-foreground">
            Manage external service connections and Token Vault linked accounts.
          </p>
        </div>

        <div className="flex items-start gap-3 p-4 rounded-lg bg-ai-surface border border-ai-border mb-4">
          <Shield className="w-5 h-5 text-ai-accent mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-semibold text-ai-accent">Security Notice</p>
            <p className="text-xs text-muted-foreground">
              Slack, Google, and GitHub use user-level delegated access through Connected Accounts and Token Vault.
              Zoom and Email remain system-owned in this MVP.
            </p>
          </div>
        </div>

        <div className="mb-6 rounded-lg border border-primary/20 bg-primary/5 p-4 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-semibold mb-1">Connected Accounts status</p>
            <p className="text-xs text-muted-foreground">
              {linkedCount > 0
                ? `This operator currently has ${linkedCount} linked connected account(s).`
                : 'This operator does not yet have any linked connected accounts. Connect Slack, Google, and GitHub here before rerunning Token Vault-backed actions.'}
            </p>
          </div>

          <button
            type="button"
            onClick={handleCheckLinkedAccounts}
            disabled={checkingConnections || !isAuthenticated}
            className="text-xs px-3 py-2 rounded-md border border-border bg-background hover:bg-muted disabled:opacity-50"
          >
            {checkingConnections ? 'Checking...' : 'Check Linked Accounts'}
          </button>
        </div>

        {loading && <div className="text-center py-12 text-muted-foreground">Loading integrations...</div>}
        {error && !loading && <div className="text-center py-12 text-red-500">{error}</div>}

        {!loading && !error && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {integrations.map((c) => (
              <IntegrationStatusCard
                key={c.id}
                connection={c}
                busy={busyId === c.id || checkingConnections}
                onConnect={isVaultBacked(c.provider) ? handleVaultConnect : undefined}
                onRefresh={loadBackendOnly}
              />
            ))}

            {integrations.length === 0 && (
              <div className="text-center py-12 text-muted-foreground col-span-full">
                No integrations found.
              </div>
            )}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
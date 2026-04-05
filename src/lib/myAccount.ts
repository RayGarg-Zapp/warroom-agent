import { MyAccountClient } from '@auth0/myaccount-js';

type TokenGetter = (options?: {
  authorizationParams?: {
    audience?: string;
    scope?: string;
  };
}) => Promise<string>;

const CONNECTED_ACCOUNT_SCOPES =
  'read:me:connected_accounts create:me:connected_accounts delete:me:connected_accounts';

function getMyAccountAudience(domain: string) {
  return `https://${domain}/me/`;
}

function getMyAccountBaseRedirectUri() {
  return `${window.location.origin}/integrations`;
}

export function createMyAccountClient(params: {
  domain: string;
  getAccessTokenSilently: TokenGetter;
}) {
  const { domain, getAccessTokenSilently } = params;

  return new MyAccountClient({
    domain,
    token: async () =>
      getAccessTokenSilently({
        authorizationParams: {
          audience: getMyAccountAudience(domain),
          scope: CONNECTED_ACCOUNT_SCOPES,
        },
      }),
  });
}

async function collectItems<T>(pageable: AsyncIterable<T>): Promise<T[]> {
  const items: T[] = [];
  for await (const item of pageable) {
    items.push(item);
  }
  return items;
}

export async function listConnectedAccounts(params: {
  domain: string;
  getAccessTokenSilently: TokenGetter;
}) {
  const client = createMyAccountClient(params);
  const page = await client.connectedAccounts.list({ take: 100 });
  return collectItems<any>(page as AsyncIterable<any>);
}

export async function listAvailableConnectedAccountConnections(params: {
  domain: string;
  getAccessTokenSilently: TokenGetter;
}) {
  const client = createMyAccountClient(params);
  const page = await client.connectedAccounts.connections.list({ take: 100 });
  return collectItems<any>(page as AsyncIterable<any>);
}

export async function startConnectedAccountFlow(params: {
  domain: string;
  getAccessTokenSilently: TokenGetter;
  connection: string;
  redirectUri?: string;
}) {
  const client = createMyAccountClient(params);
  const redirectUri = params.redirectUri || getMyAccountBaseRedirectUri();

  const response: any = await client.connectedAccounts.create({
    connection: params.connection,
    redirect_uri: redirectUri,
  });

  const nextUrl =
    response?.redirect_uri ||
    response?.redirectUri ||
    response?.url ||
    response?.authorization_url;

  if (!nextUrl) {
    throw new Error('Connected account flow started, but no redirect URL was returned.');
  }

  window.location.assign(nextUrl);
}

export async function completeConnectedAccountFlow(params: {
  domain: string;
  getAccessTokenSilently: TokenGetter;
  authSession: string;
  connectCode: string;
  redirectUri?: string;
}) {
  const client = createMyAccountClient(params);
  const redirectUri = params.redirectUri || getMyAccountBaseRedirectUri();

  return client.connectedAccounts.complete({
    auth_session: params.authSession,
    connect_code: params.connectCode,
    redirect_uri: redirectUri,
  });
}

export function getConnectionNameForProvider(provider: string): string | null {
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

export function isProviderVaultBacked(provider: string): boolean {
  return getConnectionNameForProvider(provider) !== null;
}
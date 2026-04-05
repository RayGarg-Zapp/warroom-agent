import { Auth0Provider, AppState, useAuth0 } from '@auth0/auth0-react';
import { ReactNode, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { auth0Config } from './auth0-config';
import { setAccessTokenGetter } from '@/lib/authToken';

type ConnectedAccountAppState = AppState & {
  connectedAccount?: {
    connection?: string;
    provider?: string;
  };
  returnTo?: string;
  pendingExecuteActionId?: string;
  pendingIncidentId?: string;
};

type Props = {
  children: ReactNode;
};

const PENDING_EXECUTE_KEY = 'warroom-pending-execute';

function AuthTokenBridge() {
  const { getAccessTokenSilently, isAuthenticated } = useAuth0();

  useEffect(() => {
    if (!isAuthenticated) {
      console.log('[AUTH TOKEN BRIDGE] user not authenticated, clearing getter');
      setAccessTokenGetter(null);
      return;
    }

    console.log('[AUTH TOKEN BRIDGE] installing access token getter', {
      audience: auth0Config.audience,
      scope: auth0Config.scope,
    });

    setAccessTokenGetter(async () => {
      return getAccessTokenSilently({
        authorizationParams: {
          audience: auth0Config.audience,
          scope: auth0Config.scope,
        },
      });
    });

    return () => {
      console.log('[AUTH TOKEN BRIDGE] cleanup, clearing getter');
      setAccessTokenGetter(null);
    };
  }, [getAccessTokenSilently, isAuthenticated]);

  return null;
}

export default function Auth0ProviderWithNavigate({ children }: Props) {
  const navigate = useNavigate();

  const onRedirectCallback = (appState?: ConnectedAccountAppState) => {
    console.log('[AUTH0 REDIRECT CALLBACK] entered', {
      href: window.location.href,
      appState,
    });

    if (appState?.connectedAccount) {
      console.log('[CONNECTED ACCOUNT COMPLETE]', appState.connectedAccount);
      sessionStorage.setItem(
        'tv-last-connected-account',
        JSON.stringify(appState.connectedAccount)
      );
    }

    if (appState?.pendingExecuteActionId) {
      const pending = JSON.stringify({
        actionId: appState.pendingExecuteActionId,
        incidentId: appState.pendingIncidentId,
      });

      console.log('[AUTH0 REDIRECT CALLBACK] restoring pending execute payload from appState', pending);

      sessionStorage.setItem(PENDING_EXECUTE_KEY, pending);
      localStorage.setItem(PENDING_EXECUTE_KEY, pending);
    } else {
      console.log('[AUTH0 REDIRECT CALLBACK] no pending execute payload in appState');
    }

    const target = appState?.returnTo || window.location.pathname || '/integrations';

    console.log('[AUTH0 REDIRECT CALLBACK] navigating', {
      target,
      replace: true,
    });

    navigate(target, { replace: true });
  };

  return (
    <Auth0Provider
      domain={auth0Config.domain}
      clientId={auth0Config.clientId}
      authorizationParams={{
        redirect_uri: window.location.origin,
        audience: auth0Config.audience,
        scope: auth0Config.scope,
      }}
      cacheLocation="localstorage"
      useRefreshTokens={true}
      useRefreshTokensFallback={true}
      onRedirectCallback={onRedirectCallback}
    >
      <AuthTokenBridge />
      {children}
    </Auth0Provider>
  );
}
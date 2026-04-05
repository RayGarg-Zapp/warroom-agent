import { useEffect } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import { LogOut, Shield } from 'lucide-react';

import { SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar';
import { AppSidebar } from './AppSidebar';
import { setAccessTokenGetter } from '@/lib/authToken';
import { auth0Config } from '@/auth/auth0-config';

function initialsFor(name?: string, email?: string) {
  const source = name || email || 'U';
  const parts = source.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0] || ''}${parts[1][0] || ''}`.toUpperCase();
}

export function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, logout, getAccessTokenSilently, isAuthenticated } = useAuth0();

  useEffect(() => {
    if (!isAuthenticated) {
      setAccessTokenGetter(null);
      return;
    }

    setAccessTokenGetter(async () => {
      return getAccessTokenSilently({
        authorizationParams: {
          audience: auth0Config.audience,
          scope: auth0Config.scope,
        },
      });
    });

    return () => setAccessTokenGetter(null);
  }, [getAccessTokenSilently, isAuthenticated]);

  const displayName = user?.name || user?.email || 'Signed In User';
  const initials = initialsFor(user?.name, user?.email);

  return (
    <SidebarProvider>
      <div className="min-h-screen flex w-full">
        <AppSidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <header className="h-14 flex items-center gap-3 border-b border-border bg-card px-4 shrink-0">
            <SidebarTrigger />
            <div className="flex items-center gap-3 ml-auto">
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-severity-success-bg text-severity-success text-xs font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-severity-success" />
                Agent Active
              </div>

              <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full border border-border bg-background">
                <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center text-xs font-semibold text-primary">
                  {initials}
                </div>
                <div className="flex flex-col leading-none">
                  <span className="text-xs font-medium">{displayName}</span>
                  <span className="text-[11px] text-muted-foreground">Operator</span>
                </div>
              </div>

              <button
                onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border bg-background text-sm hover:bg-accent transition-colors"
              >
                <Shield className="w-4 h-4 text-primary" />
                <span className="hidden sm:inline">Sign Out</span>
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </header>

          <main className="flex-1 overflow-auto">{children}</main>
        </div>
      </div>
    </SidebarProvider>
  );
}
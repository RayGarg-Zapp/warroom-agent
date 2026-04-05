import { useAuth0 } from "@auth0/auth0-react";
import { PropsWithChildren, useEffect } from "react";
import { useLocation } from "react-router-dom";

export default function RequireAuth({ children }: PropsWithChildren) {
  const { isAuthenticated, isLoading, loginWithRedirect } = useAuth0();
  const location = useLocation();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      void loginWithRedirect({
        appState: {
          returnTo: location.pathname + location.search,
        },
      });
    }
  }, [isAuthenticated, isLoading, loginWithRedirect, location.pathname, location.search]);

  if (isLoading || !isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center text-sm text-muted-foreground">
        Redirecting to Auth0 sign-in…
      </div>
    );
  }

  return <>{children}</>;
}
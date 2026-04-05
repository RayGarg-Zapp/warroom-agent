export const auth0Config = {
  domain: import.meta.env.VITE_AUTH0_DOMAIN,
  clientId: import.meta.env.VITE_AUTH0_CLIENT_ID,
  audience: import.meta.env.VITE_AUTH0_AUDIENCE,
  scope:
    import.meta.env.VITE_AUTH0_SCOPE ||
    'openid profile email offline_access read:incidents read:audit read:integrations approve:actions execute:actions admin:config',
};

const missing = [
  !auth0Config.domain && 'VITE_AUTH0_DOMAIN',
  !auth0Config.clientId && 'VITE_AUTH0_CLIENT_ID',
  !auth0Config.audience && 'VITE_AUTH0_AUDIENCE',
].filter(Boolean);

if (missing.length) {
  throw new Error(`Missing Auth0 frontend env vars: ${missing.join(', ')}`);
}
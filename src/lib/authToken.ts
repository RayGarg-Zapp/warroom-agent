type TokenGetter = () => Promise<string>;

let tokenGetter: TokenGetter | null = null;
let oneTimeAccessToken: string | null = null;

export function setAccessTokenGetter(getter: TokenGetter | null) {
  tokenGetter = getter;
}

export function setOneTimeAccessToken(token: string | null) {
  oneTimeAccessToken = token;
}

export async function getAccessTokenForApi(): Promise<string> {
  if (oneTimeAccessToken) {
    const token = oneTimeAccessToken;
    oneTimeAccessToken = null;
    return token;
  }

  if (!tokenGetter) {
    throw new Error('No Auth0 access token getter registered');
  }

  return tokenGetter();
}
import { getAccessTokenForApi } from '@/lib/authToken';

export type ApiEnvelope<T> = {
  data: T;
  error: string | null;
  meta?: Record<string, unknown>;
};

export type Incident = Record<string, unknown>;
export type Action = Record<string, unknown>;
export type AuditEntry = Record<string, unknown>;
export type Integration = Record<string, unknown>;
export type DemoHealth = Record<string, unknown>;
export type SeedResult = Record<string, unknown>;

export type ExecutionResult = {
  action_id?: string;
  status?: string;
  success?: boolean;
  error?: string;
  token_path?: string;
  vault_provider?: string | null;
  vault_mode?: string | null;
  authorization_details?: Record<string, unknown>;
  recipients?: string[];
  join_url?: string;
  meeting_id?: number;
  commit_url?: string;
  commit_sha?: string;
  content_url?: string;
  repo?: string;
  file_path?: string;
  operation?: string;
  authz_expected_failure?: boolean;
};

export type IntegrationStatusResult = {
  id: string;
  providerName: string;
  healthy: boolean;
  connectionStatus: string;
};

export type PrepareExecuteResult = {
  actionId: string;
  incidentId: string;
  sensitive: boolean;
  stepUpRequired: boolean;
  requiredScope?: string | null;
  readyToExecute: boolean;
  privilegedAuthMode?: 'redirect' | 'ciba' | null;
  cibaEnabled?: boolean;
};

export type CibaStatusResult = {
  actionId: string;
  incidentId: string;
  state: string;
  executionStatus?: string;
  consoleOperatorSub?: string | null;
  ownerSub?: string | null;
  ownerResolutionSource?: string | null;
  approvedPrincipalSub?: string | null;
  executionPrincipalSub?: string | null;
  executionMode?: string | null;
  executionId?: string | null;
  bindingMessage?: string | null;
  expiresAt?: string | null;
  approvedAt?: string | null;
  executedAt?: string | null;
  pollIntervalSeconds: number;
  terminal: boolean;
  authorized: boolean;
  executed: boolean;
  error?: string | null;
  errorDescription?: string | null;
};

type ApiRequestInit = RequestInit & {
  accessToken?: string;
};

async function apiFetchEnvelope<T>(
  path: string,
  init: ApiRequestInit = {}
): Promise<ApiEnvelope<T>> {
  const { accessToken, ...requestInit } = init;

  const headers = new Headers(requestInit.headers || {});
  headers.set('Content-Type', 'application/json');

  if (!path.startsWith('/health')) {
    if (!accessToken && /^\/api\/actions\/[^/]+\/execute$/.test(path)) {
      throw new Error("❌ Missing stepped-up token for execute call");
    }
    const token = accessToken || (await getAccessTokenForApi());
        headers.set('Authorization', `Bearer ${token}`);
      }

  const response = await fetch(path, {
    ...requestInit,
    headers,
  });

  let payload: ApiEnvelope<T> | null = null;

  try {
    payload = (await response.json()) as ApiEnvelope<T>;
  } catch {
    if (!response.ok) {
      throw new Error(`API request failed: ${response.status} ${response.statusText}`);
    }
  }

  if (!response.ok) {
    throw new Error(
      payload?.error || `API request failed: ${response.status} ${response.statusText}`
    );
  }

  return payload!;
}

async function apiFetch<T>(path: string, init: ApiRequestInit = {}): Promise<T> {
  const envelope = await apiFetchEnvelope<T>(path, init);
  return envelope.data;
}

export const getIncidents = () => apiFetch<Incident[]>('/api/incidents');

export const getIncident = (incidentId: string) =>
  apiFetch<Incident>(`/api/incidents/${incidentId}`);

export const injectIncident = (body: { slackMessage: string; source?: string }) =>
  apiFetch<Incident>('/api/incidents/inject', {
    method: 'POST',
    body: JSON.stringify(body),
  });

export const getActions = (params?: { status?: string; incidentId?: string }) => {
  const search = new URLSearchParams();
  if (params?.status) search.set('status', params.status);
  if (params?.incidentId) search.set('incident_id', params.incidentId);
  const qs = search.toString();
  return apiFetch<Action[]>(`/api/actions${qs ? `?${qs}` : ''}`);
};

export const getAllActions = () => getActions();

export const approveAction = (actionId: string) =>
  apiFetch<Action>(`/api/actions/${actionId}/approve`, { method: 'POST' });

export const denyAction = (actionId: string) =>
  apiFetch<Action>(`/api/actions/${actionId}/deny`, { method: 'POST' });

export const prepareExecuteAction = (actionId: string) =>
  apiFetch<PrepareExecuteResult>(`/api/actions/${actionId}/prepare-execute`, {
    method: 'POST',
  });

export const executeAction = (actionId: string, accessToken?: string) =>
  apiFetch<Action>(`/api/actions/${actionId}/execute`, {
    method: 'POST',
    accessToken,
  });

export const executeActionDetailed = (actionId: string, accessToken?: string) =>
  apiFetchEnvelope<Action>(`/api/actions/${actionId}/execute`, {
    method: 'POST',
    accessToken,
  });

export const startCibaAction = (actionId: string) =>
  apiFetch<CibaStatusResult>(`/api/actions/${actionId}/start-ciba`, {
    method: 'POST',
  });

export const getCibaActionStatus = (actionId: string) =>
  apiFetch<CibaStatusResult>(`/api/actions/${actionId}/ciba-status`);

export const executeAllActions = (incidentId: string) =>
  apiFetch<ExecutionResult[]>(`/api/actions/execute-all/${incidentId}`, {
    method: 'POST',
  });

export const getAuditEntries = (params?: {
  incidentId?: string;
  search?: string;
  actorType?: string;
}) => {
  const search = new URLSearchParams();
  if (params?.incidentId) search.set('incident_id', params.incidentId);
  if (params?.search) search.set('search', params.search);
  if (params?.actorType) search.set('actor_type', params.actorType);
  const qs = search.toString();
  return apiFetch<AuditEntry[]>(`/api/audit${qs ? `?${qs}` : ''}`);
};

export const getIntegrations = () => apiFetch<Integration[]>('/api/integrations');

export const reconnectIntegration = (integrationId: string) =>
  apiFetch<Integration>(`/api/integrations/${integrationId}/reconnect`, {
    method: 'POST',
  });

export const getIntegrationStatus = (integrationId: string) =>
  apiFetch<IntegrationStatusResult>(`/api/integrations/${integrationId}/status`);

export const seedDemoData = () =>
  apiFetch<SeedResult>('/api/demo/seed', { method: 'POST' });

export const getDemoHealth = () => apiFetch<DemoHealth>('/api/demo/health');

export type ChatMessage = { role: 'user' | 'assistant'; content: string };
export type ChatReply = { reply: string; incidentId: string; model: string };

export const chatWithAgent = (
  incidentId: string,
  message: string,
  history: ChatMessage[]
) =>
  apiFetch<ChatReply>(`/api/chat/${incidentId}`, {
    method: 'POST',
    body: JSON.stringify({ message, history }),
  });

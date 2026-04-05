import { useEffect, useMemo, useState, useCallback, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { useAuth0 } from '@auth0/auth0-react';
import { AppLayout } from '@/components/AppLayout';
import { IncidentSummaryHero } from '@/components/IncidentSummaryHero';
import { ResponderList } from '@/components/ResponderList';
import { KnownIssueCard } from '@/components/KnownIssueCard';
import { ApprovalCard } from '@/components/ApprovalCard';
import { AuditTimeline } from '@/components/AuditTimeline';
import { StepUpAuthNotice } from '@/components/StepUpAuthNotice';
import { Button } from '@/components/ui/button';
import { IncidentChatWidget } from '@/components/IncidentChatWidget';
import { Loader2, Play, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import {
  approveAction,
  denyAction,
  executeActionDetailed,
  executeAllActions,
  getCibaActionStatus,
  getIncident,
  prepareExecuteAction,
  startCibaAction,
} from '@/lib/api';
import { auth0Config } from '@/auth/auth0-config';
import type { Incident } from '@/types';
import type { CibaStatusResult } from '@/lib/api';

type ExecuteResult = {
  action_id?: string;
  status?: string;
  success?: boolean;
  error?: string;
  token_path?: string;
  vault_provider?: string | null;
  vault_mode?: string | null;
  authorization_details?: Record<string, unknown>;
  commit_url?: string;
  commit_sha?: string;
  content_url?: string;
  repo?: string;
  file_path?: string;
  operation?: string;
  authz_expected_failure?: boolean;
};

function isGitHubRemediation(action: any): boolean {
  return (
    action?.type === 'github_app_repo_update' ||
    action?.type === 'github_network_repo_update'
  );
}

const FORCED_STEP_UP_SCOPE =
  'openid profile email offline_access read:incidents read:audit read:integrations approve:actions execute:actions admin:config execute:remediation';

const PENDING_EXECUTE_KEY = 'warroom-pending-execute';

type PendingExecutePayload = {
  actionId: string;
  incidentId?: string;
  requestedAt?: string;
};

function getPersistedCibaSession(action: any): CibaStatusResult | null {
  const raw = action?.metadata?.ciba;
  if (!raw || typeof raw !== 'object') {
    return null;
  }

  const record = raw as Record<string, unknown>;
  const principal = (record.principal || {}) as Record<string, unknown>;
  const request = (record.request || {}) as Record<string, unknown>;
  const approval = (record.approval || {}) as Record<string, unknown>;
  const execution = (record.execution || {}) as Record<string, unknown>;
  const state = String(record.status || record.state || '');
  if (!state) {
    return null;
  }

  const intervalValue = Number(request.poll_interval_seconds || record.interval_seconds || 5);

  return {
    actionId: String(action.id),
    incidentId: String(action.incidentId || ''),
    state,
    executionStatus: typeof action.executionStatus === 'string' ? action.executionStatus : undefined,
    consoleOperatorSub:
      typeof principal.console_operator_sub === 'string'
        ? String(principal.console_operator_sub)
        : null,
    ownerSub:
      typeof principal.target_owner_sub === 'string'
        ? String(principal.target_owner_sub)
        : null,
    ownerResolutionSource:
      typeof principal.owner_resolution_source === 'string'
        ? String(principal.owner_resolution_source)
        : null,
    approvedPrincipalSub:
      typeof principal.approved_sub === 'string' ? String(principal.approved_sub) : null,
    executionPrincipalSub:
      typeof principal.execution_sub === 'string' ? String(principal.execution_sub) : null,
    executionMode:
      typeof principal.execution_mode === 'string' ? String(principal.execution_mode) : null,
    executionId:
      typeof execution.execution_id === 'string' ? String(execution.execution_id) : null,
    bindingMessage:
      typeof request.binding_message === 'string' ? String(request.binding_message) : null,
    expiresAt:
      typeof request.expires_at === 'string' ? String(request.expires_at) : null,
    approvedAt:
      typeof approval.approved_at === 'string' ? String(approval.approved_at) : null,
    executedAt:
      typeof execution.completed_at === 'string' ? String(execution.completed_at) : null,
    pollIntervalSeconds: Number.isFinite(intervalValue) && intervalValue > 0 ? intervalValue : 5,
    terminal: ['executed', 'execution_failed', 'denied', 'expired', 'failed'].includes(state),
    authorized: ['approval_received', 'execution_in_progress', 'executed', 'execution_failed'].includes(state),
    executed: state === 'executed',
    error:
      typeof request.last_poll_error === 'string' ? String(request.last_poll_error) : null,
    errorDescription:
      typeof request.last_poll_error_description === 'string'
        ? String(request.last_poll_error_description)
        : null,
  };
}

function describeCibaState(session: CibaStatusResult | null | undefined): string | undefined {
  if (!session) return undefined;

  switch (session.state) {
    case 'authorization_pending':
      return 'Waiting for external approval from the remediation owner.';
    case 'approval_received':
      return 'External approval received. Executing remediation now.';
    case 'execution_in_progress':
      return 'External approval received. Remediation execution is in progress.';
    case 'executed':
      return 'External approval completed and remediation executed.';
    case 'execution_failed':
      return 'External approval succeeded, but remediation execution failed.';
    case 'denied':
      return 'External approval was denied.';
    case 'expired':
      return 'External approval request expired.';
    case 'failed':
      return 'External approval request failed.';
    default:
      return undefined;
  }
}

function buildResumeUrl(actionId: string, incidentId?: string) {
  const params = new URLSearchParams();
  params.set('resumeActionId', actionId);
  if (incidentId) {
    params.set('resumeIncidentId', incidentId);
  }
  return `${window.location.pathname}?${params.toString()}`;
}

function readPendingFromUrl(): PendingExecutePayload | null {
  const params = new URLSearchParams(window.location.search);
  const actionId = params.get('resumeActionId');
  const incidentId = params.get('resumeIncidentId');

  if (!actionId) return null;

  return {
    actionId,
    incidentId: incidentId || undefined,
  };
}

function clearResumeParamsFromUrl() {
  const cleanUrl = window.location.pathname;
  window.history.replaceState({}, document.title, cleanUrl);
}

export default function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const {
    loginWithRedirect,
    getAccessTokenSilently,
    isAuthenticated,
    isLoading: authLoading,
    user,
  } = useAuth0();

  const [incident, setIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(true);
  const [mutating, setMutating] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [executingActionId, setExecutingActionId] = useState<string | null>(null);
  const [cibaSessions, setCibaSessions] = useState<Record<string, CibaStatusResult>>({});
  const [error, setError] = useState('');
  const cibaPollTimeoutsRef = useRef<Record<string, number>>({});

  useEffect(() => {
    console.log('[WARROOM DEBUG] component mounted', {
      href: window.location.href,
      auth0Config,
      forcedStepUpScope: FORCED_STEP_UP_SCOPE,
      isAuthenticated,
      authLoading,
      userSub: user?.sub,
      userEmail: user?.email,
      pendingInSessionStorage: sessionStorage.getItem(PENDING_EXECUTE_KEY),
      pendingInLocalStorage: localStorage.getItem(PENDING_EXECUTE_KEY),
      pendingFromUrl: readPendingFromUrl(),
    });
  }, [isAuthenticated, authLoading, user]);

  const loadIncident = useCallback(async () => {
    if (!id) return;
    try {
      setLoading(true);
      setError('');
      const data = await getIncident(id);
      setIncident(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load incident');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void loadIncident();
  }, [loadIncident]);

  const clearCibaPoll = useCallback((actionId: string) => {
    const handle = cibaPollTimeoutsRef.current[actionId];
    if (handle) {
      window.clearTimeout(handle);
      delete cibaPollTimeoutsRef.current[actionId];
    }
  }, []);

  const pollCibaStatus = useCallback(
    async (actionId: string, delaySeconds = 5) => {
      clearCibaPoll(actionId);

      cibaPollTimeoutsRef.current[actionId] = window.setTimeout(async () => {
        try {
          const status = await getCibaActionStatus(actionId);

          console.log('[WARROOM CIBA] polled status', status);
          console.log('[WARROOM CIBA] principal state', {
            actionId,
            consoleOperatorSub: status.consoleOperatorSub,
            targetOwnerSub: status.ownerSub,
            ownerResolutionSource: status.ownerResolutionSource,
            approvedPrincipalSub: status.approvedPrincipalSub,
            executionPrincipalSub: status.executionPrincipalSub,
            executionMode: status.executionMode,
            executionId: status.executionId,
            state: status.state,
          });
          setCibaSessions((prev) => ({
            ...prev,
            [actionId]: status,
          }));

          if (status.terminal) {
            clearCibaPoll(actionId);
            setExecutingActionId((current) => (current === actionId ? null : current));
            await loadIncident();

            if (status.executed) {
              toast.success('External approval completed and remediation executed.');
            } else {
              toast.error(
                status.errorDescription ||
                  describeCibaState(status) ||
                  'External approval did not complete successfully.'
              );
            }
            return;
          }

          void pollCibaStatus(actionId, status.pollIntervalSeconds || 5);
        } catch (err) {
          console.error('[WARROOM CIBA] poll failed', err);
          clearCibaPoll(actionId);
          setExecutingActionId((current) => (current === actionId ? null : current));
          toast.error(
            err instanceof Error ? err.message : 'Failed while polling external approval status'
          );
        }
      }, Math.max(delaySeconds, 1) * 1000);
    },
    [clearCibaPoll, loadIncident]
  );

  useEffect(() => {
    return () => {
      Object.values(cibaPollTimeoutsRef.current).forEach((handle) => {
        window.clearTimeout(handle);
      });
      cibaPollTimeoutsRef.current = {};
    };
  }, []);

  const plannedActions = useMemo(() => {
    const raw = (incident as any)?.plannedActions;
    return Array.isArray(raw) ? raw : [];
  }, [incident]);

  const responders = useMemo(() => {
    const raw = (incident as any)?.responders;
    return Array.isArray(raw) ? raw : [];
  }, [incident]);

  const knownIssues = useMemo(() => {
    const raw = (incident as any)?.knownIssues;
    return Array.isArray(raw) ? raw : [];
  }, [incident]);

  const auditEntries = useMemo(() => {
    const raw = (incident as any)?.auditEntries;
    return Array.isArray(raw) ? raw : [];
  }, [incident]);

  useEffect(() => {
    plannedActions.forEach((action: any) => {
      const persisted = getPersistedCibaSession(action);
      if (!persisted) return;

      setCibaSessions((prev) => {
        const existing = prev[action.id];
        if (existing && existing.state === persisted.state && existing.executionStatus === persisted.executionStatus) {
          return prev;
        }
        return {
          ...prev,
          [action.id]: persisted,
        };
      });

      if (!persisted.terminal && !cibaPollTimeoutsRef.current[action.id]) {
        console.log('[WARROOM CIBA] resuming persisted poll', persisted);
        setExecutingActionId((current) => current || action.id);
        void pollCibaStatus(action.id, persisted.pollIntervalSeconds || 5);
      }
    });
  }, [plannedActions, pollCibaStatus]);

  const handleApprove = async (actionId: string) => {
    try {
      setMutating(true);
      await approveAction(actionId);
      toast.success('Action approved successfully');
      await loadIncident();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to approve action');
    } finally {
      setMutating(false);
    }
  };

  const handleDeny = async (actionId: string) => {
    try {
      setMutating(true);
      await denyAction(actionId);
      toast.error('Action denied');
      await loadIncident();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to deny action');
    } finally {
      setMutating(false);
    }
  };

  const handleExecuteApproved = async () => {
    if (!id) return;

    try {
      setExecuting(true);

      const rawResults = await executeAllActions(id);
      const results = Array.isArray(rawResults) ? (rawResults as ExecuteResult[]) : [];

      const executed = results.filter((r) => r?.status === 'executed' || r?.success).length;
      const skippedSensitive = results.filter(
        (r) => r?.status === 'requires_individual_execution'
      ).length;
      const failed = results.filter(
        (r) =>
          r?.status === 'failed' ||
          (r?.success === false && r?.status !== 'requires_individual_execution')
      );

      if (failed.length === 0) {
        if (skippedSensitive > 0) {
          toast.success(
            `${executed} coordination action(s) executed. ${skippedSensitive} sensitive remediation action(s) are ready for individual execution.`
          );
        } else {
          toast.success(`Executed ${executed} approved action(s) successfully.`);
        }
      } else {
        toast.error(
          `${executed} action(s) executed, ${failed.length} failed. Check audit/logs.`
        );
      }

      await loadIncident();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to execute approved actions');
    } finally {
      setExecuting(false);
    }
  };

  const runFinalExecute = useCallback(
    async (actionId: string, steppedUpAccessToken?: string) => {
      try {
        console.log("🚀 RUN FINAL EXECUTE");

        if (!steppedUpAccessToken) {
          throw new Error("❌ CRITICAL: No stepped-up token provided");
        }

        const payload = JSON.parse(atob(steppedUpAccessToken.split('.')[1]));

        console.log("✅ TOKEN SCOPE:", payload.scope);
        console.log("✅ TOKEN PERMISSIONS:", payload.permissions);

        if (
          !payload.scope?.includes("execute:remediation") &&
          !payload.permissions?.includes("execute:remediation")
        ) {
          throw new Error("❌ TOKEN DOES NOT CONTAIN execute:remediation");
        }

        setExecutingActionId(actionId);

        const envelope = await executeActionDetailed(
          actionId,
          steppedUpAccessToken // 🔥 FORCE USE
        );

        console.log("🔥 EXECUTE RESPONSE:", envelope);

        await loadIncident();
      } catch (err) {
        console.error("❌ EXECUTION FAILED", err);
        toast.error(err instanceof Error ? err.message : "Execution failed");
      } finally {
        setExecutingActionId(null);
      }
    },
    [loadIncident]
  );

  const handleExecuteSingle = async (actionId: string) => {
    let keepActionBusy = false;

    try {
      setExecutingActionId(actionId);

      const prep = await prepareExecuteAction(actionId);

      console.log('[WARROOM EXECUTE] prepareExecuteAction response', prep);

      if (prep.privilegedAuthMode === 'ciba') {
        const started = await startCibaAction(actionId);

        console.log('[WARROOM CIBA] start response', started);
        console.log('[WARROOM CIBA] principal model', {
          actionId,
          consoleOperatorSub: started.consoleOperatorSub,
          targetOwnerSub: started.ownerSub,
          ownerResolutionSource: started.ownerResolutionSource,
          executionMode: started.executionMode,
          executionId: started.executionId,
        });

        setCibaSessions((prev) => ({
          ...prev,
          [actionId]: started,
        }));
        keepActionBusy = true;

        toast.info('Waiting for external approval from the remediation owner.');
        void pollCibaStatus(actionId, started.pollIntervalSeconds || 5);
        return;
      }

      if (prep.sensitive && prep.privilegedAuthMode !== 'redirect') {
        throw new Error('Sensitive GitHub remediation execution is unavailable without CIBA');
      }

      if (prep.stepUpRequired) {
        const pending: PendingExecutePayload = {
          actionId,
          incidentId: id,
          requestedAt: new Date().toISOString(),
        };

        const resumeUrl = buildResumeUrl(actionId, id);

        console.log('[WARROOM EXECUTE] step-up required, opening redirect', {
          pending,
          resumeUrl,
          audience: auth0Config.audience,
          auth0ConfigScope: auth0Config.scope,
          forcedScope: FORCED_STEP_UP_SCOPE,
          hrefBeforeRedirect: window.location.href,
        });

        sessionStorage.setItem(PENDING_EXECUTE_KEY, JSON.stringify(pending));
        localStorage.setItem(PENDING_EXECUTE_KEY, JSON.stringify(pending));

        console.log('[WARROOM EXECUTE] pending written to storage', {
          sessionValue: sessionStorage.getItem(PENDING_EXECUTE_KEY),
          localValue: localStorage.getItem(PENDING_EXECUTE_KEY),
        });

        await loginWithRedirect({
          authorizationParams: {
            audience: auth0Config.audience,
            scope: FORCED_STEP_UP_SCOPE,
            prompt: 'login',
          },
          appState: {
            returnTo: resumeUrl,
          },
        });

        return;
      }

      await runFinalExecute(actionId);
    } catch (err) {
      console.error('[WARROOM EXECUTE] handleExecuteSingle failed', err);
      toast.error(err instanceof Error ? err.message : 'Failed to prepare remediation execution');
    } finally {
      if (!keepActionBusy) {
        setExecutingActionId(null);
      }
    }
  };

  useEffect(() => {
    const pendingFromSession = sessionStorage.getItem(PENDING_EXECUTE_KEY);
    const pendingFromLocal = localStorage.getItem(PENDING_EXECUTE_KEY);
    const pendingFromUrl = readPendingFromUrl();

    console.log('[WARROOM EXECUTE] resume effect entered', {
      id,
      authLoading,
      isAuthenticated,
      href: window.location.href,
      sessionValue: pendingFromSession,
      localValue: pendingFromLocal,
      pendingFromUrl,
    });

    if (!id) {
      console.log('[WARROOM EXECUTE] resume exit: missing route id');
      return;
    }

    if (authLoading) {
      console.log('[WARROOM EXECUTE] resume exit: auth still loading');
      return;
    }

    if (!isAuthenticated) {
      console.log('[WARROOM EXECUTE] resume exit: not authenticated yet');
      return;
    }

    const raw = pendingFromSession || pendingFromLocal;
    const fallbackPending = pendingFromUrl;

    if (!raw && !fallbackPending) {
      console.log('[WARROOM EXECUTE] resume exit: no pending payload found');
      return;
    }

    const resume = async () => {
      try {
        let pending: PendingExecutePayload;

        if (raw) {
          pending = JSON.parse(raw) as PendingExecutePayload;
          console.log('[WARROOM EXECUTE] resume found pending payload from storage', pending);
        } else {
          pending = fallbackPending as PendingExecutePayload;
          console.log('[WARROOM EXECUTE] resume using pending payload from URL', pending);
        }

        console.log('[WARROOM EXECUTE] resume current location', window.location.href);
        console.log('[WARROOM EXECUTE] resume auth context', {
          isAuthenticated,
          authLoading,
          userSub: user?.sub,
          userEmail: user?.email,
          auth0ConfigScope: auth0Config.scope,
          forcedScope: FORCED_STEP_UP_SCOPE,
        });

        if (!pending?.actionId || (pending?.incidentId && pending.incidentId !== id)) {
          console.warn('[WARROOM EXECUTE] pending payload mismatch, clearing it', pending);
          sessionStorage.removeItem(PENDING_EXECUTE_KEY);
          localStorage.removeItem(PENDING_EXECUTE_KEY);
          clearResumeParamsFromUrl();
          return;
        }

        console.log('[WARROOM EXECUTE] requesting stepped-up token silently', {
          audience: auth0Config.audience,
          scope: FORCED_STEP_UP_SCOPE,
        });

        const steppedUpToken = await getAccessTokenSilently({
          authorizationParams: {
            audience: auth0Config.audience,
            scope: FORCED_STEP_UP_SCOPE,
          },
        });

        const payload = JSON.parse(atob(steppedUpToken.split('.')[1]));
        console.log('STEP-UP TOKEN PAYLOAD', payload);
        console.log('STEP-UP TOKEN SCOPE', payload.scope);
        console.log('STEP-UP TOKEN PERMISSIONS', payload.permissions);
        console.log('STEP-UP TOKEN AUD', payload.aud);

        console.log('[WARROOM EXECUTE] obtained stepped-up token after redirect', {
          actionId: pending.actionId,
          incidentId: pending.incidentId,
          tokenPreview: steppedUpToken ? `${steppedUpToken.slice(0, 20)}...` : null,
        });

        sessionStorage.removeItem(PENDING_EXECUTE_KEY);
        localStorage.removeItem(PENDING_EXECUTE_KEY);
        clearResumeParamsFromUrl();

        await runFinalExecute(pending.actionId, steppedUpToken);
      } catch (err) {
        console.error('[WARROOM EXECUTE] resume failed after redirect', err);
        sessionStorage.removeItem(PENDING_EXECUTE_KEY);
        localStorage.removeItem(PENDING_EXECUTE_KEY);
        clearResumeParamsFromUrl();
        toast.error(err instanceof Error ? err.message : 'Failed to resume step-up remediation');
      }
    };

    void resume();
  }, [id, isAuthenticated, authLoading, getAccessTokenSilently, runFinalExecute, user]);

  if (loading) {
    return (
      <AppLayout>
        <div className="p-6 text-center text-muted-foreground">Loading incident...</div>
      </AppLayout>
    );
  }

  if (error || !incident) {
    return (
      <AppLayout>
        <div className="p-6 text-center text-muted-foreground">
          {error || 'Incident not found.'}
        </div>
      </AppLayout>
    );
  }

  const hasHighRisk = plannedActions.some(
    (a: any) =>
      (a?.riskLevel === 'high' || a?.riskLevel === 'critical') &&
      a?.status === 'pending'
  );

  const approvedCoordinationCount = plannedActions.filter(
    (a: any) => a?.status === 'approved' && !isGitHubRemediation(a)
  ).length;
  const controlsDisabled = mutating || executing || executingActionId !== null;

  return (
    <AppLayout>
      <div className="p-6 max-w-6xl mx-auto space-y-6">
        <IncidentSummaryHero incident={incident} />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="glass-panel p-5">
              <h2 className="text-base font-bold mb-4">Suggested Responders</h2>
              <ResponderList responders={responders} />
            </div>

            {knownIssues.length > 0 && (
              <div className="glass-panel p-5">
                <h2 className="text-base font-bold mb-4">Known Issues & Remediation</h2>
                <div className="space-y-3">
                  {knownIssues.map((ki: any) => (
                    <KnownIssueCard key={ki.id || ki.title} issue={ki} />
                  ))}
                </div>
              </div>
            )}

            <div className="glass-panel p-5">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
                <div>
                  <h2 className="text-base font-bold">Proposed Actions — Approval Queue</h2>
                  <p className="text-xs text-muted-foreground mt-1">
                    Approve first. Use bulk execution for coordination actions, then execute
                    sensitive GitHub remediations individually.
                  </p>
                </div>

                <Button
                  type="button"
                  onClick={handleExecuteApproved}
                  disabled={
                    controlsDisabled ||
                    approvedCoordinationCount === 0
                  }
                  className="gap-2"
                >
                  {executing ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Executing...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4" />
                      Execute Approved Actions
                    </>
                  )}
                </Button>
              </div>

              {approvedCoordinationCount > 0 && (
                <div className="mb-4 text-xs text-muted-foreground flex items-center gap-2">
                  <RefreshCw className="w-3.5 h-3.5" />
                  {approvedCoordinationCount} approved coordination action(s) ready for bulk
                  execution.
                </div>
              )}

              {hasHighRisk && (
                <div className="mb-4">
                  <StepUpAuthNotice />
                </div>
              )}

              <div className="space-y-3">
                {plannedActions.map((a: any) => (
                  <ApprovalCard
                    key={a.id}
                    action={a}
                    onApprove={handleApprove}
                    onDeny={handleDeny}
                    onExecute={handleExecuteSingle}
                    disabled={controlsDisabled}
                    busy={executingActionId === a.id}
                    statusMessage={describeCibaState(cibaSessions[a.id] || getPersistedCibaSession(a))}
                  />
                ))}
              </div>
            </div>

            <IncidentChatWidget incidentId={id!} />
          </div>

          <div className="space-y-6">
            <div className="glass-panel p-5">
              <h2 className="text-base font-bold mb-4">Audit Trail</h2>
              <AuditTimeline entries={auditEntries} />
            </div>
          </div>
        </div>

        <div className="glass-panel p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-bold">Incident Lifecycle Log</h2>
              <p className="text-xs text-muted-foreground mt-1">
                Complete trace from discovery through AI analysis, approvals, execution, and chat
                interactions. Click any entry to expand details.
              </p>
            </div>
            <span className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded">
              {auditEntries.length} event{auditEntries.length !== 1 ? 's' : ''}
            </span>
          </div>
          <AuditTimeline entries={auditEntries} />
        </div>
      </div>
    </AppLayout>
  );
}

export type Severity = 'P1' | 'P2' | 'P3';
export type IncidentStatus = 'detected' | 'analyzing' | 'awaiting_approval' | 'in_progress' | 'resolved' | 'failed';
export type ActionType =
  | 'zoom_meeting'
  | 'calendar_event'
  | 'slack_dm'
  | 'email_notification'
  | 'github_app_repo_update'
  | 'github_network_repo_update';
export type ActionStatus = 'pending' | 'approved' | 'denied' | 'executed' | 'failed';
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';
export type Domain = 'identity' | 'network' | 'cloud' | 'security' | 'application' | 'infrastructure';
export type ActorType = 'ai_agent' | 'human' | 'system' | 'integration';

export interface Incident {
  id: string;
  title: string;
  severity: Severity;
  status: IncidentStatus;
  source: string;
  slackMessage: string;
  aiSummary: string;
  severityReasoning: string;
  confidenceScore: number;
  impactedSystems: string[];
  domains: Domain[];
  responders: Responder[];
  knownIssues: KnownIssue[];
  plannedActions: PlannedAction[];
  auditEntries: AuditEntry[];
  detectedAt: string;
  updatedAt: string;
}

export interface Responder {
  id: string;
  name: string;
  role: string;
  domain: Domain;
  email: string;
  avatar?: string;
  available: boolean;
  confidence: number;
}

export interface KnownIssue {
  id: string;
  title: string;
  description: string;
  matchScore: number;
  resolution: string;
  lastOccurrence: string;
}

export interface PlannedAction {
  id: string;
  incidentId: string;
  type: ActionType;
  title: string;
  description: string;
  riskLevel: RiskLevel;
  status: ActionStatus;
  executionStatus?: string;
  provider: string;
  scopesUsed: string[];
  recipients: string[];
  metadata: Record<string, unknown>;
  createdAt: string;
  executedAt?: string;
}

export interface AuditEntry {
  id: string;
  incidentId: string;
  event: string;
  timestamp: string;
  actorType: ActorType;
  actorName: string;
  targetSystem: string;
  approvalStatus?: ActionStatus;
  executionStatus?: ActionStatus;
  metadata?: Record<string, string>;
}

export interface IntegrationConnection {
  id: string;
  provider: string;
  icon: string;
  status: 'connected' | 'disconnected' | 'error';
  scopesGranted: string[];
  lastUsed: string;
  securityNote: string;
}

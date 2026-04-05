import type { Incident, IntegrationConnection, PlannedAction, AuditEntry } from '@/types';

export const mockIncidents: Incident[] = [
  {
    id: 'INC-2024-001',
    title: 'North America Login Outage — IAM Certificate Failure',
    severity: 'P1',
    status: 'awaiting_approval',
    source: '#incidents-prod',
    slackMessage: 'P1 incident: users across North America cannot log in to the customer portal after this morning\'s IAM certificate update. MFA also appears impacted for some tenants. Multiple enterprise customers reporting outage.',
    aiSummary: 'A certificate rotation in the IAM infrastructure has caused authentication failures across the North American region. The expired intermediate certificate is preventing SAML assertion validation, causing cascading failures in both primary SSO and MFA verification flows. Approximately 12,000 enterprise users across 47 tenants are affected.',
    severityReasoning: 'Classified as P1 due to: (1) complete authentication failure for an entire region, (2) multiple enterprise customers impacted, (3) MFA cascade indicating infrastructure-level failure, (4) revenue-impacting — customers cannot access paid services.',
    confidenceScore: 0.94,
    impactedSystems: ['IAM Gateway', 'SSO Service', 'MFA Provider', 'Customer Portal', 'API Gateway'],
    domains: ['identity', 'security', 'application'],
    responders: [
      { id: 'r1', name: 'Sarah Chen', role: 'IAM Lead Engineer', domain: 'identity', email: 'sarah.chen@company.com', available: true, confidence: 0.96 },
      { id: 'r2', name: 'Marcus Williams', role: 'Cloud Security Architect', domain: 'security', email: 'marcus.w@company.com', available: true, confidence: 0.91 },
      { id: 'r3', name: 'Priya Patel', role: 'Platform Engineer', domain: 'cloud', email: 'priya.p@company.com', available: true, confidence: 0.87 },
      { id: 'r4', name: 'James Rodriguez', role: 'App Reliability Lead', domain: 'application', email: 'james.r@company.com', available: false, confidence: 0.82 },
      { id: 'r5', name: 'Nina Kowalski', role: 'Network Engineer', domain: 'network', email: 'nina.k@company.com', available: true, confidence: 0.74 },
    ],
    knownIssues: [
      { id: 'ki1', title: 'IAM Certificate Chain Validation Failure', description: 'Intermediate certificate expiry causes SAML assertion failures across federated identity providers.', matchScore: 0.92, resolution: 'Re-issue intermediate certificate and restart IAM gateway pods. Flush SAML token cache.', lastOccurrence: '2024-01-15' },
      { id: 'ki2', title: 'MFA Cascade from SSO Failure', description: 'When SSO primary path fails, MFA verification falls back to an expired endpoint.', matchScore: 0.78, resolution: 'Update MFA fallback endpoint configuration and enable bypass for known devices during recovery.', lastOccurrence: '2023-11-02' },
    ],
    plannedActions: [
      { id: 'a1', incidentId: 'INC-2024-001', type: 'zoom_meeting', title: 'Create War Room', description: 'Open Zoom war room with all identified responders for real-time incident coordination.', riskLevel: 'low', status: 'pending', provider: 'Zoom', scopesUsed: ['meeting:write'], recipients: ['sarah.chen@company.com', 'marcus.w@company.com', 'priya.p@company.com', 'james.r@company.com'], metadata: { duration: '60', topic: 'P1 War Room — INC-2024-001: NA Login Outage' }, createdAt: '2024-03-15T10:32:00Z' },
      { id: 'a2', incidentId: 'INC-2024-001', type: 'calendar_event', title: 'Schedule Incident Bridge', description: 'Create Google Calendar event for all responders with Zoom link and incident context.', riskLevel: 'low', status: 'pending', provider: 'Google Calendar', scopesUsed: ['calendar.events.write'], recipients: ['sarah.chen@company.com', 'marcus.w@company.com', 'priya.p@company.com', 'james.r@company.com'], metadata: { duration: '60', title: 'P1 Incident Bridge — NA Login Outage' }, createdAt: '2024-03-15T10:32:00Z' },
      { id: 'a3', incidentId: 'INC-2024-001', type: 'slack_dm', title: 'Notify Responders via Slack', description: 'Send direct messages to all identified responders with incident summary and war room link.', riskLevel: 'medium', status: 'pending', provider: 'Slack', scopesUsed: ['chat:write', 'im:write'], recipients: ['sarah.chen', 'marcus.w', 'priya.p', 'james.r', 'nina.k'], metadata: { urgency: 'high' }, createdAt: '2024-03-15T10:32:00Z' },
      { id: 'a4', incidentId: 'INC-2024-001', type: 'email_notification', title: 'Email Stakeholder Notification', description: 'Send email notification to VP Engineering and CTO with incident briefing.', riskLevel: 'high', status: 'pending', provider: 'Email', scopesUsed: ['mail.send'], recipients: ['vp-eng@company.com', 'cto@company.com'], metadata: { template: 'p1-executive-briefing' }, createdAt: '2024-03-15T10:32:00Z' },
    ],
    auditEntries: [
      { id: 'ae1', incidentId: 'INC-2024-001', event: 'Incident detected from Slack channel', timestamp: '2024-03-15T10:30:00Z', actorType: 'ai_agent', actorName: 'WarRoom Agent', targetSystem: 'Slack' },
      { id: 'ae2', incidentId: 'INC-2024-001', event: 'AI analysis completed — P1 classification', timestamp: '2024-03-15T10:30:45Z', actorType: 'ai_agent', actorName: 'WarRoom Agent', targetSystem: 'Analysis Engine' },
      { id: 'ae3', incidentId: 'INC-2024-001', event: '5 responders identified across 4 domains', timestamp: '2024-03-15T10:31:00Z', actorType: 'ai_agent', actorName: 'WarRoom Agent', targetSystem: 'Responder Directory' },
      { id: 'ae4', incidentId: 'INC-2024-001', event: '2 known issues matched', timestamp: '2024-03-15T10:31:15Z', actorType: 'ai_agent', actorName: 'WarRoom Agent', targetSystem: 'Knowledge Base' },
      { id: 'ae5', incidentId: 'INC-2024-001', event: '4 actions proposed — awaiting approval', timestamp: '2024-03-15T10:32:00Z', actorType: 'ai_agent', actorName: 'WarRoom Agent', targetSystem: 'Action Engine' },
    ],
    detectedAt: '2024-03-15T10:30:00Z',
    updatedAt: '2024-03-15T10:32:00Z',
  },
  {
    id: 'INC-2024-002',
    title: 'EU Region — Elevated API Latency on Payment Service',
    severity: 'P2',
    status: 'in_progress',
    source: '#incidents-prod',
    slackMessage: 'P2: EU payment gateway latency is 4x normal. Checkout completion rates dropping. No errors yet but trending toward SLA breach.',
    aiSummary: 'The EU payment processing service is experiencing significant latency degradation. Database connection pooling appears saturated due to a misconfigured max-connections setting deployed in this morning\'s release.',
    severityReasoning: 'P2 — degraded service without complete outage. Revenue impact is growing but transactions are still completing. Risk of escalation to P1 if unresolved within 30 minutes.',
    confidenceScore: 0.87,
    impactedSystems: ['Payment Gateway', 'Database Cluster EU', 'Checkout Service'],
    domains: ['application', 'infrastructure'],
    responders: [
      { id: 'r6', name: 'Alex Müller', role: 'Backend Lead', domain: 'application', email: 'alex.m@company.com', available: true, confidence: 0.93 },
      { id: 'r7', name: 'Yuki Tanaka', role: 'DBA', domain: 'infrastructure', email: 'yuki.t@company.com', available: true, confidence: 0.89 },
    ],
    knownIssues: [
      { id: 'ki3', title: 'Connection Pool Exhaustion', description: 'Max connections set too low after deploy, causing queuing.', matchScore: 0.85, resolution: 'Update connection pool max to 200, restart service pods.', lastOccurrence: '2024-02-20' },
    ],
    plannedActions: [
      { id: 'a5', incidentId: 'INC-2024-002', type: 'slack_dm', title: 'Notify Backend & DBA', description: 'Alert responders about payment latency.', riskLevel: 'low', status: 'executed', provider: 'Slack', scopesUsed: ['chat:write'], recipients: ['alex.m', 'yuki.t'], metadata: {}, createdAt: '2024-03-15T09:15:00Z', executedAt: '2024-03-15T09:16:00Z' },
      { id: 'a6', incidentId: 'INC-2024-002', type: 'zoom_meeting', title: 'Quick Sync Call', description: 'Sync call for backend and DBA.', riskLevel: 'low', status: 'approved', provider: 'Zoom', scopesUsed: ['meeting:write'], recipients: ['alex.m@company.com', 'yuki.t@company.com'], metadata: { duration: '30' }, createdAt: '2024-03-15T09:16:00Z' },
    ],
    auditEntries: [
      { id: 'ae6', incidentId: 'INC-2024-002', event: 'Incident detected', timestamp: '2024-03-15T09:14:00Z', actorType: 'ai_agent', actorName: 'WarRoom Agent', targetSystem: 'Slack' },
      { id: 'ae7', incidentId: 'INC-2024-002', event: 'Slack DMs sent to responders', timestamp: '2024-03-15T09:16:00Z', actorType: 'system', actorName: 'WarRoom Agent', targetSystem: 'Slack', executionStatus: 'executed' },
    ],
    detectedAt: '2024-03-15T09:14:00Z',
    updatedAt: '2024-03-15T09:16:00Z',
  },
  {
    id: 'INC-2024-003',
    title: 'CDN Cache Invalidation Delay — Static Assets Stale',
    severity: 'P2',
    status: 'resolved',
    source: '#incidents-prod',
    slackMessage: 'P2: CDN cache invalidation not propagating. Users seeing old static assets after deploy. Marketing launch page showing yesterday\'s content.',
    aiSummary: 'CDN cache purge request failed silently. Edge nodes in APAC region still serving stale content.',
    severityReasoning: 'P2 — cosmetic and content issue but impacting a marketing launch with revenue implications.',
    confidenceScore: 0.82,
    impactedSystems: ['CDN', 'Marketing Portal'],
    domains: ['network', 'application'],
    responders: [
      { id: 'r8', name: 'Li Wei', role: 'CDN Engineer', domain: 'network', email: 'li.w@company.com', available: true, confidence: 0.95 },
    ],
    knownIssues: [],
    plannedActions: [],
    auditEntries: [
      { id: 'ae8', incidentId: 'INC-2024-003', event: 'Incident detected', timestamp: '2024-03-14T14:00:00Z', actorType: 'ai_agent', actorName: 'WarRoom Agent', targetSystem: 'Slack' },
      { id: 'ae9', incidentId: 'INC-2024-003', event: 'Resolved — cache purge re-executed', timestamp: '2024-03-14T14:45:00Z', actorType: 'human', actorName: 'Li Wei', targetSystem: 'CDN' },
    ],
    detectedAt: '2024-03-14T14:00:00Z',
    updatedAt: '2024-03-14T14:45:00Z',
  },
];

export const mockIntegrations: IntegrationConnection[] = [
  { id: 'int-1', provider: 'Slack', icon: 'MessageSquare', status: 'connected', scopesGranted: ['channels:read', 'chat:write', 'im:write', 'users:read'], lastUsed: '2 minutes ago', securityNote: 'OAuth 2.0 with PKCE. Tokens rotated every 12 hours.' },
  { id: 'int-2', provider: 'Zoom', icon: 'Video', status: 'connected', scopesGranted: ['meeting:write', 'meeting:read'], lastUsed: '1 hour ago', securityNote: 'Server-to-Server OAuth. Scoped to meeting creation only.' },
  { id: 'int-3', provider: 'Google Calendar', icon: 'Calendar', status: 'connected', scopesGranted: ['calendar.events.write', 'calendar.events.read'], lastUsed: '3 hours ago', securityNote: 'Service account with domain-wide delegation. Audit logged.' },
  { id: 'int-4', provider: 'Email (SMTP)', icon: 'Mail', status: 'connected', scopesGranted: ['mail.send'], lastUsed: '1 day ago', securityNote: 'Authenticated SMTP with TLS 1.3. Rate limited to 100/hr.' },
  { id: 'int-5', provider: 'Auth0 / Token Vault', icon: 'Shield', status: 'connected', scopesGranted: ['token:read', 'token:rotate'], lastUsed: '5 minutes ago', securityNote: 'Encrypted at rest (AES-256). Access requires MFA step-up.' },
];

export const allActions: PlannedAction[] = mockIncidents.flatMap(i => i.plannedActions);
export const allAuditEntries: AuditEntry[] = mockIncidents.flatMap(i => i.auditEntries).sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

export const sampleIncidents = [
  { label: 'P1 — North America Login Outage', value: 'INC-2024-001' },
  { label: 'P2 — EU Payment Latency', value: 'INC-2024-002' },
  { label: 'P2 — CDN Cache Stale Assets', value: 'INC-2024-003' },
];

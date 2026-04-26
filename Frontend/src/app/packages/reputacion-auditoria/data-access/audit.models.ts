export interface AuditFilterOptions {
  actions?: string[];
  event_types?: string[];
  entity_types?: string[];
}

export interface AuditLogFilters {
  date_from?: string | null;
  date_to?: string | null;
  action?: string | null;
  event_type?: string | null;
  entity_type?: string | null;
  service_id?: number | null;
  incident_id?: number | null;
  request_id?: number | null;
  actor_id?: number | null;
  user_id?: number | null;
}

export interface AuditLogSummary {
  audit_id: number;
  timestamp: string;
  actor?: string | null;
  usuario?: string | null;
  actor_type?: string | null;
  action: string;
  event_type: string;
  entity_type: string;
  entity_id?: number | null;
  service_id?: number | null;
  incident_id?: number | null;
  request_id?: number | null;
  result?: string | null;
  status?: string | null;
  ip_address?: string | null;
  device_info?: string | null;
  hash_integridad?: string | null;
}

export interface AuditLogDetail extends AuditLogSummary {
  previous_state?: unknown | null;
  new_state?: unknown | null;
  detalle_json?: unknown | null;
  metadata?: unknown | null;
}

export interface ServiceTimelineItem {
  timestamp: string;
  action: string;
  event: string;
  actor?: string | null;
  state_change?: string | null;
  short_description?: string | null;
  audit_id?: number | null;
}

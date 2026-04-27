export interface AuditFilterOptions {
  actions?: string[];
  event_types?: string[];
  main_entities?: string[];
}

export interface AuditLogFilters {
  date_from?: string | null;
  date_to?: string | null;
  action?: string | null;
  event_type?: string | null;
  main_entity?: string | null;
  service_id?: number | null;
  incident_id?: number | null;
  request_id?: number | null;
  payment_id?: number | null;
  actor_user_id?: number | null;
  search?: string | null;
  limit?: number | null;
  offset?: number | null;
}

export interface AuditActorSummary {
  user_id?: number | null;
  persona_id?: number | null;
  email?: string | null;
  tipo_usuario?: string | null;
}

export interface AuditLinkedEntities {
  incident_id?: number | null;
  request_id?: number | null;
  service_id?: number | null;
  payment_id?: number | null;
}

export interface AuditLogSummary {
  audit_id: number;
  timestamp: string;
  action: string;
  event_type: string;
  description: string;
  main_entity: string;
  main_entity_id?: number | null;
  actor?: AuditActorSummary | null;
  linked: AuditLinkedEntities;
  hash_evento: string;
  has_original_data: boolean;
  has_new_data: boolean;
}

export interface AuditLogPageResponse {
  items: AuditLogSummary[];
  total: number;
  limit: number;
  offset: number;
  has_next: boolean;
}

export interface AuditLogDetail extends AuditLogSummary {
  datos_originales?: unknown | null;
  datos_nuevos?: unknown | null;
  ip_origen?: string | null;
  user_agent?: string | null;
}

export interface ServiceTimelineItem {
  audit_id: number;
  timestamp: string;
  action: string;
  event_type: string;
  description: string;
  service_state?: string | null;
  incident_state?: string | null;
}

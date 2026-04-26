export interface NotificationSummary {
  notification_id?: number | null;
  id_notificacion?: number | null;
  title?: string | null;
  titulo?: string | null;
  message?: string | null;
  mensaje?: string | null;
  type?: string | null;
  tipo?: string | null;
  priority?: string | null;
  prioridad?: string | null;
  read?: boolean | null;
  leida?: boolean | null;
  created_at?: string | null;
  fecha_creacion?: string | null;
  service_id?: number | null;
  incident_id?: number | null;
  request_id?: number | null;
  audit_id?: number | null;
  payment_id?: number | null;
}

export interface NotificationDetail extends NotificationSummary {
  read_at?: string | null;
  fecha_lectura?: string | null;
  metadata?: unknown | null;
  detalle_json?: unknown | null;
}

export interface NotificationFilters {
  status?: 'all' | 'unread' | 'read' | null;
  type?: string | null;
  priority?: string | null;
  date_from?: string | null;
  date_to?: string | null;
  service_id?: number | null;
  incident_id?: number | null;
  request_id?: number | null;
}

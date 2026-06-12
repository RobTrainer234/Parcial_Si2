export interface WorkshopSummaryResponse {
  id_taller: number;
  nombre_comercial: string;
}

export interface SpecialtySummaryResponse {
  id_especialidad: number;
  nombre: string;
}

export interface WorkshopIncidentEvidenceResponse {
  id_evidencia: number;
  tipo_evidencia: string;
  categoria: string;
  url_archivo: string;
  mime_type?: string | null;
  tamano_bytes?: number | null;
  fecha_registro: string;
}

export interface WorkshopIncidentEvidenceSummaryResponse {
  total: number;
  imagenes: number;
  audio: number;
}

export interface WorkshopRequestSummary {
  request_id: number;
  incident_id: number;
  incident_state: string;
  sent_at: string;
  expires_at: string;
  distance_km: string | number;
  detected_specialty?: SpecialtySummaryResponse | null;
  severity?: string | null;
  confidence?: string | number | null;
  requires_manual_review?: boolean;
  ai_summary?: string | null;
  used_insurance_priority: boolean;
  attempt_number: number;
  score_total?: string | number | null;
  request_status: string;
}

export interface WorkshopRequestDetailResponse {
  request_id: number;
  request_status: string;
  incident_id: number;
  incident_state: string;
  workshop: WorkshopSummaryResponse;
  sent_at: string;
  expires_at: string;
  is_expired: boolean;
  distance_km: string | number;
  used_insurance_priority: boolean;
  attempt_number: number;
  score_proximidad?: string | number | null;
  score_reputacion?: string | number | null;
  score_total?: string | number | null;
  incident_latitud: string | number;
  incident_longitud: string | number;
  client_reported_specialty?: SpecialtySummaryResponse | null;
  detected_specialty?: SpecialtySummaryResponse | null;
  severity?: string | null;
  confidence?: string | number | null;
  requires_manual_review?: boolean;
  ai_summary?: string | null;
  specific_diagnosis?: string | null;
  suggested_service?: string | null;
  customer_recommendation?: string | null;
  operator_notes?: string | null;
  visual_evidence_tags?: string[] | null;
  audio_summary?: string | null;
  audio_analysis_type?: string | null;
  transcripcion_audio?: string | null;
  image_labels?: string[] | Record<string, unknown> | null;
  evidence_summary: WorkshopIncidentEvidenceSummaryResponse;
  evidences?: WorkshopIncidentEvidenceResponse[];
  service_id?: number | null;
  service_state?: string | null;
  prequotation_code?: string | null;
  prequotation_min?: string | number | null;
  prequotation_max?: string | number | null;
  prequotation_currency?: string | null;
  catalog_service_name?: string | null;
  motivo_cierre?: string | null;
}

export interface WorkshopRequestDecisionRequest {
  decision: 'ACEPTAR' | 'RECHAZAR';
  motivo?: string;
}

export interface WorkshopRequestDecisionResponse {
  request_id: number;
  request_status: string;
  incident_id: number;
  incident_new_state: string;
  workshop: WorkshopSummaryResponse;
  service_id?: number | null;
  service_state?: string | null;
  prequotation_code?: string | null;
  prequotation_min?: string | number | null;
  prequotation_max?: string | number | null;
  prequotation_currency?: string | null;
  catalog_service_name?: string | null;
  next_request_id?: number | null;
  no_candidate_after_rejection: boolean;
  next_selected_workshop?: WorkshopSummaryResponse | null;
  message: string;
}

export interface PrequotationDecisionResult {
  service_id?: number | null;
  service_state?: string | null;
  prequotation_code?: string | null;
  prequotation_min?: string | number | null;
  prequotation_max?: string | number | null;
  prequotation_currency?: string | null;
  catalog_service_name?: string | null;
  message?: string | null;
}

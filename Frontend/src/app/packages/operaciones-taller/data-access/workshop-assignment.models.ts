export interface AssignmentWorkshopSummary {
  id_taller: number;
  nombre_comercial: string;
}

export interface AssignmentSpecialtySummary {
  id_especialidad: number;
  nombre: string;
}

export interface WaitingAssignmentServiceSummary {
  service_id: number;
  service_state: string;
  incident_id: number;
  incident_state: string;
  request_id: number;
  workshop: AssignmentWorkshopSummary;
  detected_specialty?: AssignmentSpecialtySummary | null;
  severity?: string | null;
  ai_summary?: string | null;
  prequotation_code?: string | null;
  prequotation_min?: string | number | null;
  prequotation_max?: string | number | null;
  prequotation_currency?: string | null;
  catalog_service_name?: string | null;
  assignment_timestamp?: string | null;
}

export interface OperarioCandidateSummary {
  id_persona_operario: number;
  nombre_completo: string;
  estado_disponibilidad: string;
  matched_specialty: AssignmentSpecialtySummary;
  anios_experiencia: number;
  certificacion_url?: string | null;
  recommended: boolean;
  match_reason: string;
}

export interface AssignOperarioRequest {
  id_persona_operario: number;
}

export interface AssignedOperarioSummary {
  id_persona_operario: number;
  nombre_completo: string;
  estado_disponibilidad: string;
  matched_specialty: AssignmentSpecialtySummary;
}

export interface AssignOperarioResponse {
  service_id: number;
  service_state: string;
  incident_id: number;
  incident_state: string;
  request_id: number;
  assignment_timestamp?: string | null;
  assigned_operario: AssignedOperarioSummary;
  message: string;
}

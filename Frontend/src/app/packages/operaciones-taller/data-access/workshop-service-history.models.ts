export interface WorkshopServiceHistorySummary {
  service_id: number;
  request_id: number;
  incident_id: number;
  service_state: string;
  incident_state: string;
  specialty?: string | null;
  ai_summary?: string | null;
  client_name?: string | null;
  operario_id?: number | null;
  operario_name?: string | null;
  workshop_name: string;
  prequotation_code?: string | null;
  estimated_min?: number | string | null;
  estimated_max?: number | string | null;
  final_amount?: number | string | null;
  payment_status?: string | null;
  rating_average?: number | string | null;
  rating_comment?: string | null;
  created_at: string;
  assigned_at?: string | null;
  completed_at?: string | null;
  paid_at?: string | null;
}

export interface WorkshopServiceHistoryDetail extends WorkshopServiceHistorySummary {
  client_description?: string | null;
  incident_reference?: string | null;
  detected_specialty?: string | null;
  operario_availability?: string | null;
  payment_amount?: number | string | null;
  payment_currency?: string | null;
  trabajo_realizado?: string | null;
  diagnostico_fisico?: string | null;
  observaciones?: string | null;
  recomendaciones?: string | null;
  final_evidence_count: number;
}

export interface WorkshopServiceHistoryFilters {
  estado?: string | null;
  desde?: string | null;
  hasta?: string | null;
  operario_id?: number | null;
  limit?: number | null;
  offset?: number | null;
}

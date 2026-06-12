export interface DashboardPeriod {
  date_from: string;
  date_to: string;
}

export interface DashboardCountItem {
  label: string;
  count: number;
}

export interface DashboardActionItem {
  priority: 'HIGH' | 'MEDIUM' | 'LOW' | string;
  type: string;
  title: string;
  description: string;
  related_service_id: number | null;
  related_incident_id: number | null;
  recommended_action: string;
}

export interface DashboardMonthlyRevenueItem {
  month: string;
  revenue: number | string;
}

export interface DashboardKpis {
  pending_requests: number;
  accepted_requests: number;
  rejected_requests: number;
  expired_requests: number;
  active_services: number;
  completed_services: number;
  paid_services: number;
  pending_payments: number;
  total_revenue: number | string;
  average_rating: number | null;
  first_contact_resolution_rate: number | null;
  average_acceptance_time_minutes: number | null;
  average_completion_time_minutes: number | null;
}

export interface DashboardOperations {
  services_by_state: DashboardCountItem[];
  requests_by_status: DashboardCountItem[];
}

export interface DashboardFinancial {
  total_revenue: number | string;
  confirmed_payments: number;
  pending_payments: number;
  rejected_payments: number;
  average_ticket: number | string | null;
  projected_revenue: number | string | null;
  monthly_revenue?: DashboardMonthlyRevenueItem[];
}

export interface DashboardOverviewResponse {
  period: DashboardPeriod;
  kpis: DashboardKpis;
  operations: DashboardOperations;
  financial: DashboardFinancial;
  operarios: Record<string, unknown>;
  reputation: Record<string, unknown>;
  action_items: DashboardActionItem[];
}

export interface VoiceDashboardIntentResponse {
  intent: string;
  focus?: string | null;
  metric?: string | null;
  requested_period?: string | null;
}

export interface VoiceDashboardFiltersResponse {
  scope: string;
  date_from?: string | null;
  date_to?: string | null;
}

export interface VoiceDashboardReportResponse {
  transcription?: string | null;
  interpreted_intent: VoiceDashboardIntentResponse;
  generated_report: string;
  used_filters: VoiceDashboardFiltersResponse;
  data_available: boolean;
  warnings: string[];
}

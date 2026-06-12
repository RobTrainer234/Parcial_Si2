export interface ReportFilterResponse {
  date_from?: string | null;
  date_to?: string | null;
  scope: string;
  workshop_id?: number | null;
  status?: string | null;
  severity?: string | null;
  specialty_id?: number | null;
}

export interface StaticReportSummaryResponse {
  report_type: string;
  title: string;
  description: string;
  default_period: string;
  supported_filters: string[];
}

export interface DynamicReportRequest {
  query: string;
  date_from?: string | null;
  date_to?: string | null;
  scope?: string | null;
}

export interface DynamicReportKpiItem {
  key: string;
  label: string;
  value?: number | string | null;
  display_value: string;
  unit?: string | null;
}

export interface DynamicReportSection {
  section_id: string;
  title: string;
  description: string;
  items: string[];
}

export interface DynamicReportChartPoint {
  label: string;
  value?: number | string | null;
  secondary_value?: number | string | null;
}

export interface DynamicReportChart {
  chart_id: string;
  title: string;
  chart_type: string;
  points: DynamicReportChartPoint[];
  unit?: string | null;
  empty_message?: string | null;
}

export interface DynamicReportTableColumn {
  key: string;
  label: string;
}

export interface DynamicReportTable {
  table_id: string;
  title: string;
  columns: DynamicReportTableColumn[];
  rows: Array<Record<string, unknown>>;
  total_count: number;
  limited: boolean;
  empty_message?: string | null;
}

export interface DynamicReportInsight {
  level: string;
  title: string;
  message: string;
  recommendation?: string | null;
}

export interface WorkshopReportResponse {
  report_type: string;
  title: string;
  date_from: string;
  date_to: string;
  scope: string;
  filters: ReportFilterResponse;
  summary: string;
  kpis: DynamicReportKpiItem[];
  sections: DynamicReportSection[];
  charts: DynamicReportChart[];
  tables: DynamicReportTable[];
  insights: DynamicReportInsight[];
  warnings: string[];
  source_tables: string[];
  generated_at: string;
}

export interface DynamicReportResponse extends WorkshopReportResponse {
  interpreted_query: string;
  transcription?: string | null;
}

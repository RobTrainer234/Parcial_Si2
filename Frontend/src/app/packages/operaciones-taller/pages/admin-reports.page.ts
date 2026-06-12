import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
  effect,
  inject,
  signal,
  untracked,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';

import { WorkshopSelectionService } from '../../../core/auth/workshop-selection.service';
import { AppCardComponent } from '../../../shared/components/app-card.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state.component';
import { ErrorStateComponent } from '../../../shared/components/error-state.component';
import { LoadingStateComponent } from '../../../shared/components/loading-state.component';
import { MetricCardComponent } from '../../../shared/components/metric-card.component';
import { PageHeaderComponent } from '../../../shared/components/page-header.component';
import { formatLocalDateTime } from '../../../shared/utils/user-facing-text';
import { WorkshopReportsApi } from '../data-access/workshop-reports.api';
import {
  DynamicReportChart,
  DynamicReportResponse,
  DynamicReportTable,
  StaticReportSummaryResponse,
  WorkshopReportResponse,
} from '../data-access/workshop-reports.models';

type ReportView = WorkshopReportResponse | DynamicReportResponse;

@Component({
  selector: 'app-admin-reports-page',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    FormsModule,
    AppCardComponent,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    MetricCardComponent,
    PageHeaderComponent,
  ],
  template: `
    <div class="page">
      <app-page-header
        eyebrow="BI / Reportes"
        title="Reportes profesionales"
        subtitle="Explora reportes estáticos y dinámicos del taller con KPIs, trazabilidad y detalle operativo."
      >
        <button
          page-actions
          type="button"
          class="app-button app-button--secondary"
          (click)="reloadActiveReport()"
          [disabled]="loading() || workshopSelectionRequired()"
        >
          {{ loading() ? 'Actualizando...' : 'Actualizar reporte' }}
        </button>
      </app-page-header>

      @if (workshopSelectionRequired()) {
        <app-empty-state
          title="Selecciona una sucursal"
          message="Para generar reportes como gerente primero debes seleccionar una sucursal activa."
        />
      } @else {
        <section class="summary-grid">
          <app-metric-card
            label="Reportes estáticos"
            [value]="formatInteger(staticReports().length)"
            hint="Catálogo disponible para el taller"
          />
          <app-metric-card
            label="Workshop scope"
            [value]="currentScopeLabel()"
            hint="Alcance actual aplicado por backend"
          />
          <app-metric-card
            label="Última generación"
            [value]="lastGeneratedLabel()"
            hint="Marca de tiempo del reporte activo"
          />
        </section>

        <app-card
          title="Filtros del reporte"
          subtitle="Define el alcance del reporte estático o usa una consulta dinámica en lenguaje natural."
        >
          <div class="filters">
            <label class="field">
              <span>Tipo de reporte</span>
              <select [ngModel]="selectedReportType()" (ngModelChange)="selectedReportType.set($event)">
                @for (item of staticReports(); track item.report_type) {
                  <option [value]="item.report_type">{{ item.title }}</option>
                }
              </select>
            </label>

            <label class="field">
              <span>Fecha desde</span>
              <input type="date" [ngModel]="dateFromFilter()" (ngModelChange)="dateFromFilter.set($event)" />
            </label>

            <label class="field">
              <span>Fecha hasta</span>
              <input type="date" [ngModel]="dateToFilter()" (ngModelChange)="dateToFilter.set($event)" />
            </label>

            <label class="field">
              <span>Estado</span>
              <select [ngModel]="statusFilter()" (ngModelChange)="statusFilter.set($event)">
                <option value="">Todos</option>
                @for (item of statusOptions; track item) {
                  <option [value]="item">{{ item }}</option>
                }
              </select>
            </label>

            <label class="field">
              <span>Severidad</span>
              <select [ngModel]="severityFilter()" (ngModelChange)="severityFilter.set($event)">
                <option value="">Todas</option>
                @for (item of severityOptions; track item) {
                  <option [value]="item">{{ item }}</option>
                }
              </select>
            </label>

            <label class="field">
              <span>Especialidad ID</span>
              <input
                type="number"
                min="1"
                [ngModel]="specialtyIdFilter()"
                (ngModelChange)="onSpecialtyIdChange($event)"
                placeholder="Opcional"
              />
            </label>

            <div class="field field--actions">
              <button type="button" class="app-button" (click)="loadSelectedStaticReport()" [disabled]="loading()">
                Generar estático
              </button>
            </div>
          </div>
        </app-card>

        <section class="report-catalog">
          @for (item of staticReports(); track item.report_type) {
            <button
              type="button"
              class="report-card"
              [class.report-card--active]="selectedReportType() === item.report_type"
              (click)="selectStaticReport(item.report_type)"
            >
              <strong>{{ item.title }}</strong>
              <span>{{ item.description }}</span>
              <small>Periodo por defecto: {{ formatDefaultPeriod(item.default_period) }}</small>
            </button>
          }
        </section>

        <app-card
          title="Reporte dinámico"
          subtitle="Escribe una consulta o sube un audio. El backend interpreta la intención y construye el reporte con datos reales."
        >
          <div class="dynamic-tools">
            <label class="field field--full">
              <span>Consulta libre</span>
              <textarea
                rows="3"
                [ngModel]="dynamicQuery()"
                (ngModelChange)="dynamicQuery.set($event)"
                placeholder="Ej. dame los accidentes de hoy dia"
              ></textarea>
            </label>

            <div class="dynamic-tools__actions">
              <button type="button" class="app-button" (click)="generateDynamicTextReport()" [disabled]="loading() || !dynamicQuery().trim()">
                Generar reporte
              </button>
              <label class="app-button app-button--secondary dynamic-tools__picker">
                Subir audio
                <input type="file" accept="audio/*" capture="user" (change)="onAudioSelected($event)" />
              </label>
              @if (selectedAudioName()) {
                <small class="text-muted">Audio seleccionado: {{ selectedAudioName() }}</small>
              }
            </div>
          </div>
        </app-card>

        @if (loading() && !report()) {
          <app-loading-state
            title="Generando reporte"
            message="Consultando datos operativos, financieros y de servicio del taller."
          />
        } @else if (error()) {
          <app-error-state [message]="error()">
            <button error-actions type="button" class="app-button" (click)="reloadActiveReport()">
              Reintentar
            </button>
          </app-error-state>
        } @else if (report(); as activeReport) {
          <section class="report-shell">
            <app-card
              [title]="activeReport.title"
              subtitle="Resumen ejecutivo del reporte seleccionado."
            >
              <div class="report-meta">
                <div>
                  <span class="text-muted">Periodo</span>
                  <strong>{{ formatDateRange(activeReport.date_from, activeReport.date_to) }}</strong>
                </div>
                <div>
                  <span class="text-muted">Scope</span>
                  <strong>{{ activeReport.scope }}</strong>
                </div>
                @if (isDynamicReport(activeReport)) {
                  <div>
                    <span class="text-muted">Consulta interpretada</span>
                    <strong>{{ activeReport.interpreted_query }}</strong>
                  </div>
                }
              </div>
              <p class="report-summary">{{ activeReport.summary }}</p>
              @if (isDynamicReport(activeReport) && activeReport.transcription) {
                <p class="text-muted">
                  Transcripción: {{ activeReport.transcription }}
                </p>
              }
              @if (activeReport.warnings.length) {
                <div class="warning-stack">
                  @for (warning of activeReport.warnings; track warning) {
                    <div class="warning-chip">{{ warning }}</div>
                  }
                </div>
              }
            </app-card>

            <section class="kpi-grid">
              @for (item of activeReport.kpis; track item.key) {
                <app-metric-card
                  [label]="item.label"
                  [value]="item.display_value"
                  [hint]="item.unit || 'Dato calculado desde la base transaccional'"
                />
              }
            </section>

            <section class="two-column-grid">
              <app-card
                title="Gráficos"
                subtitle="Vista visual de distribución, volumen y evolución del periodo."
              >
                <div class="chart-grid">
                  @for (chart of activeReport.charts; track chart.chart_id) {
                    <article class="chart-card">
                      <div class="chart-card__header">
                        <strong>{{ chart.title }}</strong>
                        <small class="text-muted">{{ chart.chart_type }}</small>
                      </div>
                      @if (chart.points.length) {
                        <div class="chart-bars">
                          @for (point of chart.points; track point.label + '-' + $index) {
                            <div class="chart-bars__row">
                              <div class="chart-bars__labels">
                                <span>{{ point.label }}</span>
                                <strong>{{ formatPointValue(point.value, chart.unit) }}</strong>
                              </div>
                              <div class="chart-bars__track">
                                <span
                                  class="chart-bars__fill"
                                  [style.width.%]="chartWidth(chart, point.value)"
                                ></span>
                              </div>
                            </div>
                          }
                        </div>
                      } @else {
                        <p class="text-muted">{{ chart.empty_message || 'Sin datos suficientes' }}</p>
                      }
                    </article>
                  }
                </div>
              </app-card>

              <app-card
                title="Insights y recomendaciones"
                subtitle="Hallazgos automáticos a partir de los datos reales del taller."
              >
                @if (activeReport.insights.length) {
                  <div class="insight-list">
                    @for (insight of activeReport.insights; track insight.title + insight.level) {
                      <article class="insight-card">
                        <div class="list__meta">
                          <span class="badge" [class]="insightBadgeClass(insight.level)">{{ insight.level }}</span>
                          <strong>{{ insight.title }}</strong>
                        </div>
                        <p>{{ insight.message }}</p>
                        @if (insight.recommendation) {
                          <small class="text-muted">{{ insight.recommendation }}</small>
                        }
                      </article>
                    }
                  </div>
                } @else {
                  <app-empty-state
                    title="Sin insights"
                    message="No hay hallazgos destacados para este periodo."
                  />
                }

                <div class="traceability">
                  <span class="text-muted">Fuente</span>
                  <strong>{{ activeReport.source_tables.join(', ') || 'Sin fuentes declaradas' }}</strong>
                </div>
              </app-card>
            </section>

            <section class="two-column-grid">
              <app-card
                title="Secciones del reporte"
                subtitle="Resumen estructurado para defensa y lectura ejecutiva."
              >
                @if (activeReport.sections.length) {
                  <div class="section-list">
                    @for (section of activeReport.sections; track section.section_id) {
                      <article class="list__item">
                        <strong>{{ section.title }}</strong>
                        <p class="text-muted">{{ section.description }}</p>
                        @if (section.items.length) {
                          <ul class="bullet-list">
                            @for (item of section.items; track item) {
                              <li>{{ item }}</li>
                            }
                          </ul>
                        }
                      </article>
                    }
                  </div>
                } @else {
                  <app-empty-state
                    title="Sin secciones"
                    message="No se generaron secciones narrativas para este reporte."
                  />
                }
              </app-card>

              <app-card
                title="Trazabilidad y filtros"
                subtitle="Filtros aplicados y metadatos del reporte activo."
              >
                <div class="filter-summary">
                  <div class="row">
                    <span>Scope</span>
                    <strong>{{ activeReport.filters.scope }}</strong>
                  </div>
                  <div class="row">
                    <span>Workshop</span>
                    <strong>{{ activeReport.filters.workshop_id || 'No disponible' }}</strong>
                  </div>
                  <div class="row">
                    <span>Estado</span>
                    <strong>{{ activeReport.filters.status || 'Todos' }}</strong>
                  </div>
                  <div class="row">
                    <span>Severidad</span>
                    <strong>{{ activeReport.filters.severity || 'Todas' }}</strong>
                  </div>
                  <div class="row">
                    <span>Especialidad</span>
                    <strong>{{ activeReport.filters.specialty_id || 'Todas' }}</strong>
                  </div>
                </div>
              </app-card>
            </section>

            <section class="table-stack">
              @for (table of activeReport.tables; track table.table_id) {
                <app-card
                  [title]="table.title"
                  subtitle="Detalle tabular del reporte."
                >
                  @if (table.rows.length) {
                    <div class="table-meta">
                      <span>Total filas: {{ table.total_count }}</span>
                      @if (table.limited) {
                        <span>Mostrando primeras {{ table.rows.length }} filas</span>
                      }
                    </div>
                    <div class="table-wrap">
                      <table class="report-table">
                        <thead>
                          <tr>
                            @for (column of table.columns; track column.key) {
                              <th>{{ column.label }}</th>
                            }
                          </tr>
                        </thead>
                        <tbody>
                          @for (row of table.rows; track $index) {
                            <tr>
                              @for (column of table.columns; track column.key) {
                                <td>{{ formatTableCell(row[column.key]) }}</td>
                              }
                            </tr>
                          }
                        </tbody>
                      </table>
                    </div>
                  } @else {
                    <app-empty-state
                      title="Sin filas"
                      [message]="table.empty_message || 'Sin datos suficientes para el periodo seleccionado.'"
                    />
                  }
                </app-card>
              }
            </section>
          </section>
        } @else if (staticReportsLoaded()) {
          <app-empty-state
            title="Sin reporte generado"
            message="Selecciona un reporte estático o escribe una consulta dinámica para comenzar."
          />
        }
      }
    </div>
  `,
  styles: [
    `
      .summary-grid,
      .kpi-grid {
        display: grid;
        gap: var(--space-4);
        grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
      }

      .filters {
        display: grid;
        gap: var(--space-4);
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      }

      .field {
        display: flex;
        flex-direction: column;
        gap: 0.45rem;
      }

      .field span {
        font-size: 0.82rem;
        color: var(--color-text-muted);
        font-weight: 600;
      }

      .field select,
      .field input,
      .field textarea {
        border: 1px solid var(--color-border);
        border-radius: var(--radius-md);
        padding: 0.75rem 0.85rem;
        font: inherit;
        background: var(--color-surface-elevated);
        color: var(--color-text);
      }

      .field--actions {
        justify-content: end;
      }

      .field--full {
        grid-column: 1 / -1;
      }

      .report-catalog {
        display: grid;
        gap: var(--space-4);
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      }

      .report-card {
        display: flex;
        flex-direction: column;
        gap: 0.6rem;
        padding: var(--space-5);
        border-radius: var(--radius-lg);
        border: 1px solid var(--color-border);
        background: var(--color-surface-soft);
        color: inherit;
        text-align: left;
        cursor: pointer;
      }

      .report-card--active {
        border-color: color-mix(in srgb, var(--color-primary) 28%, var(--color-border));
        background: color-mix(in srgb, var(--color-primary) 9%, var(--color-surface));
        box-shadow: inset 3px 0 0 var(--color-primary);
      }

      .dynamic-tools {
        display: flex;
        flex-direction: column;
        gap: var(--space-4);
      }

      .dynamic-tools__actions {
        display: flex;
        gap: var(--space-3);
        flex-wrap: wrap;
        align-items: center;
      }

      .dynamic-tools__picker {
        position: relative;
        overflow: hidden;
      }

      .dynamic-tools__picker input {
        position: absolute;
        inset: 0;
        opacity: 0;
        cursor: pointer;
      }

      .report-shell,
      .table-stack,
      .section-list,
      .insight-list {
        display: flex;
        flex-direction: column;
        gap: var(--space-4);
      }

      .report-meta {
        display: grid;
        gap: var(--space-4);
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      }

      .report-summary {
        margin: var(--space-4) 0 0;
        line-height: 1.65;
      }

      .warning-stack {
        display: flex;
        flex-wrap: wrap;
        gap: var(--space-3);
        margin-top: var(--space-4);
      }

      .warning-chip {
        padding: 0.45rem 0.75rem;
        border-radius: 999px;
        background: color-mix(in srgb, #f59e0b 12%, var(--color-surface));
        border: 1px solid color-mix(in srgb, #f59e0b 28%, var(--color-border));
        font-size: 0.85rem;
      }

      .two-column-grid {
        display: grid;
        gap: var(--space-4);
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }

      .chart-grid {
        display: grid;
        gap: var(--space-4);
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      }

      .chart-card,
      .insight-card {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        padding: var(--space-4);
        border-radius: var(--radius-lg);
        border: 1px solid var(--color-border);
        background: color-mix(in srgb, var(--color-surface-soft) 92%, transparent);
      }

      .chart-card__header {
        display: flex;
        justify-content: space-between;
        gap: var(--space-3);
      }

      .chart-bars {
        display: flex;
        flex-direction: column;
        gap: var(--space-4);
      }

      .chart-bars__labels {
        display: flex;
        justify-content: space-between;
        gap: var(--space-3);
        margin-bottom: var(--space-2);
      }

      .chart-bars__track {
        height: 0.7rem;
        border-radius: 999px;
        background: color-mix(in srgb, var(--color-border) 80%, transparent);
        overflow: hidden;
      }

      .chart-bars__fill {
        display: block;
        height: 100%;
        border-radius: 999px;
        background: linear-gradient(90deg, #2563eb, #38bdf8);
      }

      .list__meta {
        display: flex;
        align-items: center;
        gap: var(--space-3);
        flex-wrap: wrap;
      }

      .traceability,
      .filter-summary,
      .table-meta {
        display: flex;
        flex-direction: column;
        gap: var(--space-3);
      }

      .bullet-list {
        margin: 0;
        padding-left: 1.1rem;
      }

      .table-wrap {
        overflow: auto;
      }

      .report-table {
        width: 100%;
        border-collapse: collapse;
      }

      .report-table th,
      .report-table td {
        padding: 0.8rem 0.75rem;
        border-bottom: 1px solid color-mix(in srgb, var(--color-border) 75%, transparent);
        text-align: left;
        vertical-align: top;
      }

      .report-table th {
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--color-text-muted);
      }

      @media (max-width: 980px) {
        .two-column-grid {
          grid-template-columns: 1fr;
        }
      }
    `,
  ],
})
export class AdminReportsPage {
  private readonly reportsApi = inject(WorkshopReportsApi);
  private readonly destroyRef = inject(DestroyRef);
  private readonly workshopSelection = inject(WorkshopSelectionService);

  protected readonly loading = signal(false);
  protected readonly error = signal('');
  protected readonly staticReports = signal<StaticReportSummaryResponse[]>([]);
  protected readonly staticReportsLoaded = signal(false);
  protected readonly report = signal<ReportView | null>(null);
  protected readonly selectedReportType = signal('daily_operations');
  protected readonly selectedAudioName = signal('');
  protected readonly dynamicQuery = signal('');

  protected readonly dateFromFilter = signal('');
  protected readonly dateToFilter = signal('');
  protected readonly statusFilter = signal('');
  protected readonly severityFilter = signal('');
  protected readonly specialtyIdFilter = signal<number | null>(null);

  protected readonly statusOptions = [
    'PENDIENTE',
    'ACEPTADA',
    'RECHAZADA',
    'EXPIRADA',
    'ASIGNADO',
    'EN_CAMINO',
    'EN_SITIO',
    'PAGADO',
    'CONFIRMADO',
  ];
  protected readonly severityOptions = ['BAJA', 'MEDIA', 'ALTA', 'CRITICA'];

  protected readonly workshopSelectionRequired = computed(
    () => this.workshopSelection.isGerente() && this.workshopSelection.selectedWorkshopId() === null,
  );
  protected readonly currentScopeLabel = computed(
    () => this.report()?.scope || (this.workshopSelectionRequired() ? 'Seleccion requerida' : 'TALLER'),
  );
  protected readonly lastGeneratedLabel = computed(() => {
    const generatedAt = this.report()?.generated_at;
    return generatedAt ? formatLocalDateTime(generatedAt) : 'Sin reporte';
  });

  constructor() {
    this.loadStaticReports();

    effect(() => {
      const selectedWorkshopId = this.workshopSelection.selectedWorkshopId();
      if (this.workshopSelection.isGerente() && selectedWorkshopId === null) {
        untracked(() => {
          this.report.set(null);
          this.error.set('');
        });
        return;
      }
      if (this.staticReportsLoaded()) {
        untracked(() => this.loadSelectedStaticReport());
      }
    });
  }

  protected loadSelectedStaticReport(): void {
    if (this.workshopSelectionRequired()) {
      return;
    }
    this.loading.set(true);
    this.error.set('');
    this.reportsApi
      .getStaticReport({
        reportType: this.selectedReportType(),
        dateFrom: this.dateFromFilter() || null,
        dateTo: this.dateToFilter() || null,
        status: this.statusFilter() || null,
        severity: this.severityFilter() || null,
        specialtyId: this.specialtyIdFilter(),
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.report.set(response);
          this.loading.set(false);
        },
        error: (error: HttpErrorResponse) => {
          this.error.set(this.resolveErrorMessage(error));
          this.loading.set(false);
        },
      });
  }

  protected generateDynamicTextReport(): void {
    const query = this.dynamicQuery().trim();
    if (!query || this.workshopSelectionRequired()) {
      return;
    }
    this.loading.set(true);
    this.error.set('');
    this.reportsApi
      .createDynamicTextReport({
        query,
        date_from: this.dateFromFilter() || null,
        date_to: this.dateToFilter() || null,
        scope: 'TALLER',
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.report.set(response);
          this.loading.set(false);
        },
        error: (error: HttpErrorResponse) => {
          this.error.set(this.resolveErrorMessage(error));
          this.loading.set(false);
        },
      });
  }

  protected onAudioSelected(event: Event): void {
    const input = event.target as HTMLInputElement | null;
    const file = input?.files?.item(0) ?? null;
    if (!file || this.workshopSelectionRequired()) {
      return;
    }

    this.selectedAudioName.set(file.name);
    this.loading.set(true);
    this.error.set('');

    this.reportsApi
      .createDynamicAudioReport({
        audioFile: file,
        dateFrom: this.dateFromFilter() || null,
        dateTo: this.dateToFilter() || null,
        scope: 'TALLER',
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.report.set(response);
          this.loading.set(false);
        },
        error: (error: HttpErrorResponse) => {
          this.error.set(this.resolveErrorMessage(error));
          this.loading.set(false);
        },
      });

    if (input) {
      input.value = '';
    }
  }

  protected selectStaticReport(reportType: string): void {
    this.selectedReportType.set(reportType);
    this.loadSelectedStaticReport();
  }

  protected reloadActiveReport(): void {
    if (this.workshopSelectionRequired()) {
      return;
    }
    if (this.report() && this.isDynamicReport(this.report()!)) {
      const dynamic = this.report() as DynamicReportResponse;
      if (dynamic.transcription && !this.dynamicQuery().trim()) {
        this.dynamicQuery.set(dynamic.transcription);
      }
      if (this.dynamicQuery().trim()) {
        this.generateDynamicTextReport();
        return;
      }
    }
    if (this.staticReportsLoaded()) {
      this.loadSelectedStaticReport();
    }
  }

  protected isDynamicReport(report: ReportView): report is DynamicReportResponse {
    return 'interpreted_query' in report;
  }

  protected formatInteger(value: number | string | null | undefined): string {
    const numericValue = Number(value ?? 0);
    return new Intl.NumberFormat('es-BO', { maximumFractionDigits: 0 }).format(
      Number.isFinite(numericValue) ? numericValue : 0,
    );
  }

  protected formatDateRange(dateFrom: string, dateTo: string): string {
    return `${formatLocalDateTime(dateFrom)} -> ${formatLocalDateTime(dateTo)}`;
  }

  protected formatDefaultPeriod(value: string): string {
    switch (value) {
      case 'today':
        return 'Hoy';
      case 'current_month':
        return 'Mes actual';
      case 'last_30_days':
        return 'Últimos 30 días';
      default:
        return value;
    }
  }

  protected formatPointValue(value: number | string | null | undefined, unit?: string | null): string {
    if (value === null || value === undefined || value === '') {
      return 'Sin datos suficientes';
    }
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue)) {
      return String(value);
    }
    if (unit === 'BOB') {
      return `BOB ${numericValue.toFixed(2)}`;
    }
    if (unit === 'min') {
      return `${Math.round(numericValue)} min`;
    }
    return new Intl.NumberFormat('es-BO', { maximumFractionDigits: 2 }).format(numericValue);
  }

  protected chartWidth(chart: DynamicReportChart, value: number | string | null | undefined): number {
    const values = chart.points.map((item) => this.asNumber(item.value));
    const maxValue = Math.max(...values, 0);
    const current = this.asNumber(value);
    if (!maxValue) {
      return 0;
    }
    return Math.max(8, (current / maxValue) * 100);
  }

  protected formatTableCell(value: unknown): string {
    if (value === null || value === undefined || value === '') {
      return 'Sin datos suficientes';
    }
    if (typeof value === 'string') {
      const maybeDate = new Date(value);
      if (!Number.isNaN(maybeDate.getTime()) && value.includes('T')) {
        return formatLocalDateTime(value);
      }
      return value;
    }
    if (typeof value === 'number') {
      return new Intl.NumberFormat('es-BO', { maximumFractionDigits: 2 }).format(value);
    }
    return String(value);
  }

  protected insightBadgeClass(level: string): string {
    switch (level) {
      case 'HIGH':
        return 'badge badge--danger';
      case 'MEDIUM':
        return 'badge badge--warning';
      case 'LOW':
        return 'badge badge--neutral';
      default:
        return 'badge badge--info';
    }
  }

  protected onSpecialtyIdChange(value: string | number | null): void {
    const numericValue = Number(value);
    this.specialtyIdFilter.set(
      Number.isFinite(numericValue) && numericValue > 0 ? numericValue : null,
    );
  }

  private loadStaticReports(): void {
    this.reportsApi
      .listStaticReports()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.staticReports.set(response);
          if (response.length && !response.some((item) => item.report_type === this.selectedReportType())) {
            this.selectedReportType.set(response[0].report_type);
          }
          this.staticReportsLoaded.set(true);
        },
        error: (error: HttpErrorResponse) => {
          this.error.set(this.resolveErrorMessage(error));
          this.staticReportsLoaded.set(true);
        },
      });
  }

  private resolveErrorMessage(error: HttpErrorResponse): string {
    const detail = typeof error.error?.detail === 'string' ? error.error.detail : '';
    return detail || 'No se pudo generar el reporte solicitado.';
  }

  private asNumber(value: number | string | null | undefined): number {
    const numericValue = Number(value ?? 0);
    return Number.isFinite(numericValue) ? numericValue : 0;
  }
}

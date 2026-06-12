import { CommonModule } from '@angular/common';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';

import { AppCardComponent } from '../../../shared/components/app-card.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state.component';
import { ErrorStateComponent } from '../../../shared/components/error-state.component';
import { LoadingStateComponent } from '../../../shared/components/loading-state.component';
import { MetricCardComponent } from '../../../shared/components/metric-card.component';
import { PageHeaderComponent } from '../../../shared/components/page-header.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge.component';
import {
  WebOfflineIncidentQueueEntry,
  WebOfflineIncidentQueueService,
} from '../../gestion-auxilio/data-access/web-offline-incident-queue.service';
import {
  DashboardCountItem,
  DashboardKpiSourceMetadata,
  DashboardMonthlyRevenueItem,
  DashboardOverviewResponse,
  VoiceDashboardReportResponse,
} from '../data-access/workshop-dashboard.models';
import { WorkshopDashboardApi } from '../data-access/workshop-dashboard.api';

@Component({
  selector: 'app-admin-dashboard-page',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    PageHeaderComponent,
    MetricCardComponent,
    AppCardComponent,
    StatusBadgeComponent,
    LoadingStateComponent,
    EmptyStateComponent,
    ErrorStateComponent,
  ],
  template: `
    <div class="page">
      <app-page-header
        eyebrow="Centro de control"
        title="Dashboard del taller"
        subtitle="Visibilidad rápida del estado operativo, financiero y de servicio del taller."
      >
        <button page-actions type="button" class="app-button app-button--secondary" (click)="reload()" [disabled]="loading()">
          {{ loading() ? 'Actualizando...' : 'Actualizar panel' }}
        </button>
      </app-page-header>

      @if (loading() && !overview()) {
        <app-loading-state
          title="Cargando tablero"
          message="Consultando KPIs y métricas del taller."
        />
      } @else if (error()) {
        <app-error-state [message]="error()">
          <button error-actions type="button" class="app-button" (click)="reload()">
            Actualizar panel
          </button>
        </app-error-state>
      } @else if (overview(); as data) {
        <section class="dashboard-kpis">
          <app-metric-card
            label="Solicitudes pendientes"
            [value]="formatInteger(data.kpis.pending_requests)"
            hint="Pendientes por decisión del taller"
          />
          <app-metric-card
            label="Servicios activos"
            [value]="formatInteger(data.kpis.active_services)"
            hint="Servicios actualmente en ejecución"
          />
          <app-metric-card
            label="Tiempo de asignación"
            [value]="formatMinutes(data.kpis.average_assignment_time_minutes)"
            hint="Solicitud enviada -> solicitud aceptada"
          />
          <app-metric-card
            label="Asignación de operario"
            [value]="formatMinutes(data.kpis.average_operator_assignment_time_minutes)"
            hint="Aceptación/creación -> operario asignado"
          />
          <app-metric-card
            label="Tiempo de llegada"
            [value]="formatMinutes(data.kpis.average_arrival_time_minutes)"
            hint="Navegación iniciada -> operario en sitio"
          />
          <app-metric-card
            label="Tiempo de completado"
            [value]="formatMinutes(data.kpis.average_completion_time_minutes)"
            hint="Servicio iniciado -> servicio finalizado"
          />
          <app-card
            title="Servicios realizados"
            subtitle="Conteo real de cierres del periodo."
          >
            <div class="history-card">
              <div>
                <span class="history-card__label">Servicios con fecha_fin registrada</span>
                <strong class="history-card__value">
                  {{ formatInteger(data.kpis.completed_services_count) }}
                </strong>
              </div>
              <a routerLink="/admin/services" class="app-button app-button--secondary">
                Ver historial
              </a>
            </div>
          </app-card>
        </section>

        <section class="metric-section">
          <div class="section-heading">
            <div>
              <span class="section-heading__eyebrow">Rendimiento operacional</span>
              <h2>Tiempos de respuesta y SLA</h2>
            </div>
            <span class="period-pill">Datos reales de los ultimos 30 dias</span>
          </div>
          <div class="dashboard-kpis">
            <app-metric-card
              label="Reporte a taller asignado"
              [value]="formatMinutes(data.kpis.average_report_to_workshop_assignment_minutes)"
              hint="Tiempo promedio desde el reporte hasta la aceptacion"
            />
            <app-metric-card
              label="Asignacion de operario"
              [value]="formatMinutes(data.kpis.average_operario_assignment_time_minutes)"
              hint="Desde la aceptacion del taller"
            />
            <app-metric-card
              label="Llegada total"
              [value]="formatMinutes(data.kpis.average_arrival_time_minutes)"
              hint="Desde el reporte hasta la llegada"
            />
            <app-metric-card
              label="Asignacion a llegada"
              [value]="formatMinutes(data.kpis.average_assignment_to_arrival_minutes)"
              hint="Tiempo de desplazamiento del operario"
            />
            <app-metric-card
              label="Cumplimiento SLA"
              [value]="formatPercentage(data.kpis.sla_compliance_rate)"
              [hint]="slaHint(data)"
            />
            <app-metric-card
              label="Eficiencia del taller"
              [value]="formatPercentage(data.kpis.tenant_efficiency_score)"
              hint="Combina cumplimiento SLA y finalizacion"
            />
            <app-metric-card
              label="Casos cancelados"
              [value]="formatInteger(data.kpis.cancelled_cases)"
              hint="Emergencias canceladas en el periodo"
            />
            <app-metric-card
              label="Casos no atendidos"
              [value]="formatInteger(data.kpis.unattended_cases)"
              hint="Solicitudes rechazadas o expiradas sin servicio"
            />
          </div>
        </section>

        <section class="section-grid">
          <app-card
            title="Tiempos y cobertura"
            subtitle="Resumen de promedios, extremos y cobertura real del flujo."
          >
            <div class="list">
              <div class="row">
                <span>Solicitudes aceptadas medidas</span>
                <strong>{{ formatInteger(data.kpis.accepted_request_count) }}</strong>
              </div>
              <div class="row">
                <span>Asignación min / max</span>
                <strong>
                  {{ formatMinutes(data.kpis.min_assignment_time_minutes) }} / {{ formatMinutes(data.kpis.max_assignment_time_minutes) }}
                </strong>
              </div>
              <div class="row">
                <span>Servicios con operario / sin operario</span>
                <strong>
                  {{ formatInteger(data.kpis.assigned_services_count) }} / {{ formatInteger(data.kpis.unassigned_services_count) }}
                </strong>
              </div>
              <div class="row">
                <span>Servicios llegados medidos</span>
                <strong>{{ formatInteger(data.kpis.arrived_services_count) }}</strong>
              </div>
              <div class="row">
                <span>Llegada min / max</span>
                <strong>
                  {{ formatMinutes(data.kpis.min_arrival_time_minutes) }} / {{ formatMinutes(data.kpis.max_arrival_time_minutes) }}
                </strong>
              </div>
            </div>
          </app-card>

          <app-card
            title="Riesgos operativos"
            subtitle="Indicadores simples basados en estados, tracking y asignación."
          >
            <div class="list">
              <div class="row">
                <span>Servicios sin operario</span>
                <strong>{{ formatInteger(data.kpis.services_without_operator) }}</strong>
              </div>
              <div class="row">
                <span>Servicios sin ubicación</span>
                <strong>{{ formatInteger(data.kpis.services_without_location) }}</strong>
              </div>
              <div class="row">
                <span>Tracking desactualizado</span>
                <strong>{{ formatInteger(data.kpis.stale_tracking_services) }}</strong>
              </div>
              <div class="row">
                <span>Ruta excede umbral de llegada</span>
                <strong>{{ formatInteger(data.kpis.services_exceeding_arrival_threshold) }}</strong>
              </div>
            </div>
          </app-card>
        </section>

        <section class="section-grid">
          <app-card
            title="Acciones prioritarias"
            subtitle="Resumen de alertas y decisiones recomendadas para el administrador."
          >
            @if (data.action_items.length) {
              <div class="list">
                @for (item of actionItemsPreview(); track item.title + item.type + item.related_service_id) {
                  <article class="list__item">
                    <div class="list__meta">
                      <span class="badge" [class]="priorityBadgeClass(item.priority)">
                        {{ item.priority }}
                      </span>
                      <strong>{{ item.title }}</strong>
                    </div>
                    <p class="text-muted">{{ item.description }}</p>
                    <small class="text-muted">{{ item.recommended_action }}</small>
                  </article>
                }
              </div>
            } @else {
              <app-empty-state
                title="Sin alertas urgentes"
                message="No hay acciones inmediatas calculadas para el periodo actual."
              />
            }
          </app-card>

          <app-card
            title="Servicios por estado"
            subtitle="Distribución operativa actual del taller."
          >
            @if (data.operations.services_by_state.length) {
              <div class="list">
                @for (item of data.operations.services_by_state; track item.label) {
                  <div class="row">
                    <app-status-badge [label]="item.label" />
                    <strong>{{ formatInteger(item.count) }}</strong>
                  </div>
                }
              </div>
            } @else {
              <app-empty-state
                title="Sin servicios en el periodo"
                message="Todavía no hay estados de servicio que mostrar con el filtro actual."
              />
            }
          </app-card>
        </section>

        <section class="section-grid">
          <app-card
            title="Solicitudes por estado"
            subtitle="Conteo real de solicitudes del periodo."
          >
            @if (data.operations.requests_by_status.length) {
              <div class="list">
                @for (item of data.operations.requests_by_status; track item.label) {
                  <div class="row">
                    <app-status-badge [label]="item.label" />
                    <strong>{{ formatInteger(item.count) }}</strong>
                  </div>
                }
              </div>
            } @else {
              <app-empty-state
                title="Sin solicitudes"
                message="No hay solicitudes registradas para el filtro actual."
              />
            }
          </app-card>

          <app-card
            title="Incidentes por severidad"
            subtitle="Incidentes vinculados a solicitudes del taller."
          >
            @if (data.operations.incidents_by_severity.length) {
              <div class="list">
                @for (item of data.operations.incidents_by_severity; track item.label) {
                  <div class="row">
                    <app-status-badge [label]="item.label" />
                    <strong>{{ formatInteger(item.count) }}</strong>
                  </div>
                }
              </div>
            } @else {
              <app-empty-state
                title="Sin severidades"
                message="No hay incidentes suficientes para este periodo."
              />
            }
          </app-card>
        </section>

        <section class="section-grid">
          <app-card
            title="Incidentes por especialidad"
            subtitle="Tipo de falla detectada en el periodo."
          >
            @if (data.operations.incidents_by_detected_specialty.length) {
              <div class="list">
                @for (item of data.operations.incidents_by_detected_specialty; track item.label) {
                  <div class="row">
                    <span>{{ item.label }}</span>
                    <strong>{{ formatInteger(item.count) }}</strong>
                  </div>
                }
              </div>
            } @else {
              <app-empty-state
                title="Sin especialidades"
                message="No hay incidentes con especialidad detectada para este filtro."
              />
            }
          </app-card>

          <app-card
            title="Fuente del KPI"
            subtitle="Trazabilidad breve para defensa del examen."
          >
            @if (data.kpi_sources.length) {
              <div class="list">
                @for (source of data.kpi_sources; track source.kpi_name) {
                  <article class="list__item">
                    <div class="list__meta">
                      <strong>{{ formatKpiSourceName(source.kpi_name) }}</strong>
                    </div>
                    <p class="text-muted">
                      {{ source.start_event || 'Sin evento inicial' }} -> {{ source.end_event || 'Sin evento final' }}
                    </p>
                    <small class="text-muted">Campos: {{ formatKpiSourceFields(source) }}</small>
                    <small class="text-muted">Tablas: {{ source.source_tables.join(', ') }}</small>
                  </article>
                }
              </div>
            } @else {
              <app-empty-state
                title="Sin trazabilidad"
                message="No hay metadatos de fuente disponibles para este dashboard."
              />
            }
          </app-card>

          <app-card
            title="Incidentes por tipo"
            subtitle="Clasificacion operacional basada en los incidentes registrados."
          >
            @if (data.operations.incidents_by_type.length) {
              <div class="distribution">
                @for (item of data.operations.incidents_by_type; track item.label) {
                  <div class="distribution__item">
                    <div class="distribution__labels">
                      <strong>{{ readableLabel(item.label) }}</strong>
                      <span>{{ formatInteger(item.count) }}</span>
                    </div>
                    <div class="revenue-bars__track">
                      <span
                        class="revenue-bars__bar"
                        [style.width.%]="distributionWidth(item.count, data.operations.incidents_by_type)"
                      ></span>
                    </div>
                  </div>
                }
              </div>
            } @else {
              <app-empty-state title="Sin incidentes" message="No hay incidentes clasificados en el periodo." />
            }
          </app-card>

          <app-card
            title="Zonas con mas incidentes"
            subtitle="Agrupacion geografica aproximada para detectar concentraciones."
          >
            @if (data.operations.incident_zones.length) {
              <div class="list">
                @for (zone of data.operations.incident_zones; track zone.zone_label) {
                  <div class="zone-row">
                    <div>
                      <strong>{{ zone.zone_label }}</strong>
                      <small>{{ readableLabel(zone.dominant_incident_type) }} predominante</small>
                    </div>
                    <span class="zone-row__count">{{ formatInteger(zone.incident_count) }}</span>
                  </div>
                }
              </div>
            } @else {
              <app-empty-state title="Sin zonas detectadas" message="No hay ubicaciones registradas en el periodo." />
            }
          </app-card>
        </section>

        <section class="section-grid">
          <app-card
            title="Eficiencia del equipo"
            subtitle="Ranking de operarios del taller segun respuesta, finalizacion y calificacion."
          >
            @if (data.operarios.operario_ranking.length) {
              <div class="list">
                @for (operario of data.operarios.operario_ranking; track operario.operario_id; let position = $index) {
                  <div class="operator-row">
                    <span class="operator-row__position">{{ position + 1 }}</span>
                    <div class="operator-row__identity">
                      <strong>{{ operario.nombre_completo }}</strong>
                      <small>
                        {{ formatInteger(operario.completed_services) }} finalizados
                        · {{ formatMinutes(operario.average_completion_time_minutes) }}
                      </small>
                    </div>
                    <strong>{{ formatPercentage(operario.efficiency_score) }}</strong>
                  </div>
                }
              </div>
            } @else {
              <app-empty-state title="Sin ranking disponible" message="Aun no existen servicios suficientes para comparar al equipo." />
            }
          </app-card>
        </section>

        <section class="section-grid">
          <app-card
            title="Resumen financiero"
            subtitle="Comparativo simple de cobros y pagos del taller."
          >
            <div class="finance-grid">
              <div class="finance-grid__item">
                <span>Ingresos confirmados</span>
                <strong>{{ formatCurrency(data.financial.total_revenue) }}</strong>
              </div>
              <div class="finance-grid__item">
                <span>Pagos pendientes</span>
                <strong>{{ formatInteger(data.financial.pending_payments) }}</strong>
              </div>
              <div class="finance-grid__item">
                <span>Pagos rechazados</span>
                <strong>{{ formatInteger(data.financial.rejected_payments) }}</strong>
              </div>
              <div class="finance-grid__item">
                <span>Proyección</span>
                <strong>{{ formatCurrency(data.financial.projected_revenue) }}</strong>
              </div>
            </div>

            @if (monthlyRevenue().length) {
              <div class="revenue-bars">
                @for (item of monthlyRevenue(); track item.month) {
                  <div class="revenue-bars__row">
                    <div class="revenue-bars__labels">
                      <span>{{ item.month }}</span>
                      <strong>{{ formatCurrency(item.revenue) }}</strong>
                    </div>
                    <div class="revenue-bars__track">
                      <span
                        class="revenue-bars__bar"
                        [style.width.%]="monthlyRevenueWidth(item)"
                      ></span>
                    </div>
                  </div>
                }
              </div>
            } @else {
              <div class="finance-grid__empty">
                <app-empty-state
                  title="Sin ingresos mensuales"
                  message="No hay ingresos mensuales registrados para este periodo."
                />
              </div>
            }
          </app-card>
        </section>

        <section class="section-grid">
          <app-card
            title="Reporte con IA por voz"
            subtitle="Carga o graba un audio corto para pedir un resumen del dashboard."
          >
            <div class="voice-report">
              <label class="app-button app-button--secondary voice-report__picker">
                Seleccionar o grabar audio
                <input
                  type="file"
                  accept="audio/*"
                  capture="user"
                  (change)="onVoiceAudioSelected($event)"
                />
              </label>
              @if (selectedVoiceFileName()) {
                <p class="text-muted">Archivo: {{ selectedVoiceFileName() }}</p>
              }
              @if (voiceReportLoading()) {
                <p class="text-muted">Transcribiendo y generando reporte...</p>
              }
              @if (voiceReportError()) {
                <p class="feedback feedback--error">{{ voiceReportError() }}</p>
              }
              @if (voiceReport(); as report) {
                <div class="voice-report__result">
                  <div>
                    <span class="text-muted">Transcripcion</span>
                    <p>{{ report.transcription || 'Sin transcripcion util.' }}</p>
                  </div>
                  <div>
                    <span class="text-muted">Intencion interpretada</span>
                    <p>{{ report.interpreted_intent.intent }}</p>
                  </div>
                  <div>
                    <span class="text-muted">Reporte generado</span>
                    <p>{{ report.generated_report }}</p>
                  </div>
                  @if (report.warnings.length) {
                    <div class="warning-copy">
                      {{ report.warnings.join(', ') }}
                    </div>
                  }
                </div>
              }
            </div>
          </app-card>
        </section>
        <section class="section-grid">
          <app-card
            title="Cola offline web"
            subtitle="Fallback minimo para PWA/admin. El flujo principal de incidentes offline vive en la app movil."
          >
            <div class="offline-queue">
              <div class="history-card">
                <div>
                  <span class="history-card__label">Elementos pendientes o con error</span>
                  <strong class="history-card__value">
                    {{ webOfflinePendingCount() }}
                  </strong>
                </div>
                <div class="offline-queue__actions">
                  <button type="button" class="app-button app-button--secondary" (click)="addWebOfflineDemoEntry()">
                    Guardar demo local
                  </button>
                  <button type="button" class="app-button app-button--secondary" (click)="simulateWebOfflineSync()">
                    Simular sync
                  </button>
                  <button type="button" class="app-button app-button--ghost" (click)="simulateWebOfflineError()">
                    Simular error
                  </button>
                </div>
              </div>

              @if (webOfflineEntries().length) {
                <div class="list">
                  @for (entry of webOfflineEntries(); track entry.local_uuid) {
                    <article class="list__item">
                      <div class="list__meta">
                        <span class="badge" [class]="webOfflineBadgeClass(entry.status)">
                          {{ entry.status }}
                        </span>
                        <strong>{{ entry.local_uuid }}</strong>
                      </div>
                      <p class="text-muted">{{ entry.description }}</p>
                      <small class="text-muted">
                        {{ formatDateTime(entry.created_at_local) }}
                        @if (entry.server_incident_id) {
                          · incidente #{{ entry.server_incident_id }}
                        }
                      </small>
                      @if (entry.last_error) {
                        <small class="feedback feedback--error">{{ entry.last_error }}</small>
                      }
                    </article>
                  }
                </div>
              } @else {
                <app-empty-state
                  title="Sin elementos locales"
                  message="No hay reportes de demostracion guardados en localStorage para la web admin."
                />
              }
            </div>
          </app-card>
        </section>
      } @else {
        <app-empty-state
          title="Información no disponible"
          message="No hay información para mostrar en el panel en este momento."
        />
      }
    </div>
  `,
  styles: [
    `
      .dashboard-kpis {
        display: grid;
        gap: var(--space-4);
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      }

      .metric-section {
        display: flex;
        flex-direction: column;
        gap: var(--space-4);
      }

      .section-heading {
        display: flex;
        align-items: end;
        justify-content: space-between;
        gap: var(--space-4);
        flex-wrap: wrap;
      }

      .section-heading h2 {
        margin: var(--space-1) 0 0;
      }

      .section-heading__eyebrow {
        color: var(--color-primary);
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 0.12em;
        text-transform: uppercase;
      }

      .period-pill,
      .zone-row__count,
      .operator-row__position {
        border-radius: 999px;
        background: color-mix(in srgb, var(--color-primary) 14%, transparent);
        color: var(--color-primary);
        font-weight: 800;
      }

      .period-pill {
        padding: 0.55rem 0.85rem;
        font-size: 0.78rem;
      }

      .list {
        display: flex;
        flex-direction: column;
        gap: var(--space-4);
      }

      .list__item {
        display: flex;
        flex-direction: column;
        gap: 0.45rem;
        padding: var(--space-4);
        border-radius: var(--radius-lg);
        border: 1px solid var(--color-border);
        background: color-mix(in srgb, var(--color-surface-soft) 92%, transparent);
      }

      .list__item p,
      .list__item small {
        margin: 0;
      }

      .list__meta {
        display: flex;
        align-items: center;
        gap: var(--space-3);
        flex-wrap: wrap;
      }

      .row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--space-4);
        padding: var(--space-3) 0;
        border-bottom: 1px solid color-mix(in srgb, var(--color-border) 70%, transparent);
      }

      .row:last-child {
        border-bottom: 0;
        padding-bottom: 0;
      }

      .finance-grid {
        display: grid;
        gap: var(--space-4);
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      }

      .history-card {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--space-4);
        flex-wrap: wrap;
      }

      .history-card__label {
        display: block;
        color: var(--color-text-muted);
        font-size: 0.86rem;
      }

      .history-card__value {
        display: block;
        margin-top: var(--space-2);
        font-size: 1.45rem;
      }

      .finance-grid__item {
        padding: var(--space-4);
        border-radius: var(--radius-lg);
        background: color-mix(in srgb, var(--color-surface-soft) 92%, transparent);
        border: 1px solid var(--color-border);
      }

      .finance-grid__item span,
      .health__label {
        display: block;
        color: var(--color-text-muted);
        font-size: 0.86rem;
      }

      .finance-grid__item strong,
      .health__row strong {
        display: block;
        margin-top: var(--space-2);
      }

      .finance-grid__empty {
        margin-top: var(--space-5);
      }

      .voice-report {
        display: flex;
        flex-direction: column;
        gap: var(--space-4);
      }

      .voice-report__picker {
        position: relative;
        overflow: hidden;
        display: inline-flex;
        width: fit-content;
      }

      .voice-report__picker input {
        position: absolute;
        inset: 0;
        opacity: 0;
        cursor: pointer;
      }

      .voice-report__result p {
        margin: var(--space-2) 0 0;
        line-height: 1.6;
      }

      .warning-copy {
        padding: var(--space-4);
        border-radius: var(--radius-lg);
        background: color-mix(in srgb, #f59e0b 12%, var(--color-surface));
        border: 1px solid color-mix(in srgb, #f59e0b 28%, var(--color-border));
      }

      .offline-queue {
        display: flex;
        flex-direction: column;
        gap: var(--space-4);
      }

      .offline-queue__actions {
        display: flex;
        gap: var(--space-3);
        flex-wrap: wrap;
      }

      .revenue-bars {
        display: flex;
        flex-direction: column;
        gap: var(--space-4);
        margin-top: var(--space-6);
      }

      .revenue-bars__labels {
        display: flex;
        justify-content: space-between;
        gap: var(--space-4);
        margin-bottom: var(--space-2);
        font-size: 0.92rem;
      }

      .revenue-bars__track {
        height: 0.7rem;
        border-radius: 999px;
        background: color-mix(in srgb, var(--color-border) 82%, transparent);
        overflow: hidden;
      }

      .revenue-bars__bar {
        display: block;
        height: 100%;
        border-radius: 999px;
        background: linear-gradient(90deg, var(--color-primary), color-mix(in srgb, var(--color-primary) 62%, #ffffff));
      }

      .distribution {
        display: flex;
        flex-direction: column;
        gap: var(--space-4);
      }

      .distribution__labels,
      .zone-row,
      .operator-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--space-4);
      }

      .zone-row,
      .operator-row {
        padding: var(--space-3);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-lg);
      }

      .zone-row small,
      .operator-row small {
        display: block;
        margin-top: var(--space-1);
        color: var(--color-text-muted);
      }

      .zone-row__count,
      .operator-row__position {
        display: grid;
        min-width: 2.3rem;
        min-height: 2.3rem;
        padding: 0.4rem;
        place-items: center;
      }

      .operator-row__identity {
        flex: 1;
      }

      .health {
        display: flex;
        flex-direction: column;
        gap: var(--space-4);
      }

      .health__row {
        padding-bottom: var(--space-4);
        border-bottom: 1px solid color-mix(in srgb, var(--color-border) 70%, transparent);
      }

      .health__row:last-child {
        border-bottom: 0;
        padding-bottom: 0;
      }
    `,
  ],
})
export class AdminDashboardPage {
  private readonly dashboardApi = inject(WorkshopDashboardApi);
  private readonly webOfflineQueue = inject(WebOfflineIncidentQueueService);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly loading = signal(false);
  protected readonly error = signal('');
  protected readonly overview = signal<DashboardOverviewResponse | null>(null);
  protected readonly voiceReportLoading = signal(false);
  protected readonly voiceReportError = signal('');
  protected readonly voiceReport = signal<VoiceDashboardReportResponse | null>(null);
  protected readonly selectedVoiceFileName = signal('');

  protected readonly monthlyRevenue = computed(
    () => this.overview()?.financial.monthly_revenue ?? [],
  );

  protected readonly actionItemsPreview = computed(() =>
    (this.overview()?.action_items ?? []).slice(0, 6),
  );
  protected readonly webOfflineEntries = computed(() => this.webOfflineQueue.entries());
  protected readonly webOfflinePendingCount = computed(() =>
    this.webOfflineQueue.pendingCount(),
  );

  constructor() {
    this.reload();
  }

  protected reload(): void {
    this.loading.set(true);
    this.error.set('');

    this.dashboardApi
      .getOverview()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.overview.set(this.normalizeOverview(response));
          this.loading.set(false);
        },
        error: () => {
          this.error.set('No se pudo cargar el panel. Intenta actualizar.');
          this.loading.set(false);
        },
      });
  }

  protected onVoiceAudioSelected(event: Event): void {
    const input = event.target as HTMLInputElement | null;
    const file = input?.files?.item(0) ?? null;
    if (!file) {
      return;
    }

    this.selectedVoiceFileName.set(file.name);
    this.voiceReportLoading.set(true);
    this.voiceReportError.set('');

    this.dashboardApi
      .createVoiceReport(file)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.voiceReport.set(response);
          this.voiceReportLoading.set(false);
        },
        error: () => {
          this.voiceReportError.set(
            'No se pudo generar el reporte por voz. Intenta nuevamente con un audio más claro.',
          );
          this.voiceReportLoading.set(false);
        },
      });

    if (input) {
      input.value = '';
    }
  }

  protected formatInteger(value: number | string | null | undefined): string {
    return new Intl.NumberFormat('es-BO', { maximumFractionDigits: 0 }).format(
      this.asNumber(value),
    );
  }

  protected formatCurrency(value: number | string | null | undefined): string {
    return `BOB ${new Intl.NumberFormat('es-BO', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(this.asNumber(value))}`;
  }

  protected formatRating(value: number | null | undefined): string {
    if (value === null || value === undefined) {
      return 'Sin datos suficientes';
    }

    return `${value.toFixed(1)} / 5`;
  }

  protected formatMinutes(value: number | null | undefined): string {
    if (value === null || value === undefined) {
      return 'Sin datos suficientes';
    }

    return `${Math.round(value)} min`;
  }

  protected formatPercentage(value: number | null | undefined): string {
    if (value === null || value === undefined) {
      return 'Sin datos suficientes';
    }

    return `${value.toFixed(1)}%`;
  }

  protected formatKpiSourceName(value: string): string {
    switch (value) {
      case 'assignment_time':
        return 'Tiempo de asignación';
      case 'operator_assignment_time':
        return 'Tiempo de asignación de operario';
      case 'arrival_time':
        return 'Tiempo de llegada';
      case 'completion_time':
        return 'Tiempo de completado';
      default:
        return value;
    }
  }

  protected formatKpiSourceFields(source: DashboardKpiSourceMetadata): string {
    const fields = [source.start_field, source.end_field, ...source.source_fields]
      .filter((value): value is string => typeof value === 'string' && value.trim().length > 0);
    return Array.from(new Set(fields)).join(', ');
  }

  protected slaHint(data: DashboardOverviewResponse): string {
    return `${this.formatInteger(data.kpis.sla_met_services)} de ${this.formatInteger(data.kpis.sla_evaluated_services)} servicios dentro del tiempo esperado`;
  }

  protected readableLabel(value: string): string {
    return value.replaceAll('_', ' ').toLocaleLowerCase('es-BO').replace(/^\w/, (letter) => letter.toUpperCase());
  }

  protected distributionWidth(count: number, items: DashboardCountItem[]): number {
    const maxCount = Math.max(...items.map((item) => item.count), 0);
    return maxCount ? Math.max(8, (count / maxCount) * 100) : 0;
  }

  protected priorityBadgeClass(priority: string): string {
    switch (priority) {
      case 'HIGH':
        return 'badge badge--danger';
      case 'MEDIUM':
        return 'badge badge--warning';
      default:
        return 'badge badge--info';
    }
  }

  protected monthlyRevenueWidth(item: DashboardMonthlyRevenueItem): number {
    const values = this.monthlyRevenue().map((entry) => this.asNumber(entry.revenue));
    const maxValue = Math.max(...values, 0);
    const currentValue = this.asNumber(item.revenue);

    if (!maxValue) {
      return 0;
    }

    return Math.max(10, (currentValue / maxValue) * 100);
  }

  protected addWebOfflineDemoEntry(): void {
    this.webOfflineQueue.addDemoEntry();
  }

  protected simulateWebOfflineSync(): void {
    this.webOfflineQueue.simulateSync();
  }

  protected simulateWebOfflineError(): void {
    this.webOfflineQueue.simulateError();
  }

  protected webOfflineBadgeClass(status: WebOfflineIncidentQueueEntry['status']): string {
    switch (status) {
      case 'SINCRONIZADO':
        return 'badge badge--success';
      case 'SINCRONIZANDO':
        return 'badge badge--info';
      case 'ERROR_SYNC':
        return 'badge badge--danger';
      default:
        return 'badge badge--warning';
    }
  }

  protected formatDateTime(value: string): string {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return 'Fecha local no disponible';
    }
    return new Intl.DateTimeFormat('es-BO', {
      dateStyle: 'short',
      timeStyle: 'short',
    }).format(parsed);
  }

  private asNumber(value: number | string | null | undefined): number {
    const numericValue = Number(value ?? 0);
    return Number.isFinite(numericValue) ? numericValue : 0;
  }

  private normalizeOverview(
    response: DashboardOverviewResponse | null | undefined,
  ): DashboardOverviewResponse {
    const data = response ?? this.buildEmptyOverview();
    return {
      period: {
        date_from: data.period?.date_from ?? '',
        date_to: data.period?.date_to ?? '',
      },
      kpis: {
        pending_requests: this.asNumber(data.kpis?.pending_requests),
        accepted_requests: this.asNumber(data.kpis?.accepted_requests),
        rejected_requests: this.asNumber(data.kpis?.rejected_requests),
        expired_requests: this.asNumber(data.kpis?.expired_requests),
        cancelled_requests: this.asNumber(data.kpis?.cancelled_requests),
        active_services: this.asNumber(data.kpis?.active_services),
        completed_services: this.asNumber(data.kpis?.completed_services),
        paid_services: this.asNumber(data.kpis?.paid_services),
        pending_payments: this.asNumber(data.kpis?.pending_payments),
        total_revenue: this.asNumber(data.kpis?.total_revenue),
        average_rating:
          data.kpis?.average_rating !== null && data.kpis?.average_rating !== undefined
            ? Number(data.kpis.average_rating)
            : null,
        first_contact_resolution_rate:
          data.kpis?.first_contact_resolution_rate !== null &&
          data.kpis?.first_contact_resolution_rate !== undefined
            ? Number(data.kpis.first_contact_resolution_rate)
            : null,
        average_assignment_time_minutes:
          data.kpis?.average_assignment_time_minutes !== null &&
          data.kpis?.average_assignment_time_minutes !== undefined
            ? Number(data.kpis.average_assignment_time_minutes)
            : null,
        min_assignment_time_minutes:
          data.kpis?.min_assignment_time_minutes !== null &&
          data.kpis?.min_assignment_time_minutes !== undefined
            ? Number(data.kpis.min_assignment_time_minutes)
            : null,
        max_assignment_time_minutes:
          data.kpis?.max_assignment_time_minutes !== null &&
          data.kpis?.max_assignment_time_minutes !== undefined
            ? Number(data.kpis.max_assignment_time_minutes)
            : null,
        accepted_request_count: this.asNumber(data.kpis?.accepted_request_count),
        average_operator_assignment_time_minutes:
          data.kpis?.average_operator_assignment_time_minutes !== null &&
          data.kpis?.average_operator_assignment_time_minutes !== undefined
            ? Number(data.kpis.average_operator_assignment_time_minutes)
            : null,
        unassigned_services_count: this.asNumber(data.kpis?.unassigned_services_count),
        assigned_services_count: this.asNumber(data.kpis?.assigned_services_count),
        average_arrival_time_minutes:
          data.kpis?.average_arrival_time_minutes !== null &&
          data.kpis?.average_arrival_time_minutes !== undefined
            ? Number(data.kpis.average_arrival_time_minutes)
            : null,
        min_arrival_time_minutes:
          data.kpis?.min_arrival_time_minutes !== null &&
          data.kpis?.min_arrival_time_minutes !== undefined
            ? Number(data.kpis.min_arrival_time_minutes)
            : null,
        max_arrival_time_minutes:
          data.kpis?.max_arrival_time_minutes !== null &&
          data.kpis?.max_arrival_time_minutes !== undefined
            ? Number(data.kpis.max_arrival_time_minutes)
            : null,
        arrived_services_count: this.asNumber(data.kpis?.arrived_services_count),
        average_acceptance_time_minutes:
          data.kpis?.average_acceptance_time_minutes !== null &&
          data.kpis?.average_acceptance_time_minutes !== undefined
            ? Number(data.kpis.average_acceptance_time_minutes)
            : data.kpis?.average_assignment_time_minutes !== null &&
                data.kpis?.average_assignment_time_minutes !== undefined
              ? Number(data.kpis.average_assignment_time_minutes)
            : null,
        average_report_to_workshop_assignment_minutes:
          data.kpis?.average_report_to_workshop_assignment_minutes !== null &&
          data.kpis?.average_report_to_workshop_assignment_minutes !== undefined
            ? Number(data.kpis.average_report_to_workshop_assignment_minutes)
            : null,
        average_operario_assignment_time_minutes:
          data.kpis?.average_operario_assignment_time_minutes !== null &&
          data.kpis?.average_operario_assignment_time_minutes !== undefined
            ? Number(data.kpis.average_operario_assignment_time_minutes)
            : null,
        average_assignment_to_arrival_minutes:
          data.kpis?.average_assignment_to_arrival_minutes !== null &&
          data.kpis?.average_assignment_to_arrival_minutes !== undefined
            ? Number(data.kpis.average_assignment_to_arrival_minutes)
            : null,
        average_completion_time_minutes:
          data.kpis?.average_completion_time_minutes !== null &&
          data.kpis?.average_completion_time_minutes !== undefined
            ? Number(data.kpis.average_completion_time_minutes)
            : null,
        completed_services_count: this.asNumber(data.kpis?.completed_services_count),
        services_without_operator: this.asNumber(data.kpis?.services_without_operator),
        services_without_location: this.asNumber(data.kpis?.services_without_location),
        stale_tracking_services: this.asNumber(data.kpis?.stale_tracking_services),
        services_exceeding_arrival_threshold: this.asNumber(
          data.kpis?.services_exceeding_arrival_threshold,
        ),
        cancelled_cases: this.asNumber(data.kpis?.cancelled_cases),
        unattended_cases: this.asNumber(data.kpis?.unattended_cases),
        sla_compliance_rate:
          data.kpis?.sla_compliance_rate !== null && data.kpis?.sla_compliance_rate !== undefined
            ? Number(data.kpis.sla_compliance_rate)
            : null,
        sla_met_services: this.asNumber(data.kpis?.sla_met_services),
        sla_evaluated_services: this.asNumber(data.kpis?.sla_evaluated_services),
        tenant_efficiency_score:
          data.kpis?.tenant_efficiency_score !== null &&
          data.kpis?.tenant_efficiency_score !== undefined
            ? Number(data.kpis.tenant_efficiency_score)
            : null,
      },
      kpi_sources: data.kpi_sources ?? [],
      operations: {
        services_by_state: data.operations?.services_by_state ?? [],
        requests_by_status: data.operations?.requests_by_status ?? [],
        incidents_by_severity: data.operations?.incidents_by_severity ?? [],
        incidents_by_detected_specialty: data.operations?.incidents_by_detected_specialty ?? [],
        incidents_by_type: data.operations?.incidents_by_type ?? [],
        incident_zones: data.operations?.incident_zones ?? [],
      },
      financial: {
        total_revenue: this.asNumber(data.financial?.total_revenue),
        confirmed_payments: this.asNumber(data.financial?.confirmed_payments),
        pending_payments: this.asNumber(data.financial?.pending_payments),
        rejected_payments: this.asNumber(data.financial?.rejected_payments),
        average_ticket:
          data.financial?.average_ticket !== null &&
          data.financial?.average_ticket !== undefined
            ? this.asNumber(data.financial.average_ticket)
            : null,
        projected_revenue:
          data.financial?.projected_revenue !== null &&
          data.financial?.projected_revenue !== undefined
            ? this.asNumber(data.financial.projected_revenue)
            : null,
        monthly_revenue: data.financial?.monthly_revenue ?? [],
      },
      operarios: {
        operario_ranking: data.operarios?.operario_ranking ?? [],
      },
      reputation: data.reputation ?? {},
      action_items: data.action_items ?? [],
    };
  }

  private buildEmptyOverview(): DashboardOverviewResponse {
    return {
      period: { date_from: '', date_to: '' },
      kpis: {
        pending_requests: 0,
        accepted_requests: 0,
        rejected_requests: 0,
        expired_requests: 0,
        cancelled_requests: 0,
        active_services: 0,
        completed_services: 0,
        paid_services: 0,
        pending_payments: 0,
        total_revenue: 0,
        average_rating: null,
        first_contact_resolution_rate: null,
        average_assignment_time_minutes: null,
        min_assignment_time_minutes: null,
        max_assignment_time_minutes: null,
        accepted_request_count: 0,
        average_operator_assignment_time_minutes: null,
        unassigned_services_count: 0,
        assigned_services_count: 0,
        average_arrival_time_minutes: null,
        min_arrival_time_minutes: null,
        max_arrival_time_minutes: null,
        arrived_services_count: 0,
        average_acceptance_time_minutes: null,
        average_report_to_workshop_assignment_minutes: null,
        average_operario_assignment_time_minutes: null,
        average_assignment_to_arrival_minutes: null,
        average_completion_time_minutes: null,
        completed_services_count: 0,
        services_without_operator: 0,
        services_without_location: 0,
        stale_tracking_services: 0,
        services_exceeding_arrival_threshold: 0,
        cancelled_cases: 0,
        unattended_cases: 0,
        sla_compliance_rate: null,
        sla_met_services: 0,
        sla_evaluated_services: 0,
        tenant_efficiency_score: null,
      },
      kpi_sources: [],
      operations: {
        services_by_state: [],
        requests_by_status: [],
        incidents_by_severity: [],
        incidents_by_detected_specialty: [],
        incidents_by_type: [],
        incident_zones: [],
      },
      financial: {
        total_revenue: 0,
        confirmed_payments: 0,
        pending_payments: 0,
        rejected_payments: 0,
        average_ticket: null,
        projected_revenue: null,
        monthly_revenue: [],
      },
      operarios: { operario_ranking: [] },
      reputation: {},
      action_items: [],
    };
  }
}

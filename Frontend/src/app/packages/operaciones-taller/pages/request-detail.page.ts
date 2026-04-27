import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { AppCardComponent } from '../../../shared/components/app-card.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state.component';
import { ErrorStateComponent } from '../../../shared/components/error-state.component';
import { LoadingStateComponent } from '../../../shared/components/loading-state.component';
import { PageHeaderComponent } from '../../../shared/components/page-header.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge.component';
import {
  RequestDecisionMode,
  RequestDecisionPanelComponent,
} from '../components/request-decision-panel.component';
import { PrequotationResultCardComponent } from '../components/prequotation-result-card.component';
import { WorkshopRequestsApi } from '../data-access/workshop-requests.api';
import {
  PrequotationDecisionResult,
  WorkshopRequestDecisionRequest,
  WorkshopRequestDecisionResponse,
  WorkshopRequestDetailResponse,
} from '../data-access/workshop-request.models';

type DecisionConflictAction = 'catalog' | null;

@Component({
  selector: 'app-request-detail-page',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    RouterLink,
    PageHeaderComponent,
    AppCardComponent,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    StatusBadgeComponent,
    RequestDecisionPanelComponent,
    PrequotationResultCardComponent,
  ],
  template: `
    <div class="page">
      <app-page-header
        eyebrow="Detalle operativo"
        title="Solicitud del taller"
        subtitle="Revisa la informacion de la solicitud, el resumen IA y la decision administrativa."
      >
        <div page-actions class="toolbar toolbar--tight">
          <a class="app-button app-button--ghost" routerLink="/admin/requests">
            Volver a solicitudes
          </a>
          @if (requestId() > 0) {
            <button
              type="button"
              class="app-button app-button--secondary"
              (click)="loadDetail()"
              [disabled]="loading() || submittingDecision()"
            >
              {{ loading() ? 'Actualizando...' : 'Actualizar' }}
            </button>
          }
        </div>
      </app-page-header>

      @if (loading() && !detail()) {
        <app-loading-state
          title="Cargando detalle"
          message="Consultando la solicitud real del taller."
        />
      } @else if (pageError()) {
        <app-error-state [message]="pageError()">
          @if (requestId() > 0) {
            <button error-actions type="button" class="app-button" (click)="loadDetail()">
              Reintentar
            </button>
          }
        </app-error-state>
      } @else if (detail(); as data) {
        <section class="detail-layout">
          <div class="detail-layout__main">
            <app-card
              title="Resumen de la solicitud"
              subtitle="Datos operativos que el administrador usa para decidir si acepta el caso."
            >
              <div class="summary-grid">
                <div class="summary-item">
                  <span class="text-muted">Solicitud</span>
                  <strong>#{{ data.request_id }}</strong>
                </div>
                <div class="summary-item">
                  <span class="text-muted">Incidente</span>
                  <strong>#{{ data.incident_id }}</strong>
                </div>
                <div class="summary-item">
                  <span class="text-muted">Estado de solicitud</span>
                  <app-status-badge [label]="data.request_status" />
                </div>
                <div class="summary-item">
                  <span class="text-muted">Estado del incidente</span>
                  <strong>{{ data.incident_state }}</strong>
                </div>
                <div class="summary-item">
                  <span class="text-muted">Enviada</span>
                  <strong>{{ formatDate(data.sent_at) }}</strong>
                </div>
                <div class="summary-item">
                  <span class="text-muted">Expira</span>
                  <strong>{{ formatDate(data.expires_at) }}</strong>
                </div>
                <div class="summary-item">
                  <span class="text-muted">Tiempo restante</span>
                  <strong>{{ buildRemainingTimeLabel(data.expires_at) }}</strong>
                </div>
                <div class="summary-item">
                  <span class="text-muted">Distancia</span>
                  <strong>{{ formatDistance(data.distance_km) }}</strong>
                </div>
                <div class="summary-item">
                  <span class="text-muted">Intento</span>
                  <strong>#{{ data.attempt_number }}</strong>
                </div>
                <div class="summary-item">
                  <span class="text-muted">Seguro prioritario</span>
                  <strong>{{ data.used_insurance_priority ? 'Si' : 'No' }}</strong>
                </div>
              </div>
            </app-card>

            <app-card
              title="Diagnostico IA e incidente"
              subtitle="Resumen tecnico del caso segun el triaje y la deteccion de especialidad."
            >
              <div class="detail-copy">
                <div class="summary-grid summary-grid--dense">
                  <div class="summary-item">
                    <span class="text-muted">Especialidad detectada</span>
                    <strong>{{ data.detected_specialty?.nombre || 'Sin detectar' }}</strong>
                  </div>
                  <div class="summary-item">
                    <span class="text-muted">Especialidad reportada</span>
                    <strong>{{ data.client_reported_specialty?.nombre || 'Sin reportar' }}</strong>
                  </div>
                  <div class="summary-item">
                    <span class="text-muted">Severidad</span>
                    <strong>{{ data.severity || 'Sin severidad' }}</strong>
                  </div>
                  <div class="summary-item">
                    <span class="text-muted">Ubicacion</span>
                    <strong>{{ formatCoordinate(data.incident_latitud) }}, {{ formatCoordinate(data.incident_longitud) }}</strong>
                  </div>
                </div>

                <div class="copy-block">
                  <span class="text-muted">Resumen IA</span>
                  <p>{{ data.ai_summary || 'Sin resumen IA disponible.' }}</p>
                </div>

                @if (data.transcripcion_audio) {
                  <div class="copy-block">
                    <span class="text-muted">Transcripcion de audio</span>
                    <p>{{ data.transcripcion_audio }}</p>
                  </div>
                }

                @if (imageLabelsText()) {
                  <div class="copy-block">
                    <span class="text-muted">Etiquetas de imagen</span>
                    <p>{{ imageLabelsText() }}</p>
                  </div>
                }
              </div>
            </app-card>

            <app-card
              title="Scoring y priorizacion"
              subtitle="Puntajes que ayudan a entender por que el caso fue enviado al taller."
            >
              <div class="summary-grid summary-grid--dense">
                <div class="summary-item">
                  <span class="text-muted">Score proximidad</span>
                  <strong>{{ formatNumber(data.score_proximidad) }}</strong>
                </div>
                <div class="summary-item">
                  <span class="text-muted">Score reputacion</span>
                  <strong>{{ formatNumber(data.score_reputacion) }}</strong>
                </div>
                <div class="summary-item">
                  <span class="text-muted">Score total</span>
                  <strong>{{ formatNumber(data.score_total) }}</strong>
                </div>
                <div class="summary-item">
                  <span class="text-muted">Taller asignado</span>
                  <strong>{{ data.workshop.nombre_comercial }}</strong>
                </div>
              </div>
            </app-card>

            @if (currentPrequotation()) {
              <app-prequotation-result-card
                [result]="currentPrequotation()!"
                [showAssignmentLink]="true"
              />
            }
          </div>

          <div class="detail-layout__side">
            <app-card
              title="Decision administrativa"
              subtitle="Acepta o rechaza la solicitud de auxilio."
            >
              <div class="decision-actions">
                <button
                  type="button"
                  class="app-button"
                  (click)="openDecision('accept')"
                  [disabled]="!canDecide() || submittingDecision()"
                >
                  Aceptar
                </button>
                <button
                  type="button"
                  class="app-button app-button--secondary"
                  (click)="openDecision('reject')"
                  [disabled]="!canDecide() || submittingDecision()"
                >
                  Rechazar
                </button>
              </div>

              @if (!canDecide()) {
                <p class="text-muted side-note">
                  Esta solicitud ya no se encuentra pendiente para nuevas decisiones.
                </p>
              }

              @if (decisionMode()) {
                <div class="decision-panel-wrap">
                  <app-request-decision-panel
                    [mode]="decisionMode()"
                    [submitting]="submittingDecision()"
                    [errorMessage]="decisionError()"
                    (confirmAccept)="confirmAccept()"
                    (confirmReject)="confirmReject($event)"
                    (cancel)="cancelDecision()"
                  />
                </div>
              }

              @if (decisionConflictAction() === 'catalog') {
                <div class="decision-help">
                  <a class="app-button app-button--secondary" routerLink="/admin/workshop/catalog">
                    Ir al catalogo
                  </a>
                </div>
              }
            </app-card>

            @if (successMessage()) {
              <app-card title="Resultado" subtitle="Ultima accion procesada correctamente.">
                <p class="feedback feedback--success">{{ successMessage() }}</p>
              </app-card>
            }
          </div>
        </section>
      } @else {
        <app-empty-state
          title="Solicitud no disponible"
          message="No se encontró información para esta solicitud."
        />
      }
    </div>
  `,
  styles: [
    `
      .toolbar--tight {
        justify-content: flex-end;
      }

      .detail-layout {
        display: grid;
        gap: var(--space-5);
        grid-template-columns: minmax(0, 1.65fr) minmax(300px, 0.95fr);
        align-items: start;
      }

      .detail-layout__main,
      .detail-layout__side {
        min-width: 0;
        display: flex;
        flex-direction: column;
        gap: var(--space-5);
      }

      .summary-grid {
        display: grid;
        gap: var(--space-4);
        grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      }

      .summary-grid--dense {
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      }

      .summary-item {
        display: flex;
        flex-direction: column;
        gap: var(--space-2);
      }

      .detail-copy {
        display: flex;
        flex-direction: column;
        gap: var(--space-5);
      }

      .copy-block p {
        margin: var(--space-2) 0 0;
        line-height: 1.6;
      }

      .decision-actions {
        display: flex;
        gap: var(--space-3);
        flex-wrap: wrap;
      }

      .decision-panel-wrap,
      .decision-help {
        margin-top: var(--space-5);
      }

      .side-note,
      .feedback {
        margin: var(--space-4) 0 0;
      }

      .feedback--success {
        color: var(--color-success);
      }

      @media (max-width: 980px) {
        .detail-layout {
          grid-template-columns: 1fr;
        }
      }
    `,
  ],
})
export class RequestDetailPage {
  private readonly api = inject(WorkshopRequestsApi);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly loading = signal(false);
  protected readonly submittingDecision = signal(false);
  protected readonly pageError = signal('');
  protected readonly decisionError = signal('');
  protected readonly successMessage = signal('');
  protected readonly decisionConflictAction = signal<DecisionConflictAction>(null);
  protected readonly detail = signal<WorkshopRequestDetailResponse | null>(null);
  protected readonly decisionMode = signal<RequestDecisionMode>(null);
  protected readonly decisionResult = signal<PrequotationDecisionResult | null>(null);
  protected readonly requestId = signal(0);

  protected readonly canDecide = computed(
    () => this.detail()?.request_status === 'PENDIENTE',
  );

  protected readonly currentPrequotation = computed(() => {
    if (this.decisionResult()) {
      return this.decisionResult();
    }

    const data = this.detail();
    if (!data) {
      return null;
    }

    const hasValues =
      Boolean(data.prequotation_code) ||
      (data.prequotation_min !== null && data.prequotation_min !== undefined) ||
      (data.prequotation_max !== null && data.prequotation_max !== undefined) ||
      Boolean(data.service_id);

    if (!hasValues) {
      return null;
    }

    return {
      service_id: data.service_id,
      service_state: data.service_state,
      prequotation_code: data.prequotation_code,
      prequotation_min: data.prequotation_min,
      prequotation_max: data.prequotation_max,
      prequotation_currency: data.prequotation_currency,
      catalog_service_name: data.catalog_service_name,
      message: data.motivo_cierre,
    };
  });

  protected readonly imageLabelsText = computed(() => {
    const labels = this.detail()?.image_labels;
    if (!labels) {
      return '';
    }

    if (Array.isArray(labels)) {
      return labels.join(', ');
    }

    return JSON.stringify(labels);
  });

  constructor() {
    this.route.paramMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      const parsedId = this.parsePositiveId(params.get('requestId'));
      this.requestId.set(parsedId);
      this.decisionMode.set(null);
      this.decisionError.set('');
      this.decisionConflictAction.set(null);
      this.successMessage.set('');
      this.decisionResult.set(null);

      if (parsedId <= 0) {
        this.detail.set(null);
        this.pageError.set('El identificador de la solicitud no es valido.');
        this.loading.set(false);
        return;
      }

      this.loadDetail();
    });
  }

  protected loadDetail(): void {
    const currentRequestId = this.requestId();
    if (!this.isPositiveInteger(currentRequestId)) {
      this.pageError.set('El identificador de la solicitud no es valido.');
      return;
    }

    this.loading.set(true);
    this.pageError.set('');

    this.api
      .getRequestDetail(currentRequestId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.detail.set(response);
          this.loading.set(false);
        },
        error: (error) => {
          this.pageError.set(
            this.mapGenericError(
              error,
              'No se pudo cargar el detalle de la solicitud.',
            ),
          );
          this.loading.set(false);
        },
      });
  }

  protected openDecision(mode: RequestDecisionMode): void {
    if (!this.canDecide()) {
      return;
    }

    this.decisionMode.set(mode);
    this.decisionError.set('');
    this.decisionConflictAction.set(null);
    this.successMessage.set('');
  }

  protected cancelDecision(): void {
    this.decisionMode.set(null);
    this.decisionError.set('');
    this.decisionConflictAction.set(null);
  }

  protected confirmAccept(): void {
    const currentRequestId = this.requestId();
    if (!this.isPositiveInteger(currentRequestId)) {
      this.decisionError.set('La solicitud seleccionada no es valida.');
      return;
    }

    this.submitDecision(currentRequestId, { decision: 'ACEPTAR' });
  }

  protected confirmReject(reason: string): void {
    const currentRequestId = this.requestId();
    if (!this.isPositiveInteger(currentRequestId)) {
      this.decisionError.set('La solicitud seleccionada no es valida.');
      return;
    }

    const payload = this.buildRejectPayload(reason);
    if (!payload) {
      this.decisionError.set('Ingresa un motivo valido antes de rechazar.');
      return;
    }

    this.submitDecision(currentRequestId, payload);
  }

  protected formatDate(value: string): string {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }

    return new Intl.DateTimeFormat('es-BO', {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(date);
  }

  protected formatDistance(value: string | number): string {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
      return 'No disponible';
    }

    return `${new Intl.NumberFormat('es-BO', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(numeric)} km`;
  }

  protected formatCoordinate(value: string | number): string {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
      return String(value ?? 'No disponible');
    }

    return new Intl.NumberFormat('es-BO', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 6,
    }).format(numeric);
  }

  protected formatNumber(value: string | number | null | undefined): string {
    if (value === null || value === undefined || value === '') {
      return 'No disponible';
    }

    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
      return String(value);
    }

    return new Intl.NumberFormat('es-BO', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(numeric);
  }

  protected buildRemainingTimeLabel(expiresAt: string): string {
    const expiration = new Date(expiresAt);
    if (Number.isNaN(expiration.getTime())) {
      return 'No disponible';
    }

    const deltaMs = expiration.getTime() - Date.now();
    if (deltaMs <= 0) {
      return 'Expirada';
    }

    const totalMinutes = Math.floor(deltaMs / 60000);
    if (totalMinutes < 1) {
      return 'Menos de 1 min';
    }

    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;

    if (hours <= 0) {
      return `${minutes} min`;
    }

    return `${hours} h ${minutes} min`;
  }

  private submitDecision(
    requestId: number,
    payload: WorkshopRequestDecisionRequest,
  ): void {
    this.submittingDecision.set(true);
    this.decisionError.set('');
    this.decisionConflictAction.set(null);

    this.api
      .decideRequest(requestId, payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.submittingDecision.set(false);
          this.handleDecisionSuccess(response);
        },
        error: (error) => {
          const mapped = this.mapDecisionError(error);
          this.decisionError.set(mapped.message);
          this.decisionConflictAction.set(mapped.action);
          this.submittingDecision.set(false);
        },
      });
  }

  private handleDecisionSuccess(response: WorkshopRequestDecisionResponse): void {
    this.successMessage.set(response.message || 'Decision registrada correctamente.');
    this.decisionMode.set(null);

    if (response.request_status === 'ACEPTADA') {
      const currentDetail = this.detail();
      this.decisionResult.set({
        service_id: response.service_id,
        service_state: response.service_state,
        prequotation_code: response.prequotation_code,
        prequotation_min: response.prequotation_min,
        prequotation_max: response.prequotation_max,
        prequotation_currency: response.prequotation_currency,
        catalog_service_name: response.catalog_service_name,
        message: response.message,
      });

      if (currentDetail) {
        this.detail.set({
          ...currentDetail,
          request_status: response.request_status,
          incident_state: response.incident_new_state,
          service_id: response.service_id ?? null,
          service_state: response.service_state ?? null,
          prequotation_code: response.prequotation_code ?? null,
          prequotation_min: response.prequotation_min ?? null,
          prequotation_max: response.prequotation_max ?? null,
          prequotation_currency: response.prequotation_currency ?? null,
          catalog_service_name: response.catalog_service_name ?? null,
          motivo_cierre: response.message,
        });
      }
    }

    if (response.request_status === 'RECHAZADA') {
      this.router.navigate(['/admin/requests']);
      return;
    }
  }

  private buildRejectPayload(
    reason: string,
  ): WorkshopRequestDecisionRequest | null {
    const trimmed = reason.trim();
    if (trimmed.length < 5) {
      return null;
    }

    return {
      decision: 'RECHAZAR',
      motivo: trimmed,
    };
  }

  private parsePositiveId(rawValue: string | null): number {
    if (!rawValue || !/^\d+$/.test(rawValue)) {
      return 0;
    }

    const parsed = Number(rawValue);
    return Number.isInteger(parsed) && parsed > 0 ? parsed : 0;
  }

  private mapDecisionError(
    error: unknown,
  ): { message: string; action: DecisionConflictAction } {
    const raw = this.extractDetail(error);
    const normalized = raw.toLowerCase();

    if (
      normalized.includes('no active catalog service matches') ||
      normalized.includes('configure cu26 catalog before accepting')
    ) {
      return {
        message:
          'No existe un servicio activo en el catalogo para la especialidad detectada. Configura CU26 antes de aceptar esta solicitud.',
        action: 'catalog',
      };
    }

    if (normalized.includes('triage') || normalized.includes('manual review')) {
      return {
        message:
          'El diagnostico IA todavia no esta listo para generar la pre-cotizacion tecnica.',
        action: null,
      };
    }

    if (normalized.includes('expired')) {
      return {
        message: 'La solicitud ya expiro y no puede ser decidida.',
        action: null,
      };
    }

    if (normalized.includes('no longer pending')) {
      return {
        message: 'La solicitud ya no se encuentra pendiente.',
        action: null,
      };
    }

    return {
      message: raw || 'No se pudo registrar la decision de la solicitud.',
      action: null,
    };
  }

  private mapGenericError(error: unknown, fallback: string): string {
    const raw = this.extractDetail(error);
    if (raw) {
      return raw;
    }

    if (error instanceof HttpErrorResponse) {
      if (error.status === 403) {
        return 'No tienes permisos para revisar esta solicitud.';
      }

      if (error.status === 404) {
        return 'La solicitud indicada no fue encontrada para este taller.';
      }
    }

    return fallback;
  }

  private extractDetail(error: unknown): string {
    if (error instanceof HttpErrorResponse) {
      const detail = error.error?.detail;

      if (typeof detail === 'string' && detail.trim()) {
        return detail.trim();
      }

      if (Array.isArray(detail)) {
        const messages = detail
          .map((item) => {
            if (typeof item === 'string') {
              return item;
            }
            if (item && typeof item === 'object' && 'msg' in item) {
              return String((item as { msg?: unknown }).msg ?? '');
            }
            return '';
          })
          .filter(Boolean);

        if (messages.length) {
          return messages.join(' ');
        }
      }

      if (typeof error.error === 'string' && error.error.trim()) {
        return error.error.trim();
      }
    }

    if (error instanceof Error && error.message.trim()) {
      return error.message.trim();
    }

    return '';
  }

  private isPositiveInteger(value: number | null): value is number {
    return typeof value === 'number' && Number.isInteger(value) && value > 0;
  }
}

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
import { RouterLink } from '@angular/router';

import { AppCardComponent } from '../../../shared/components/app-card.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state.component';
import { ErrorStateComponent } from '../../../shared/components/error-state.component';
import { LoadingStateComponent } from '../../../shared/components/loading-state.component';
import { PageHeaderComponent } from '../../../shared/components/page-header.component';
import { PendingRequestCardComponent } from '../components/pending-request-card.component';
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
  WorkshopRequestSummary,
} from '../data-access/workshop-request.models';

type DecisionConflictAction = 'catalog' | null;

@Component({
  selector: 'app-pending-requests-page',
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
    PendingRequestCardComponent,
    RequestDecisionPanelComponent,
    PrequotationResultCardComponent,
  ],
  template: `
    <div class="page">
      <app-page-header
        eyebrow="Flujo de aceptacion"
        title="Solicitudes pendientes"
        subtitle="Revisa solicitudes entrantes, diagnostico IA y decide si el taller puede atenderlas."
      >
        <div page-actions class="toolbar toolbar--tight">
          <span class="badge badge--info">{{ requests().length }} pendiente(s)</span>
          <button
            type="button"
            class="app-button app-button--ghost"
            (click)="reload()"
            [disabled]="loading() || submittingDecision()"
          >
            {{ loading() ? 'Actualizando...' : 'Actualizar' }}
          </button>
        </div>
      </app-page-header>

      @if (successMessage()) {
        <app-card
          title="Operacion completada"
          subtitle="Resultado de la última decisión enviada."
        >
          <p class="feedback feedback--success">{{ successMessage() }}</p>
        </app-card>
      }

      @if (acceptedResult()) {
        <app-prequotation-result-card [result]="acceptedResult()!" />
      }

      @if (loading() && !requests().length) {
        <app-loading-state
          title="Cargando solicitudes"
          message="Consultando solicitudes pendientes reales del taller."
        />
      } @else if (pageError() && !requests().length) {
        <app-error-state [message]="pageError()">
          <button error-actions type="button" class="app-button" (click)="reload()">
            Reintentar
          </button>
        </app-error-state>
      } @else if (!requests().length) {
        <app-empty-state
          title="Sin solicitudes pendientes"
          message="No hay solicitudes pendientes en este momento."
        />
      } @else {
        <section class="request-list">
          @for (item of requests(); track item.request_id) {
            <div class="request-list__item">
              <app-pending-request-card
                [request]="item"
                (accept)="openDecision(item, 'accept')"
                (reject)="openDecision(item, 'reject')"
              />

              @if (selectedRequestId() === item.request_id && decisionMode()) {
                <app-card
                  title="Decision de la solicitud"
                  subtitle="Confirma la acción antes de continuar."
                >
                  <app-request-decision-panel
                    [mode]="decisionMode()"
                    [submitting]="submittingDecision()"
                    [errorMessage]="decisionError()"
                    (confirmAccept)="confirmAccept()"
                    (confirmReject)="confirmReject($event)"
                    (cancel)="cancelDecision()"
                  />

                  @if (decisionConflictAction() === 'catalog') {
                    <div class="decision-help">
                      <a
                        class="app-button app-button--secondary"
                        routerLink="/admin/workshop/catalog"
                      >
                        Ir al catalogo
                      </a>
                    </div>
                  }
                </app-card>
              }
            </div>
          }
        </section>
      }
    </div>
  `,
  styles: [
    `
      .toolbar--tight {
        justify-content: flex-end;
      }

      .request-list {
        display: flex;
        flex-direction: column;
        gap: var(--space-5);
      }

      .request-list__item {
        display: flex;
        flex-direction: column;
        gap: var(--space-4);
      }

      .feedback {
        margin: 0;
        font-size: 0.92rem;
        line-height: 1.5;
      }

      .feedback--success {
        color: var(--color-success);
      }

      .decision-help {
        margin-top: var(--space-4);
      }
    `,
  ],
})
export class PendingRequestsPage {
  private readonly api = inject(WorkshopRequestsApi);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly loading = signal(false);
  protected readonly submittingDecision = signal(false);
  protected readonly pageError = signal('');
  protected readonly decisionError = signal('');
  protected readonly successMessage = signal('');
  protected readonly decisionConflictAction = signal<DecisionConflictAction>(null);
  protected readonly requests = signal<WorkshopRequestSummary[]>([]);
  protected readonly selectedRequest = signal<WorkshopRequestSummary | null>(null);
  protected readonly decisionMode = signal<RequestDecisionMode>(null);
  protected readonly acceptedResult = signal<PrequotationDecisionResult | null>(null);

  protected readonly selectedRequestId = computed(
    () => this.selectedRequest()?.request_id ?? null,
  );

  constructor() {
    this.reload();
  }

  protected reload(): void {
    this.loading.set(true);
    this.pageError.set('');
    this.successMessage.set('');
    this.decisionError.set('');
    this.decisionConflictAction.set(null);

    this.api
      .listPendingRequests()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.requests.set(response);
          this.loading.set(false);
        },
        error: (error) => {
          this.pageError.set(
            this.mapGenericError(
              error,
              'No se pudieron cargar las solicitudes pendientes.',
            ),
          );
          this.loading.set(false);
        },
      });
  }

  protected openDecision(
    request: WorkshopRequestSummary,
    mode: RequestDecisionMode,
  ): void {
    this.selectedRequest.set(request);
    this.decisionMode.set(mode);
    this.decisionError.set('');
    this.decisionConflictAction.set(null);
    this.successMessage.set('');
  }

  protected cancelDecision(): void {
    this.decisionMode.set(null);
    this.decisionError.set('');
    this.decisionConflictAction.set(null);
    this.selectedRequest.set(null);
  }

  protected confirmAccept(): void {
    const requestId = this.selectedRequestId();
    if (!this.isPositiveInteger(requestId)) {
      this.decisionError.set('La solicitud seleccionada no es valida.');
      return;
    }

    this.submitDecision(requestId, this.buildAcceptPayload());
  }

  protected confirmReject(reason: string): void {
    const requestId = this.selectedRequestId();
    if (!this.isPositiveInteger(requestId)) {
      this.decisionError.set('La solicitud seleccionada no es valida.');
      return;
    }

    const payload = this.buildRejectPayload(reason);
    if (!payload) {
      this.decisionError.set('Ingresa un motivo valido antes de rechazar.');
      return;
    }

    this.submitDecision(requestId, payload);
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
    this.requests.update((items) =>
      items.filter((item) => item.request_id !== response.request_id),
    );

    if (response.request_status === 'ACEPTADA') {
      this.acceptedResult.set({
        service_id: response.service_id,
        service_state: response.service_state,
        prequotation_code: response.prequotation_code,
        prequotation_min: response.prequotation_min,
        prequotation_max: response.prequotation_max,
        prequotation_currency: response.prequotation_currency,
        catalog_service_name: response.catalog_service_name,
        message: response.message,
      });
    } else {
      this.acceptedResult.set(null);
    }

    this.cancelDecision();
  }

  private buildAcceptPayload(): WorkshopRequestDecisionRequest {
    return { decision: 'ACEPTAR' };
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

    if (error instanceof HttpErrorResponse && error.status === 403) {
      return 'No tienes permisos para revisar las solicitudes del taller.';
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

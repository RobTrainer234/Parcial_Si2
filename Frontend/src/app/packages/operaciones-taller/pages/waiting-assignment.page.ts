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

import { AppCardComponent } from '../../../shared/components/app-card.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state.component';
import { ErrorStateComponent } from '../../../shared/components/error-state.component';
import { LoadingStateComponent } from '../../../shared/components/loading-state.component';
import { PageHeaderComponent } from '../../../shared/components/page-header.component';
import { AssignmentConfirmationPanelComponent } from '../components/assignment-confirmation-panel.component';
import { OperarioCandidatesTableComponent } from '../components/operario-candidates-table.component';
import { WaitingServiceCardComponent } from '../components/waiting-service-card.component';
import { WorkshopAssignmentApi } from '../data-access/workshop-assignment.api';
import {
  AssignOperarioResponse,
  OperarioCandidateSummary,
  WaitingAssignmentServiceSummary,
} from '../data-access/workshop-assignment.models';

@Component({
  selector: 'app-waiting-assignment-page',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    PageHeaderComponent,
    AppCardComponent,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    WaitingServiceCardComponent,
    OperarioCandidatesTableComponent,
    AssignmentConfirmationPanelComponent,
  ],
  template: `
    <div class="page">
      <app-page-header
        eyebrow="Coordinacion de campo"
        title="Asignacion de operarios"
        subtitle="Asigna tecnicos compatibles a servicios aceptados y pendientes de atencion."
      >
        <div page-actions class="toolbar toolbar--tight">
          <span class="badge badge--info">{{ services().length }} en espera</span>
          <button
            type="button"
            class="app-button app-button--ghost"
            (click)="reload()"
            [disabled]="loading() || candidatesLoading() || assignmentLoading()"
          >
            {{ loading() ? 'Actualizando...' : 'Actualizar' }}
          </button>
        </div>
      </app-page-header>

      @if (successMessage()) {
        <app-card title="Asignación registrada" subtitle="La asignación del operario fue confirmada.">
          <p class="feedback feedback--success">{{ successMessage() }}</p>
          @if (lastAssignment()) {
            <div class="assignment-result">
              <span class="text-muted">Servicio #{{ lastAssignment()!.service_id }}</span>
              <strong>{{ lastAssignment()!.assigned_operario.nombre_completo }}</strong>
            </div>
          }
        </app-card>
      }

      @if (loading() && !services().length) {
        <app-loading-state
          title="Cargando servicios"
          message="Consultando servicios aceptados que esperan asignacion."
        />
      } @else if (pageError() && !services().length) {
        <app-error-state [message]="pageError()">
          <button error-actions type="button" class="app-button" (click)="reload()">
            Reintentar
          </button>
        </app-error-state>
      } @else if (!services().length) {
        <app-empty-state
          title="Sin servicios en espera"
          message="No hay servicios aceptados pendientes de asignacion para este taller."
        />
      } @else {
        <section class="assignment-layout">
          <div class="assignment-layout__main">
            <app-card
              title="Servicios pendientes de asignacion"
              subtitle="Selecciona un servicio para revisar candidatos compatibles."
            >
              <div class="service-list">
                @for (service of services(); track service.service_id) {
                  <app-waiting-service-card
                    [service]="service"
                    [selected]="selectedServiceId() === service.service_id"
                    (viewCandidates)="selectService(service)"
                  />
                }
              </div>
            </app-card>
          </div>

          <div class="assignment-layout__side">
            @if (selectedService(); as service) {
              <app-card
                title="Candidatos compatibles"
                subtitle="Carga operarios reales del taller segun especialidad y disponibilidad."
              >
                <div class="panel-heading">
                  <div>
                    <strong>Servicio #{{ service.service_id }}</strong>
                    <p class="text-muted">
                      {{ service.detected_specialty?.nombre || 'Sin especialidad detectada' }}
                    </p>
                  </div>
                  <button
                    type="button"
                    class="app-button app-button--secondary"
                    (click)="clearSelection()"
                    [disabled]="candidatesLoading() || assignmentLoading()"
                  >
                    Cerrar
                  </button>
                </div>

                <app-operario-candidates-table
                  [candidates]="candidates()"
                  [loading]="candidatesLoading()"
                  [errorMessage]="candidatesError()"
                  (assign)="openAssignmentConfirmation($event)"
                />

                @if (selectedCandidate()) {
                  <div class="confirmation-wrap">
                    <app-assignment-confirmation-panel
                      [service]="service"
                      [candidate]="selectedCandidate()!"
                      [submitting]="assignmentLoading()"
                      [errorMessage]="assignmentError()"
                      (confirm)="confirmAssignment()"
                      (cancel)="cancelAssignmentConfirmation()"
                    />
                  </div>
                }
              </app-card>
            } @else {
              <app-card
                title="Panel de asignacion"
                subtitle="Elige un servicio para cargar candidatos reales del taller."
              >
                <app-empty-state
                  title="Sin servicio seleccionado"
                  message="Selecciona un servicio desde la lista para revisar operarios compatibles."
                />
              </app-card>
            }
          </div>
        </section>
      }
    </div>
  `,
  styles: [
    `
      .toolbar--tight {
        justify-content: flex-end;
      }

      .assignment-layout {
        display: grid;
        gap: var(--space-5);
        grid-template-columns: minmax(0, 1.45fr) minmax(320px, 1fr);
        align-items: start;
      }

      .assignment-layout__main,
      .assignment-layout__side {
        min-width: 0;
      }

      .service-list {
        display: flex;
        flex-direction: column;
        gap: var(--space-4);
      }

      .panel-heading {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: var(--space-4);
        flex-wrap: wrap;
        margin-bottom: var(--space-5);
      }

      .panel-heading p {
        margin: var(--space-2) 0 0;
      }

      .confirmation-wrap {
        margin-top: var(--space-5);
      }

      .feedback {
        margin: 0;
      }

      .feedback--success {
        color: var(--color-success);
      }

      .assignment-result {
        display: flex;
        flex-direction: column;
        gap: var(--space-2);
        margin-top: var(--space-4);
      }

      @media (max-width: 1100px) {
        .assignment-layout {
          grid-template-columns: 1fr;
        }
      }
    `,
  ],
})
export class WaitingAssignmentPage {
  private readonly api = inject(WorkshopAssignmentApi);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly loading = signal(false);
  protected readonly candidatesLoading = signal(false);
  protected readonly assignmentLoading = signal(false);
  protected readonly pageError = signal('');
  protected readonly candidatesError = signal('');
  protected readonly assignmentError = signal('');
  protected readonly successMessage = signal('');
  protected readonly services = signal<WaitingAssignmentServiceSummary[]>([]);
  protected readonly candidates = signal<OperarioCandidateSummary[]>([]);
  protected readonly selectedService = signal<WaitingAssignmentServiceSummary | null>(null);
  protected readonly selectedCandidate = signal<OperarioCandidateSummary | null>(null);
  protected readonly lastAssignment = signal<AssignOperarioResponse | null>(null);

  protected readonly selectedServiceId = computed(
    () => this.selectedService()?.service_id ?? null,
  );

  constructor() {
    this.reload();
  }

  protected reload(): void {
    this.loading.set(true);
    this.pageError.set('');
    this.successMessage.set('');
    this.api
      .listWaitingAssignmentServices()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.services.set(response);
          const currentServiceId = this.selectedServiceId();

          if (
            currentServiceId &&
            !response.some((item) => item.service_id === currentServiceId)
          ) {
            this.clearSelection();
          } else if (currentServiceId) {
            const refreshed = response.find(
              (item) => item.service_id === currentServiceId,
            );
            if (refreshed) {
              this.selectedService.set(refreshed);
            }
          }

          this.loading.set(false);
        },
        error: (error) => {
          this.pageError.set(
            this.mapGenericError(
              error,
              'No se pudieron cargar los servicios pendientes de asignacion.',
            ),
          );
          this.loading.set(false);
        },
      });
  }

  protected selectService(service: WaitingAssignmentServiceSummary): void {
    if (!this.isPositiveInteger(service.service_id)) {
      this.candidatesError.set('El servicio seleccionado no es valido.');
      return;
    }

    this.selectedService.set(service);
    this.selectedCandidate.set(null);
    this.assignmentError.set('');
    this.candidatesError.set('');
    this.loadCandidates(service.service_id);
  }

  protected clearSelection(): void {
    this.selectedService.set(null);
    this.selectedCandidate.set(null);
    this.candidates.set([]);
    this.candidatesError.set('');
    this.assignmentError.set('');
    this.candidatesLoading.set(false);
    this.assignmentLoading.set(false);
  }

  protected openAssignmentConfirmation(
    candidate: OperarioCandidateSummary,
  ): void {
    this.selectedCandidate.set(candidate);
    this.assignmentError.set('');
  }

  protected cancelAssignmentConfirmation(): void {
    this.selectedCandidate.set(null);
    this.assignmentError.set('');
  }

  protected confirmAssignment(): void {
    const service = this.selectedService();
    const candidate = this.selectedCandidate();

    if (!service || !candidate) {
      this.assignmentError.set('Selecciona un servicio y un operario validos.');
      return;
    }

    const serviceId = service.service_id;
    const operarioId = candidate.id_persona_operario;
    if (!this.isPositiveInteger(serviceId) || !this.isPositiveInteger(operarioId)) {
      this.assignmentError.set('Los identificadores de asignacion no son validos.');
      return;
    }

    this.assignmentLoading.set(true);
    this.assignmentError.set('');

    this.api
      .assignOperario(serviceId, operarioId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.assignmentLoading.set(false);
          this.lastAssignment.set(response);
          this.successMessage.set(
            response.message || 'Operario asignado correctamente al servicio.',
          );
          this.selectedCandidate.set(null);
          this.reload();
        },
        error: (error) => {
          this.assignmentError.set(this.mapAssignmentError(error));
          this.assignmentLoading.set(false);
        },
      });
  }

  private loadCandidates(serviceId: number): void {
    this.candidatesLoading.set(true);
    this.candidatesError.set('');
    this.candidates.set([]);

    this.api
      .listOperarioCandidates(serviceId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.candidates.set(response);
          this.candidatesLoading.set(false);
        },
        error: (error) => {
          this.candidatesError.set(
            this.mapGenericError(
              error,
              'No se pudieron cargar los candidatos para el servicio seleccionado.',
            ),
          );
          this.candidatesLoading.set(false);
        },
      });
  }

  private mapAssignmentError(error: unknown): string {
    const raw = this.extractDetail(error);
    const normalized = raw.toLowerCase();

    if (normalized.includes('no longer waiting assignment')) {
      return 'El servicio ya no esta en espera de asignacion.';
    }

    if (normalized.includes('not currently available')) {
      return 'El operario seleccionado ya no esta disponible.';
    }

    if (normalized.includes('candidate not found for this workshop')) {
      return 'El operario no pertenece a este taller.';
    }

    if (normalized.includes('does not match the detected specialty')) {
      return 'El operario no cubre la especialidad detectada.';
    }

    if (normalized.includes('not eligible for operario assignment')) {
      return 'Actualiza la lista e intenta nuevamente.';
    }

    return raw || 'No se pudo asignar el operario seleccionado.';
  }

  private mapGenericError(error: unknown, fallback: string): string {
    const raw = this.extractDetail(error);
    if (raw) {
      return raw;
    }

    if (error instanceof HttpErrorResponse) {
      if (error.status === 403) {
        return 'No tienes permisos para asignar operarios en este taller.';
      }

      if (error.status === 404) {
        return 'El servicio solicitado no fue encontrado para este taller.';
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

  private isPositiveInteger(value: number | null | undefined): value is number {
    return typeof value === 'number' && Number.isInteger(value) && value > 0;
  }
}

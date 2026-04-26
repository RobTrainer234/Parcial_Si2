import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  output,
} from '@angular/core';
import { RouterLink } from '@angular/router';

import { StatusBadgeComponent } from '../../../shared/components/status-badge.component';
import { WorkshopRequestSummary } from '../data-access/workshop-request.models';

@Component({
  selector: 'app-pending-request-card',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, RouterLink, StatusBadgeComponent],
  template: `
    <article class="request-card">
      <div class="request-card__header">
        <div class="request-card__title">
          <strong>Solicitud #{{ request().request_id }}</strong>
          <span class="text-muted">Incidente #{{ request().incident_id }}</span>
        </div>

        <div class="request-card__badges">
          <app-status-badge [label]="request().request_status" />
          @if (severityLabel()) {
            <span class="badge badge--warning">{{ severityLabel() }}</span>
          }
          @if (request().used_insurance_priority) {
            <span class="badge badge--info">Seguro</span>
          }
        </div>
      </div>

      <div class="request-card__body">
        <div class="request-card__summary">
          <span class="text-muted">Resumen IA</span>
          <p>{{ request().ai_summary || 'Sin resumen IA disponible.' }}</p>
        </div>

        <div class="request-card__grid">
          <div class="request-card__item">
            <span class="text-muted">Especialidad detectada</span>
            <strong>{{ request().detected_specialty?.nombre || 'Sin detectar' }}</strong>
          </div>
          <div class="request-card__item">
            <span class="text-muted">Tiempo restante</span>
            <strong>{{ remainingTimeLabel() }}</strong>
          </div>
          <div class="request-card__item">
            <span class="text-muted">Intento</span>
            <strong>#{{ request().attempt_number }}</strong>
          </div>
          <div class="request-card__item">
            <span class="text-muted">Score total</span>
            <strong>{{ formatNumber(request().score_total) }}</strong>
          </div>
          <div class="request-card__item">
            <span class="text-muted">Distancia</span>
            <strong>{{ formatDistance(request().distance_km) }}</strong>
          </div>
          <div class="request-card__item">
            <span class="text-muted">Enviada</span>
            <strong>{{ formatDate(request().sent_at) }}</strong>
          </div>
        </div>
      </div>

      <div class="request-card__actions">
        <a
          class="app-button app-button--ghost"
          [routerLink]="['/admin/requests', request().request_id]"
        >
          Ver detalle
        </a>
        <button
          type="button"
          class="app-button"
          (click)="accept.emit(request())"
        >
          Aceptar
        </button>
        <button
          type="button"
          class="app-button app-button--secondary"
          (click)="reject.emit(request())"
        >
          Rechazar
        </button>
      </div>
    </article>
  `,
  styles: [
    `
      .request-card {
        display: flex;
        flex-direction: column;
        gap: var(--space-5);
        padding: var(--space-5);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-lg);
        background: color-mix(in srgb, var(--color-surface-soft) 92%, transparent);
      }

      .request-card__header,
      .request-card__actions {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: var(--space-4);
        flex-wrap: wrap;
      }

      .request-card__title {
        display: flex;
        flex-direction: column;
        gap: var(--space-1);
      }

      .request-card__badges {
        display: flex;
        align-items: center;
        gap: var(--space-3);
        flex-wrap: wrap;
      }

      .request-card__summary p {
        margin: var(--space-2) 0 0;
        line-height: 1.6;
      }

      .request-card__grid {
        display: grid;
        gap: var(--space-4);
        grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
        margin-top: var(--space-5);
      }

      .request-card__item {
        display: flex;
        flex-direction: column;
        gap: var(--space-2);
      }

      .request-card__actions {
        justify-content: flex-end;
      }
    `,
  ],
})
export class PendingRequestCardComponent {
  readonly request = input.required<WorkshopRequestSummary>();
  readonly accept = output<WorkshopRequestSummary>();
  readonly reject = output<WorkshopRequestSummary>();

  protected readonly severityLabel = computed(() => {
    const value = this.request().severity;
    return typeof value === 'string' && value.trim() ? value : null;
  });

  protected readonly remainingTimeLabel = computed(() =>
    this.buildRemainingTimeLabel(this.request().expires_at),
  );

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

  protected formatNumber(value: string | number | null | undefined): string {
    if (value === null || value === undefined || value === '') {
      return 'Sin score';
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

  private buildRemainingTimeLabel(expiresAt: string): string {
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
}

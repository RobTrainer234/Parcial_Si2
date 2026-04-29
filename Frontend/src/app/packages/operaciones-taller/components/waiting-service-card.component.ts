import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  output,
} from '@angular/core';

import { StatusBadgeComponent } from '../../../shared/components/status-badge.component';
import { localizeStatusLabel } from '../../../shared/utils/user-facing-text';
import { WaitingAssignmentServiceSummary } from '../data-access/workshop-assignment.models';

@Component({
  selector: 'app-waiting-service-card',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, StatusBadgeComponent],
  template: `
    <article class="service-card" [class.service-card--selected]="selected()">
      <div class="service-card__header">
        <div class="service-card__title">
          <strong>Servicio #{{ service().service_id }}</strong>
          <span class="text-muted">Solicitud #{{ service().request_id }} · Incidente #{{ service().incident_id }}</span>
        </div>

        <div class="service-card__badges">
          <app-status-badge [label]="service().service_state" />
          @if (service().severity) {
            <span class="badge badge--warning">{{ service().severity }}</span>
          }
        </div>
      </div>

      <div class="service-card__summary">
        <div class="service-card__item">
          <span class="text-muted">Especialidad detectada</span>
          <strong>{{ service().detected_specialty?.nombre || 'Sin detectar' }}</strong>
        </div>
        <div class="service-card__item">
          <span class="text-muted">Estado incidente</span>
          <strong>{{ localizeStatus(service().incident_state) }}</strong>
        </div>
        <div class="service-card__item">
          <span class="text-muted">Servicio de catalogo</span>
          <strong>{{ service().catalog_service_name || 'No informado' }}</strong>
        </div>
        <div class="service-card__item">
          <span class="text-muted">Pre-cotizacion</span>
          <strong>{{ prequotationLabel() }}</strong>
        </div>
      </div>

      <div class="service-card__copy">
        <span class="text-muted">Resumen IA</span>
        <p>{{ service().ai_summary || 'Sin resumen IA disponible.' }}</p>
      </div>

      <div class="service-card__actions">
        <button
          type="button"
          class="app-button"
          (click)="viewCandidates.emit(service())"
        >
          {{ selected() ? 'Actualizar candidatos' : 'Ver candidatos' }}
        </button>
      </div>
    </article>
  `,
  styles: [
    `
      .service-card {
        display: flex;
        flex-direction: column;
        gap: var(--space-5);
        padding: var(--space-5);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-lg);
        background: color-mix(in srgb, var(--color-surface-soft) 92%, transparent);
      }

      .service-card--selected {
        border-color: color-mix(in srgb, var(--color-primary) 28%, var(--color-border));
        box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-primary) 22%, transparent);
      }

      .service-card__header,
      .service-card__actions {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: var(--space-4);
        flex-wrap: wrap;
      }

      .service-card__title {
        display: flex;
        flex-direction: column;
        gap: var(--space-1);
      }

      .service-card__badges {
        display: flex;
        align-items: center;
        gap: var(--space-3);
        flex-wrap: wrap;
      }

      .service-card__summary {
        display: grid;
        gap: var(--space-4);
        grid-template-columns: repeat(auto-fit, minmax(165px, 1fr));
      }

      .service-card__item {
        display: flex;
        flex-direction: column;
        gap: var(--space-2);
      }

      .service-card__copy p {
        margin: var(--space-2) 0 0;
        line-height: 1.6;
      }
    `,
  ],
})
export class WaitingServiceCardComponent {
  readonly service = input.required<WaitingAssignmentServiceSummary>();
  readonly selected = input(false);
  readonly viewCandidates = output<WaitingAssignmentServiceSummary>();

  protected readonly prequotationLabel = computed(() => {
    const service = this.service();
    if (service.prequotation_code) {
      const currency = service.prequotation_currency || 'BOB';
      const hasRange =
        service.prequotation_min !== null &&
        service.prequotation_min !== undefined &&
        service.prequotation_max !== null &&
        service.prequotation_max !== undefined;

      if (hasRange) {
        return `${service.prequotation_code} · ${currency} ${this.formatAmount(
          service.prequotation_min,
        )} - ${currency} ${this.formatAmount(service.prequotation_max)}`;
      }

      return service.prequotation_code;
    }

    return 'Sin pre-cotizacion';
  });

  protected localizeStatus(value: string | null | undefined): string {
    return localizeStatusLabel(value || 'Sin estado');
  }

  private formatAmount(value: string | number | null | undefined): string {
    const numeric = Number(value ?? 0);
    return new Intl.NumberFormat('es-BO', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(Number.isFinite(numeric) ? numeric : 0);
  }
}

import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';

import { AppCardComponent } from '../../../shared/components/app-card.component';
import {
  localizeBackendMessage,
  localizeStatusLabel,
} from '../../../shared/utils/user-facing-text';
import { PrequotationDecisionResult } from '../data-access/workshop-request.models';

@Component({
  selector: 'app-prequotation-result-card',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, RouterLink, AppCardComponent],
  template: `
    <app-card
      title="Solicitud aceptada"
      subtitle="Servicio creado y pendiente de asignacion."
    >
      <div class="result-grid">
        @if (result().service_id) {
          <div class="result-item">
            <span class="text-muted">Servicio</span>
            <strong>#{{ result().service_id }}</strong>
          </div>
        }
        @if (result().service_state) {
          <div class="result-item">
            <span class="text-muted">Estado del servicio</span>
            <strong>{{ localizeStatus(result().service_state) }}</strong>
          </div>
        }
        @if (result().prequotation_code) {
          <div class="result-item">
            <span class="text-muted">Codigo de pre-cotizacion</span>
            <strong>{{ result().prequotation_code }}</strong>
          </div>
        }
        @if (result().catalog_service_name) {
          <div class="result-item">
            <span class="text-muted">Servicio de catalogo</span>
            <strong>{{ result().catalog_service_name }}</strong>
          </div>
        }
        @if (result().prequotation_min !== null && result().prequotation_min !== undefined) {
          <div class="result-item">
            <span class="text-muted">Rango minimo</span>
            <strong>{{ formatCurrency(result().prequotation_min) }}</strong>
          </div>
        }
        @if (result().prequotation_max !== null && result().prequotation_max !== undefined) {
          <div class="result-item">
            <span class="text-muted">Rango maximo</span>
            <strong>{{ formatCurrency(result().prequotation_max) }}</strong>
          </div>
        }
        @if (result().prequotation_currency) {
          <div class="result-item">
            <span class="text-muted">Moneda</span>
            <strong>{{ result().prequotation_currency }}</strong>
          </div>
        }
      </div>

      <p class="result-note text-muted">
        La pre-cotizacion es referencial antes del diagnostico fisico del operario.
      </p>

      @if (result().message) {
        <p class="result-message">{{ localizeMessage(result().message) }}</p>
      }

      @if (showAssignmentLink()) {
        <div class="result-actions">
          <a
            class="app-button app-button--secondary"
            routerLink="/admin/services/waiting-assignment"
          >
            Ir a asignaciones
          </a>
        </div>
      }
    </app-card>
  `,
  styles: [
    `
      .result-grid {
        display: grid;
        gap: var(--space-4);
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      }

      .result-item {
        display: flex;
        flex-direction: column;
        gap: var(--space-2);
      }

      .result-note,
      .result-message {
        margin: var(--space-5) 0 0;
      }

      .result-actions {
        margin-top: var(--space-5);
      }
    `,
  ],
})
export class PrequotationResultCardComponent {
  readonly result = input.required<PrequotationDecisionResult>();
  readonly showAssignmentLink = input<boolean>(true);

  protected localizeStatus(value: string | null | undefined): string {
    return localizeStatusLabel(value);
  }

  protected localizeMessage(value: string | null | undefined): string {
    return localizeBackendMessage(value);
  }

  protected formatCurrency(value: string | number | null | undefined): string {
    const numeric = Number(value ?? 0);
    return `BOB ${new Intl.NumberFormat('es-BO', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(Number.isFinite(numeric) ? numeric : 0)}`;
  }
}

import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  effect,
  inject,
  input,
  output,
} from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';

import { NotificationFilters } from '../data-access/notifications.models';

@Component({
  selector: 'app-notification-filter-panel',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, ReactiveFormsModule],
  template: `
    <section class="filter-panel app-card">
      <header class="filter-panel__header">
        <h4>Filtros de Notificaciones</h4>
        <button
          type="button"
          class="app-button app-button--secondary app-button--sm"
          (click)="closePanel.emit()"
        >
          Cerrar
        </button>
      </header>

      <form [formGroup]="filterForm" (ngSubmit)="applyFilters()" class="filter-panel__form">
        <div class="filter-grid">
          <label class="app-field">
            <span class="app-field__label">Estado</span>
            <select class="app-select" formControlName="status">
              <option value="all">Todas</option>
              <option value="unread">No leídas</option>
              <option value="read">Leídas</option>
            </select>
          </label>

          <label class="app-field">
            <span class="app-field__label">Prioridad</span>
            <select class="app-select" formControlName="priority">
              <option value="">Cualquiera</option>
              <option value="CRITICAL">Crítica</option>
              <option value="HIGH">Alta</option>
              <option value="MEDIUM">Media</option>
              <option value="LOW">Baja</option>
            </select>
          </label>

          <label class="app-field">
            <span class="app-field__label">Tipo</span>
            <input type="text" class="app-input" formControlName="type" placeholder="Ej. ALERTA_SISTEMA" />
          </label>

          <label class="app-field">
            <span class="app-field__label">Fecha desde</span>
            <input type="date" class="app-input" formControlName="date_from" />
          </label>

          <label class="app-field">
            <span class="app-field__label">Fecha hasta</span>
            <input type="date" class="app-input" formControlName="date_to" />
          </label>

          <label class="app-field">
            <span class="app-field__label">Servicio ID</span>
            <input type="number" class="app-input" formControlName="service_id" min="1" />
          </label>

          <label class="app-field">
            <span class="app-field__label">Incidente ID</span>
            <input type="number" class="app-input" formControlName="incident_id" min="1" />
          </label>

          <label class="app-field">
            <span class="app-field__label">Solicitud ID</span>
            <input type="number" class="app-input" formControlName="request_id" min="1" />
          </label>
        </div>

        @if (validationError) {
          <p class="feedback feedback--error">{{ validationError }}</p>
        }

        <footer class="filter-panel__actions">
          <button type="submit" class="app-button" [disabled]="filterForm.invalid">
            Aplicar filtros
          </button>
          <button
            type="button"
            class="app-button app-button--secondary"
            (click)="resetFilters()"
          >
            Limpiar filtros
          </button>
        </footer>
      </form>
    </section>
  `,
  styles: [
    `
      .filter-panel {
        padding: var(--space-4);
        margin-bottom: var(--space-4);
        background: color-mix(in srgb, var(--color-surface-soft) 40%, transparent);
        border: 1px solid var(--color-border);
      }

      .filter-panel__header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: var(--space-4);
      }

      .filter-panel__header h4 {
        margin: 0;
        font-size: 1.1rem;
      }

      .filter-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: var(--space-4);
        margin-bottom: var(--space-4);
      }

      .filter-panel__actions {
        display: flex;
        gap: var(--space-3);
        justify-content: flex-end;
        padding-top: var(--space-3);
        border-top: 1px solid var(--color-border);
      }

      .feedback--error {
        color: var(--color-danger);
        margin-bottom: var(--space-3);
        font-size: 0.9rem;
      }
    `,
  ],
})
export class NotificationFilterPanelComponent {
  readonly currentFilters = input<NotificationFilters | null>(null);

  readonly filtersApplied = output<NotificationFilters>();
  readonly closePanel = output<void>();

  protected validationError = '';
  private readonly fb = inject(FormBuilder);

  protected readonly filterForm = this.fb.group({
    status: ['all'],
    type: [''],
    priority: [''],
    date_from: [''],
    date_to: [''],
    service_id: [null as number | null],
    incident_id: [null as number | null],
    request_id: [null as number | null],
  });

  constructor() {
    effect(() => {
      const filters = this.currentFilters();
      if (filters) {
        this.filterForm.patchValue({
          status: filters.status ?? 'all',
          type: filters.type ?? '',
          priority: filters.priority ?? '',
          date_from: filters.date_from ?? '',
          date_to: filters.date_to ?? '',
          service_id: filters.service_id ?? null,
          incident_id: filters.incident_id ?? null,
          request_id: filters.request_id ?? null,
        }, { emitEvent: false });
      } else {
        this.filterForm.reset({ status: 'all' }, { emitEvent: false });
      }
    });
  }

  protected applyFilters(): void {
    if (this.filterForm.invalid) {
      return;
    }

    this.validationError = '';
    const raw = this.filterForm.getRawValue();

    if (raw.date_from && raw.date_to && raw.date_to < raw.date_from) {
      this.validationError = 'La fecha de fin no puede ser anterior a la fecha de inicio.';
      return;
    }

    const payload: NotificationFilters = {};

    if (raw.status && raw.status !== 'all') {
      payload.status = raw.status as 'unread' | 'read';
    }
    if (raw.type) payload.type = raw.type;
    if (raw.priority) payload.priority = raw.priority;
    if (raw.date_from) payload.date_from = raw.date_from;
    if (raw.date_to) payload.date_to = raw.date_to;

    const parsePositiveId = (val: number | string | null | undefined, errorMsg: string): number | undefined => {
      if (val === null || val === undefined || val === '') {
        return undefined;
      }
      const num = Number(val);
      if (!Number.isInteger(num) || num <= 0) {
        throw new Error(errorMsg);
      }
      return num;
    };

    try {
      const sId = parsePositiveId(raw.service_id, 'Servicio ID debe ser un entero positivo.');
      if (sId) payload.service_id = sId;

      const iId = parsePositiveId(raw.incident_id, 'Incidente ID debe ser un entero positivo.');
      if (iId) payload.incident_id = iId;

      const rId = parsePositiveId(raw.request_id, 'Solicitud ID debe ser un entero positivo.');
      if (rId) payload.request_id = rId;
    } catch (error: any) {
      this.validationError = error.message;
      return;
    }

    this.filtersApplied.emit(payload);
  }

  protected resetFilters(): void {
    this.validationError = '';
    this.filterForm.reset({ status: 'all' });
    this.filtersApplied.emit({});
  }
}

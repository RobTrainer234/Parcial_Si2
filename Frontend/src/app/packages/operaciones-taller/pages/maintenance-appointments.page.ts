import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';

import { buildApiUrl } from '../../../core/config/api.config';
import { AppCardComponent } from '../../../shared/components/app-card.component';
import { PageHeaderComponent } from '../../../shared/components/page-header.component';

interface MaintenanceAppointment {
  appointment_id: number;
  status: string;
  scheduled_at: string;
  vehicle_label: string;
  workshop_name: string;
  customer_name: string | null;
  reason: string | null;
  client_notes: string | null;
  workshop_notes: string | null;
}

@Component({
  selector: 'app-maintenance-appointments-page',
  standalone: true,
  imports: [CommonModule, AppCardComponent, PageHeaderComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page">
      <app-page-header
        eyebrow="Mantenimiento preventivo"
        title="Citas programadas"
        subtitle="Confirma, rechaza o completa los mantenimientos solicitados por clientes."
      >
        <button page-actions type="button" class="app-button app-button--secondary" (click)="load()" [disabled]="loading()">
          {{ loading() ? 'Actualizando...' : 'Actualizar' }}
        </button>
      </app-page-header>

      @if (error()) { <p class="feedback">{{ error() }}</p> }
      @if (loading()) { <p>Cargando citas...</p> }
      @if (!loading() && appointments().length === 0) { <p>No hay citas de mantenimiento programadas.</p> }

      <div class="list">
        @for (appointment of appointments(); track appointment.appointment_id) {
          <app-card>
            <div class="appointment">
              <div>
                <h3>{{ appointment.customer_name || 'Cliente' }} · {{ appointment.vehicle_label }}</h3>
                <p>{{ appointment.workshop_name }} · {{ formatDate(appointment.scheduled_at) }}</p>
                @if (appointment.reason) { <p><strong>Motivo:</strong> {{ appointment.reason }}</p> }
                @if (appointment.client_notes) { <p><strong>Notas:</strong> {{ appointment.client_notes }}</p> }
              </div>
              <div class="actions">
                <span class="status">{{ appointment.status }}</span>
                @if (appointment.status === 'PENDIENTE') {
                  <button type="button" class="app-button" (click)="act(appointment, 'confirm')">Confirmar</button>
                  <button type="button" class="app-button app-button--secondary" (click)="act(appointment, 'reject')">Rechazar</button>
                }
                @if (appointment.status === 'CONFIRMADA') {
                  <button type="button" class="app-button" (click)="act(appointment, 'complete')">Completar</button>
                }
              </div>
            </div>
          </app-card>
        }
      </div>
    </div>
  `,
  styles: [`
    .list { display: grid; gap: var(--space-4); }
    .appointment { display: flex; justify-content: space-between; gap: var(--space-5); }
    h3 { margin: 0 0 var(--space-2); } p { margin: var(--space-1) 0; color: var(--color-text-muted); }
    .actions { display: flex; align-items: flex-start; gap: var(--space-2); flex-wrap: wrap; }
    .status { padding: .45rem .7rem; border-radius: 999px; background: var(--color-surface-soft); font-weight: 700; font-size: .8rem; }
    .feedback { color: var(--color-danger); }
    @media (max-width: 720px) { .appointment { flex-direction: column; } }
  `],
})
export class MaintenanceAppointmentsPage {
  private readonly http = inject(HttpClient);
  protected readonly appointments = signal<MaintenanceAppointment[]>([]);
  protected readonly loading = signal(false);
  protected readonly error = signal('');

  constructor() { this.load(); }

  protected load(): void {
    this.loading.set(true);
    this.error.set('');
    this.http.get<MaintenanceAppointment[]>(buildApiUrl('/workshop/maintenance-appointments')).subscribe({
      next: (items) => { this.appointments.set(items); this.loading.set(false); },
      error: () => { this.error.set('No se pudieron cargar las citas.'); this.loading.set(false); },
    });
  }

  protected act(appointment: MaintenanceAppointment, action: 'confirm' | 'reject' | 'complete'): void {
    this.http.patch(buildApiUrl(`/workshop/maintenance-appointments/${appointment.appointment_id}/${action}`), {}).subscribe({
      next: () => this.load(),
      error: () => this.error.set('No se pudo actualizar la cita.'),
    });
  }

  protected formatDate(value: string): string {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('es-BO', { dateStyle: 'medium', timeStyle: 'short' }).format(date);
  }
}

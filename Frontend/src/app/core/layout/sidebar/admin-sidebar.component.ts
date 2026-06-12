import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { HttpClient } from '@angular/common/http';
import { RouterLink, RouterLinkActive } from '@angular/router';

import { AuthService } from '../../auth/auth.service';
import { WorkshopSelectionService } from '../../auth/workshop-selection.service';
import { buildApiUrl } from '../../config/api.config';

interface WorkshopOption {
  id_taller: number;
  nombre_comercial: string;
}

@Component({
  selector: 'app-admin-sidebar',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <aside class="sidebar">
      <div class="sidebar__brand">
        <p class="sidebar__eyebrow">SI2 Auxilio</p>
        <h1>Control del Taller</h1>
        <p class="sidebar__copy">
          Gestiona solicitudes, operarios, servicios, auditoría y notificaciones del taller.
        </p>
      </div>

      @if (isGerente()) {
        <div class="sidebar__workshop-selector">
          <label for="workshop-select" class="sidebar__selector-label">Sucursal activa</label>
          <select
            id="workshop-select"
            class="sidebar__select"
            [value]="selectedWorkshopId() ?? ''"
            (change)="onWorkshopChange($event)"
          >
            <option value="" disabled>Seleccione una sucursal</option>
            @for (ws of workshops(); track ws.id_taller) {
              <option [value]="ws.id_taller">{{ ws.nombre_comercial }}</option>
            }
          </select>
        </div>
      }

      <nav class="sidebar__nav" aria-label="Navegación principal del taller">
        @for (item of navItems; track item.path) {
          <a
            class="sidebar__link"
            [routerLink]="item.path"
            routerLinkActive="sidebar__link--active"
            [routerLinkActiveOptions]="{ exact: item.exact ?? false }"
          >
            <span class="sidebar__link-label">{{ item.label }}</span>
            @if (item.badge) {
              <span class="badge badge--neutral">{{ item.badge }}</span>
            }
          </a>
        }
      </nav>
    </aside>
  `,
  styles: [
    `
      .sidebar {
        display: flex;
        flex-direction: column;
        gap: var(--space-8);
        height: 100%;
      }

      .sidebar__brand {
        padding: var(--space-6);
        border-radius: var(--radius-xl);
        border: 1px solid color-mix(in srgb, var(--color-primary) 16%, var(--color-border));
        background:
          radial-gradient(circle at top right, color-mix(in srgb, var(--color-primary) 16%, transparent), transparent 30%),
          linear-gradient(180deg, color-mix(in srgb, var(--color-surface-elevated) 94%, transparent), var(--color-surface));
        box-shadow: var(--shadow-card);
      }

      .sidebar__eyebrow {
        margin: 0 0 0.55rem;
        color: var(--color-primary);
        font-size: 0.76rem;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        font-weight: 700;
      }

      .sidebar__brand h1 {
        margin: 0;
        font-size: 1.55rem;
        line-height: 1.04;
      }

      .sidebar__copy {
        margin: 0.8rem 0 0;
        color: var(--color-text-muted);
        line-height: 1.55;
      }

      .sidebar__workshop-selector {
        padding: var(--space-4) var(--space-6);
        border-radius: var(--radius-lg);
        border: 1px solid var(--color-border);
        background: var(--color-surface-soft);
      }

      .sidebar__selector-label {
        display: block;
        margin-bottom: 0.4rem;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--color-text-muted);
      }

      .sidebar__select {
        width: 100%;
        padding: 0.55rem 0.6rem;
        border-radius: var(--radius-md);
        border: 1px solid var(--color-border);
        background: var(--color-surface-elevated);
        color: var(--color-text);
        font-size: 0.85rem;
        font-family: inherit;
        cursor: pointer;
      }

      .sidebar__nav {
        display: flex;
        flex-direction: column;
        gap: 0.35rem;
      }

      .sidebar__link {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--space-3);
        min-height: 3rem;
        padding: 0.8rem 1rem;
        border-radius: var(--radius-md);
        border: 1px solid transparent;
        color: var(--color-text-muted);
        text-decoration: none;
      }

      .sidebar__link:hover {
        color: var(--color-text);
        background: color-mix(in srgb, var(--color-primary) 7%, transparent);
        border-color: color-mix(in srgb, var(--color-primary) 16%, var(--color-border));
      }

      .sidebar__link--active {
        color: var(--color-text);
        background: color-mix(in srgb, var(--color-primary) 14%, transparent);
        border-color: color-mix(in srgb, var(--color-primary) 28%, var(--color-border));
        box-shadow: inset 3px 0 0 var(--color-primary);
      }

      .sidebar__link-label {
        font-weight: 600;
      }

      @media (max-width: 1024px) {
        .sidebar__nav {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        }
      }
    `,
  ],
})
export class AdminSidebarComponent {
  private readonly authService = inject(AuthService);
  private readonly workshopSelection = inject(WorkshopSelectionService);
  private readonly http = inject(HttpClient);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly isGerente = computed(() => this.authService.isGerente());
  protected readonly selectedWorkshopId = this.workshopSelection.selectedWorkshopId;
  protected readonly workshops = signal<WorkshopOption[]>([]);

  protected readonly navItems: Array<{
    label: string;
    path: string;
    exact?: boolean;
    badge?: string;
  }> = [
    { label: 'Panel', path: '/admin/dashboard', exact: true },
    { label: 'Gestión del Taller', path: '/admin/workshop', exact: true },
    { label: 'Solicitudes', path: '/admin/requests' },
    { label: 'Asignaciones', path: '/admin/services/waiting-assignment' },
    { label: 'Servicios realizados', path: '/admin/services', exact: true },
    { label: 'Auditoría', path: '/admin/audit' },
    { label: 'Notificaciones', path: '/admin/notifications' },
  ];

  protected onWorkshopChange(event: Event): void {
    const select = event.target as HTMLSelectElement;
    const value = select.value;
    this.workshopSelection.selectWorkshop(value ? Number(value) : null);
  }

  constructor() {
    if (this.authService.isGerente()) {
      this.loadWorkshops();
    }
  }

  private loadWorkshops(): void {
    this.http
      .get<WorkshopOption[]>(buildApiUrl('/workshop/gerente/workshops'))
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
          this.workshops.set(data);
          const currentId = this.selectedWorkshopId();
          if (currentId !== null && !data.some((w) => w.id_taller === currentId)) {
            this.workshopSelection.selectWorkshop(null);
          }
        },
      });
  }
}

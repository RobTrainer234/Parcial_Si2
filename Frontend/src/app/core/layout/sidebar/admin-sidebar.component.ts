import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

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
  protected readonly navItems: Array<{
    label: string;
    path: string;
    exact?: boolean;
    badge?: string;
  }> = [
    { label: 'Panel', path: '/admin/dashboard', exact: true },
    { label: 'Perfil Taller', path: '/admin/workshop/profile' },
    { label: 'Catálogo', path: '/admin/workshop/catalog' },
    { label: 'Operarios', path: '/admin/workshop/staff' },
    { label: 'Solicitudes', path: '/admin/requests' },
    { label: 'Asignaciones', path: '/admin/services/waiting-assignment' },
    { label: 'Auditoría', path: '/admin/audit' },
    { label: 'Notificaciones', path: '/admin/notifications' },
  ];
}

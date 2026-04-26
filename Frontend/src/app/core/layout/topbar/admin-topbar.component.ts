import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, output, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { AuthService } from '../../auth/auth.service';
import { NotificationApiService } from '../../notifications/notification-api.service';
import { ThemeService } from '../../theme/theme.service';

@Component({
  selector: 'app-admin-topbar',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <header class="topbar">
      <div class="topbar__context">
        <p class="topbar__label">Workshop Administration</p>
        <strong>{{ currentUserEmail() }}</strong>
        @if (workshopId(); as workshopId) {
          <p class="topbar__meta">Taller #{{ workshopId }}</p>
        }
      </div>

      <div class="topbar__actions">
        <button
          type="button"
          class="app-button app-button--ghost"
          [attr.aria-label]="themeButtonLabel()"
          (click)="toggleTheme()"
        >
          {{ currentTheme() === 'dark' ? 'Modo claro' : 'Modo oscuro' }}
        </button>

        <button
          type="button"
          class="topbar__icon-button"
          aria-label="Notificaciones del taller"
        >
          <span aria-hidden="true">●</span>
          @if (unreadCount() > 0) {
            <span class="topbar__notification-count">{{ unreadCount() }}</span>
          }
        </button>

        <div class="topbar__role">{{ currentUserRole() }}</div>

        <div class="topbar__user-pill" [attr.aria-label]="'Usuario ' + currentUserEmail()">
          {{ userInitials() }}
        </div>

        <button type="button" class="app-button app-button--secondary" (click)="logout.emit()">
          Cerrar sesión
        </button>
      </div>
    </header>
  `,
  styles: [
    `
      .topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--space-4);
        padding: var(--space-5) var(--space-6);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-xl);
        background:
          linear-gradient(180deg, color-mix(in srgb, var(--color-surface-elevated) 92%, transparent), var(--color-surface));
        box-shadow: var(--shadow-card);
      }

      .topbar__context strong {
        display: block;
        font-size: 1rem;
      }

      .topbar__label,
      .topbar__meta {
        margin: 0;
      }

      .topbar__label {
        color: var(--color-text-soft);
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.16em;
        text-transform: uppercase;
      }

      .topbar__meta {
        margin-top: 0.35rem;
        color: var(--color-text-muted);
      }

      .topbar__actions {
        display: flex;
        align-items: center;
        gap: var(--space-3);
        flex-wrap: wrap;
        justify-content: flex-end;
      }

      .topbar__icon-button,
      .topbar__user-pill {
        width: 2.75rem;
        height: 2.75rem;
        border-radius: 999px;
        border: 1px solid var(--color-border);
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background: var(--color-surface-soft);
      }

      .topbar__icon-button {
        position: relative;
        color: var(--color-primary);
        cursor: pointer;
      }

      .topbar__notification-count {
        position: absolute;
        top: -0.15rem;
        right: -0.1rem;
        min-width: 1.2rem;
        height: 1.2rem;
        padding: 0 0.25rem;
        border-radius: 999px;
        background: var(--color-danger);
        color: #fff;
        font-size: 0.72rem;
        font-weight: 700;
        display: inline-flex;
        align-items: center;
        justify-content: center;
      }

      .topbar__user-pill {
        color: var(--color-text);
        font-weight: 700;
      }

      .topbar__role {
        padding: 0.55rem 0.8rem;
        border-radius: 999px;
        border: 1px solid var(--color-border);
        background: var(--color-surface-soft);
        color: var(--color-text-muted);
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
      }

      @media (max-width: 920px) {
        .topbar {
          flex-direction: column;
          align-items: flex-start;
        }

        .topbar__actions {
          width: 100%;
          justify-content: flex-start;
        }
      }
    `,
  ],
})
export class AdminTopbarComponent {
  private readonly authService = inject(AuthService);
  private readonly themeService = inject(ThemeService);
  private readonly notificationApi = inject(NotificationApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly unreadCountState = signal(0);

  readonly logout = output<void>();

  protected readonly currentTheme = this.themeService.currentTheme;
  protected readonly currentUser = this.authService.currentUser;
  protected readonly workshopId = computed(
    () => this.currentUser()?.actor_context.taller_id ?? null,
  );
  protected readonly currentUserEmail = computed(
    () => this.currentUser()?.email ?? 'admin@si2.local',
  );
  protected readonly currentUserRole = computed(
    () => this.currentUser()?.role ?? this.currentUser()?.tipo_usuario ?? 'SIN ROL',
  );
  protected readonly unreadCount = computed(() => this.unreadCountState());
  protected readonly userInitials = computed(() => {
    const userEmail = this.currentUser()?.email ?? 'AD';
    const base = userEmail.split('@')[0].replace(/[^a-zA-Z0-9]/g, '');
    return (base.slice(0, 2) || 'AD').toUpperCase();
  });
  protected readonly themeButtonLabel = computed(() =>
    this.currentTheme() === 'dark' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro',
  );

  protected toggleTheme(): void {
    this.themeService.toggleTheme();
  }

  constructor() {
    if (this.authService.isAuthenticated()) {
      this.notificationApi
        .getUnreadCount()
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: (response) => this.unreadCountState.set(response.unread_count),
          error: () => this.unreadCountState.set(0),
        });
    }
  }
}

import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';

import { AuthService } from '../../../core/auth/auth.service';
import { AppCardComponent } from '../../../shared/components/app-card.component';
import { ErrorStateComponent } from '../../../shared/components/error-state.component';
import { LoadingStateComponent } from '../../../shared/components/loading-state.component';
import { PageHeaderComponent } from '../../../shared/components/page-header.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge.component';
import { UserProfileApi } from '../data-access/user-profile.api';
import { ProfileMeResponse, ProfileUpdateRequest } from '../data-access/user-profile.models';

@Component({
  selector: 'app-user-profile-page',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    PageHeaderComponent,
    AppCardComponent,
    LoadingStateComponent,
    ErrorStateComponent,
    StatusBadgeComponent,
  ],
  template: `
    <app-page-header
      title="Mi perfil"
      subtitle="Consulta la información de tu cuenta administrativa y el contexto del taller asociado."
    >
      <div page-actions>
        <button
          type="button"
          class="app-button app-button--secondary"
          (click)="loadProfile()"
          [disabled]="loading()"
        >
          Actualizar
        </button>
      </div>
    </app-page-header>

    @if (pageError()) {
      <div class="mb-4">
        <app-error-state [message]="pageError()"></app-error-state>
      </div>
    }

    @if (loading() && !profile()) {
      <app-loading-state message="Cargando información de tu perfil..."></app-loading-state>
    } @else if (profile(); as p) {
      <div class="profile-layout">
        <!-- Izquierda: Identidad y Seguridad -->
        <div class="profile-col">
          <app-card>
            <div class="card-header">
              <h4>Identidad de cuenta</h4>
            </div>
            <div class="card-body">
              <div class="data-group">
                <span class="data-label">Correo Electrónico (Email)</span>
                <span class="data-value">{{ p.user.email }}</span>
              </div>
              <div class="data-group">
                <span class="data-label">Rol del Sistema</span>
                <span class="data-value">{{ p.user.role || p.user.tipo_usuario || 'N/A' }}</span>
              </div>
              <div class="data-group">
                <span class="data-label">Estado de la cuenta</span>
                <span class="data-value">
                  <app-status-badge label="Activo"></app-status-badge>
                </span>
              </div>
            </div>
          </app-card>

          <app-card class="mt-4">
            <div class="card-header">
              <h4>Contexto del taller</h4>
            </div>
            <div class="card-body">
              <div class="data-group">
                <span class="data-label">ID de Taller</span>
                <span class="data-value">
                  @if (p.user.actor_context.taller_id) {
                    #{{ p.user.actor_context.taller_id }}
                  } @else {
                    <span class="text-muted">No asignado</span>
                  }
                </span>
              </div>
              <div class="data-group">
                <span class="data-label">Rol Operativo</span>
                <span class="data-value">
                  @if (p.user.actor_context.administrador_persona_id) {
                    Administrador de Taller
                  } @else if (p.user.actor_context.operario_id) {
                    Operario de Taller
                  } @else {
                    <span class="text-muted">Rol desconocido</span>
                  }
                </span>
              </div>
            </div>
          </app-card>
        </div>

        <!-- Derecha: Datos Personales -->
        <div class="profile-col">
          <app-card>
            <div class="card-header space-between">
              <h4>Datos personales</h4>
              @if (!isEditing()) {
                <button
                  type="button"
                  class="app-button app-button--secondary app-button--sm"
                  (click)="startEditing()"
                >
                  Editar datos
                </button>
              }
            </div>

            <div class="card-body">
              @if (isEditing()) {
                <form [formGroup]="editForm" (ngSubmit)="saveProfile()" class="edit-form">
                  <label class="app-field">
                    <span class="app-field__label">Nombre <span class="text-danger">*</span></span>
                    <input type="text" class="app-input" formControlName="nombre" />
                  </label>

                  <label class="app-field">
                    <span class="app-field__label">Apellido <span class="text-danger">*</span></span>
                    <input type="text" class="app-input" formControlName="apellido" />
                  </label>

                  <label class="app-field">
                    <span class="app-field__label">Teléfono</span>
                    <input type="text" class="app-input" formControlName="telefono" />
                  </label>

                  <label class="app-field">
                    <span class="app-field__label">Dirección</span>
                    <textarea class="app-input" formControlName="direccion" rows="3"></textarea>
                  </label>

                  @if (editError()) {
                    <p class="feedback feedback--error">{{ editError() }}</p>
                  }

                  <div class="form-actions mt-3">
                    <button
                      type="submit"
                      class="app-button"
                      [disabled]="editForm.invalid || saving()"
                    >
                      {{ saving() ? 'Guardando...' : 'Guardar cambios' }}
                    </button>
                    <button
                      type="button"
                      class="app-button app-button--ghost"
                      (click)="cancelEditing()"
                      [disabled]="saving()"
                    >
                      Cancelar
                    </button>
                  </div>
                </form>
              } @else {
                <div class="data-group">
                  <span class="data-label">Nombre completo</span>
                  <span class="data-value">{{ getFullName(p.persona.nombre, p.persona.apellido) }}</span>
                </div>
                <div class="data-group">
                  <span class="data-label">CI / Documento</span>
                  <span class="data-value">{{ p.persona.ci || '-' }}</span>
                </div>
                <div class="data-group">
                  <span class="data-label">Teléfono</span>
                  <span class="data-value">{{ p.persona.telefono || '-' }}</span>
                </div>
                <div class="data-group">
                  <span class="data-label">Dirección</span>
                  <span class="data-value">{{ p.persona.direccion || '-' }}</span>
                </div>
              }
            </div>
          </app-card>
        </div>
      </div>
    }
  `,
  styles: [
    `
      .profile-layout {
        display: grid;
        grid-template-columns: 1fr;
        gap: var(--space-4);
        align-items: start;
      }

      @media (min-width: 768px) {
        .profile-layout {
          grid-template-columns: 1fr 2fr;
        }
      }

      .profile-col {
        display: flex;
        flex-direction: column;
        gap: var(--space-4);
      }

      .card-header {
        margin-bottom: var(--space-4);
        padding-bottom: var(--space-3);
        border-bottom: 1px solid var(--color-border);
      }

      .card-header.space-between {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }

      .card-header h4 {
        margin: 0;
        font-size: 1.1rem;
      }

      .data-group {
        display: flex;
        flex-direction: column;
        margin-bottom: var(--space-4);
      }

      .data-group:last-child {
        margin-bottom: 0;
      }

      .data-label {
        font-size: 0.85rem;
        color: var(--color-text-muted);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: var(--space-1);
      }

      .data-value {
        font-weight: 500;
        font-size: 1.05rem;
        word-break: break-word;
      }

      .edit-form {
        display: flex;
        flex-direction: column;
        gap: var(--space-3);
      }

      .form-actions {
        display: flex;
        gap: var(--space-2);
      }

      .text-muted {
        color: var(--color-text-muted);
      }

      .text-danger {
        color: var(--color-danger);
      }

      .feedback--error {
        color: var(--color-danger);
        font-size: 0.9rem;
        margin: 0;
      }

      .mb-4 {
        margin-bottom: var(--space-4);
      }

      .mt-4 {
        margin-top: var(--space-4);
      }

      .mt-3 {
        margin-top: var(--space-3);
      }
    `,
  ],
})
export class UserProfilePage {
  private readonly api = inject(UserProfileApi);
  private readonly authService = inject(AuthService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly fb = inject(FormBuilder);

  protected readonly profile = signal<ProfileMeResponse | null>(null);
  protected readonly loading = signal(true);
  protected readonly pageError = signal('');

  protected readonly isEditing = signal(false);
  protected readonly saving = signal(false);
  protected readonly editError = signal('');

  protected readonly editForm = this.fb.group({
    nombre: [''],
    apellido: [''],
    telefono: [''],
    direccion: [''],
  });

  constructor() {
    this.loadProfile();
  }

  protected loadProfile(): void {
    this.loading.set(true);
    this.pageError.set('');

    this.api
      .getProfile()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
          this.profile.set(data);
          this.loading.set(false);
        },
        error: () => {
          this.pageError.set('Ocurrió un error al cargar el perfil de usuario. Intenta nuevamente.');
          this.loading.set(false);
        },
      });
  }

  protected getFullName(nombre: string, apellido: string): string {
    const parts = [];
    if (nombre) parts.push(nombre);
    if (apellido) parts.push(apellido);
    return parts.join(' ') || '-';
  }

  protected startEditing(): void {
    const current = this.profile();
    if (!current) return;

    this.editForm.setValue({
      nombre: current.persona.nombre || '',
      apellido: current.persona.apellido || '',
      telefono: current.persona.telefono || '',
      direccion: current.persona.direccion || '',
    });

    this.editError.set('');
    this.isEditing.set(true);
  }

  protected cancelEditing(): void {
    this.isEditing.set(false);
    this.editError.set('');
  }

  protected saveProfile(): void {
    if (this.editForm.invalid || this.saving()) {
      return;
    }

    const current = this.profile();
    if (!current) return;

    const raw = this.editForm.getRawValue();

    const trim = (val: string | null | undefined): string | null => {
      const trimmed = (val ?? '').trim();
      return trimmed.length > 0 ? trimmed : null;
    };

    const nombre = trim(raw.nombre);
    const apellido = trim(raw.apellido);

    if (!nombre || !apellido) {
      this.editError.set('Nombre y Apellido son obligatorios.');
      return;
    }

    const payload: ProfileUpdateRequest = {
      nombre,
      apellido,
      telefono: trim(raw.telefono),
      direccion: trim(raw.direccion),
    };

    this.saving.set(true);
    this.editError.set('');

    this.api
      .updateProfile(payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (updatedProfile) => {
          this.profile.set(updatedProfile);
          this.isEditing.set(false);
          this.saving.set(false);
          // Opcionalmente refrescar el usuario global del Auth
          this.authService.refreshCurrentUser().catch(() => {});
        },
        error: (err) => {
          if (err.status === 422) {
            this.editError.set('Datos inválidos. Por favor, revisa los campos.');
          } else {
            this.editError.set('Ocurrió un error al guardar los cambios.');
          }
          this.saving.set(false);
        },
      });
  }
}

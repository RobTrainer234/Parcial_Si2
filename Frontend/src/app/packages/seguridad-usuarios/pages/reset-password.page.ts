import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import { localizeBackendMessage } from '../../../shared/utils/user-facing-text';

@Component({
  selector: 'app-reset-password-page',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  template: `
    <div class="page">
      <section class="card">
        <div class="card__brand">
          <p class="card__eyebrow">SI2 Auxilio</p>
          <h1>Nueva contraseña</h1>
          <p class="card__subtitle">
            Ingresa el token de recuperación y tu nueva contraseña.
          </p>
        </div>

        @if (success()) {
          <div class="card__success">
            <p class="success-title">Contraseña restablecida</p>
            <p>Tu contraseña se ha actualizado correctamente. Ahora puedes iniciar sesión con tu nueva contraseña.</p>
            <a routerLink="/login" class="app-button" style="display:block;text-align:center;margin-top:1rem;">Iniciar sesión</a>
          </div>
        } @else {
          <form [formGroup]="form" (ngSubmit)="submit()" class="card__form">
            <div class="app-field">
              <label class="app-field__label" for="token">Token de recuperación</label>
              <input
                id="token"
                class="app-input"
                type="text"
                formControlName="token"
                placeholder="Ingresa el token recibido"
              />
            </div>

            <div class="app-field">
              <label class="app-field__label" for="new-password">Nueva contraseña</label>
              <input
                id="new-password"
                class="app-input"
                type="password"
                formControlName="newPassword"
                autocomplete="new-password"
                placeholder="Mínimo 8 caracteres"
              />
            </div>

            <div class="app-field">
              <label class="app-field__label" for="confirm-password">Confirmar contraseña</label>
              <input
                id="confirm-password"
                class="app-input"
                type="password"
                formControlName="confirmPassword"
                autocomplete="new-password"
                placeholder="Repite la contraseña"
              />
            </div>

            @if (errorMessage()) {
              <p class="card__error" role="alert">{{ errorMessage() }}</p>
            }

            <button class="app-button card__submit" type="submit" [disabled]="form.invalid || submitting()">
              {{ submitting() ? 'Restableciendo...' : 'Restablecer contraseña' }}
            </button>

            <a routerLink="/login" class="back-link">Volver al inicio de sesión</a>
          </form>
        }
      </section>
    </div>
  `,
  styles: [
    `
      :host {
        display: block;
        min-height: 100vh;
      }

      .page {
        min-height: 100vh;
        display: grid;
        place-items: center;
        padding: var(--space-8);
      }

      .card {
        width: min(480px, 100%);
        padding: var(--space-6);
        border-radius: calc(var(--radius-xl) + 4px);
        border: 1px solid color-mix(in srgb, var(--color-primary) 16%, var(--color-border));
        background:
          radial-gradient(circle at top right, color-mix(in srgb, var(--color-primary) 12%, transparent), transparent 35%),
          linear-gradient(180deg, color-mix(in srgb, var(--color-surface-elevated) 94%, transparent), var(--color-surface));
        box-shadow:
          var(--shadow-card),
          0 0 0 1px color-mix(in srgb, var(--color-primary) 8%, transparent);
      }

      .card__brand {
        margin-bottom: var(--space-6);
      }

      .card__eyebrow {
        margin: 0 0 var(--space-3);
        color: var(--color-primary);
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.18em;
        text-transform: uppercase;
      }

      .card__brand h1 {
        margin: 0;
        font-size: clamp(1.5rem, 3vw, 2rem);
      }

      .card__subtitle {
        margin: var(--space-3) 0 0;
        color: var(--color-text-muted);
        line-height: 1.65;
      }

      .card__form {
        display: flex;
        flex-direction: column;
        gap: var(--space-5);
      }

      .card__error {
        margin: 0;
        padding: var(--space-4);
        border-radius: var(--radius-md);
        border: 1px solid color-mix(in srgb, var(--color-danger) 35%, var(--color-border));
        background: color-mix(in srgb, var(--color-danger) 10%, var(--color-surface));
        color: var(--color-danger);
      }

      .card__submit {
        width: 100%;
      }

      .back-link {
        display: block;
        text-align: center;
        color: var(--color-primary);
        text-decoration: none;
        font-size: 0.9rem;
        margin-top: var(--space-2);
      }

      .back-link:hover {
        text-decoration: underline;
      }

      .card__success {
        text-align: center;
      }

      .card__success p {
        margin: 0 0 var(--space-3);
      }

      .success-title {
        font-size: 1.25rem;
        font-weight: 600;
      }

      @media (max-width: 640px) {
        .page {
          padding: var(--space-4);
        }
      }
    `,
  ],
})
export class ResetPasswordPage {
  private readonly fb = inject(FormBuilder);
  private readonly authService = inject(AuthService);

  protected readonly submitting = signal(false);
  protected readonly errorMessage = signal('');
  protected readonly success = signal(false);

  protected readonly form = this.fb.nonNullable.group({
    token: ['', [Validators.required]],
    newPassword: ['', [Validators.required, Validators.minLength(8)]],
    confirmPassword: ['', [Validators.required]],
  });

  constructor() {
    const params = new URLSearchParams(window.location.search);
    const tokenFromQuery = params.get('token');
    if (tokenFromQuery) {
      this.form.patchValue({ token: tokenFromQuery });
    }
  }

  protected async submit(): Promise<void> {
    if (this.form.invalid || this.submitting()) {
      this.form.markAllAsTouched();
      return;
    }

    const raw = this.form.getRawValue();
    if (raw.newPassword !== raw.confirmPassword) {
      this.errorMessage.set('Las contraseñas no coinciden.');
      return;
    }

    this.submitting.set(true);
    this.errorMessage.set('');

    try {
      await this.authService.resetPassword(raw.token, raw.newPassword);
      this.success.set(true);
    } catch (error) {
      const backendMessage =
        error instanceof HttpErrorResponse
          ? error.error?.detail ?? 'No se pudo restablecer la contraseña.'
          : error instanceof Error
            ? error.message
            : 'No se pudo restablecer la contraseña.';

      this.errorMessage.set(localizeBackendMessage(String(backendMessage)));
    } finally {
      this.submitting.set(false);
    }
  }
}

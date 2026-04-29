import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import { ThemeService } from '../../../core/theme/theme.service';
import { localizeBackendMessage } from '../../../shared/utils/user-facing-text';

@Component({
  selector: 'app-admin-login-page',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  template: `
    <div class="login-page">
      <button
        type="button"
        class="app-button app-button--ghost login-page__theme-toggle"
        [attr.aria-label]="themeToggleLabel()"
        (click)="toggleTheme()"
      >
        {{ currentTheme() === 'dark' ? 'Modo claro' : 'Modo oscuro' }}
      </button>

      <section class="login-card">
        <div class="login-card__brand">
          <p class="login-card__eyebrow">SI2 Auxilio</p>
          <h1>Sistema de Taller</h1>
          <p class="login-card__subtitle">
            Accede al panel para gestionar solicitudes, operarios, servicios y seguimiento del taller.
          </p>
        </div>

        <form [formGroup]="form" (ngSubmit)="submit()" class="login-card__form">
          <div class="app-field">
            <label class="app-field__label" for="login-email">Correo</label>
            <input
              id="login-email"
              class="app-input"
              type="email"
              formControlName="email"
              autocomplete="username"
              placeholder="admin@taller.com"
            />
          </div>

          <div class="app-field">
            <label class="app-field__label" for="login-password">Contraseña</label>
            <input
              id="login-password"
              class="app-input"
              type="password"
              formControlName="password"
              autocomplete="current-password"
              placeholder="Ingresa tu contraseña"
            />
          </div>

          @if (errorMessage()) {
            <p class="login-card__error" role="alert">{{ errorMessage() }}</p>
          }

          <button class="app-button login-card__submit" type="submit" [disabled]="form.invalid || submitting()">
            {{ submitting() ? 'Validando acceso...' : 'Ingresar al panel' }}
          </button>
        </form>
      </section>
    </div>
  `,
  styles: [
    `
      :host {
        display: block;
        min-height: 100vh;
      }

      .login-page {
        position: relative;
        min-height: 100vh;
        display: grid;
        place-items: center;
        padding: var(--space-8);
      }

      .login-page__theme-toggle {
        position: absolute;
        top: var(--space-6);
        right: var(--space-6);
        z-index: 1;
      }

      .login-card {
        position: relative;
        width: min(980px, 100%);
        display: grid;
        grid-template-columns: 1.1fr 0.9fr;
        gap: var(--space-6);
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

      .login-card::after {
        content: '';
        position: absolute;
        top: var(--space-6);
        bottom: var(--space-6);
        left: calc(55% - 1px);
        width: 1px;
        background: linear-gradient(
          180deg,
          transparent,
          color-mix(in srgb, var(--color-border-strong) 72%, transparent),
          transparent
        );
        pointer-events: none;
      }

      .login-card__brand {
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        padding: var(--space-6);
        border-radius: var(--radius-xl);
        background:
          linear-gradient(180deg, color-mix(in srgb, var(--color-primary) 10%, var(--color-surface-soft)), var(--color-surface-soft));
        border: 1px solid var(--color-border);
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
      }

      .login-card__eyebrow {
        margin: 0 0 var(--space-3);
        color: var(--color-primary);
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.18em;
        text-transform: uppercase;
      }

      .login-card__brand h1 {
        margin: 0;
        font-size: clamp(2rem, 4vw, 3rem);
        line-height: 0.98;
      }

      .login-card__subtitle {
        margin: var(--space-5) 0 0;
        color: var(--color-text-muted);
        line-height: 1.65;
        max-width: 38ch;
      }


      .login-card__form {
        display: flex;
        flex-direction: column;
        justify-content: center;
        gap: var(--space-5);
        padding: var(--space-4) var(--space-2);
        position: relative;
      }

      .login-card__error {
        margin: 0;
        padding: var(--space-4);
        border-radius: var(--radius-md);
        border: 1px solid color-mix(in srgb, var(--color-danger) 35%, var(--color-border));
        background: color-mix(in srgb, var(--color-danger) 10%, var(--color-surface));
        color: var(--color-danger);
      }

      .login-card__submit {
        width: 100%;
        margin-top: var(--space-2);
      }

      @media (max-width: 900px) {
        .login-card {
          grid-template-columns: 1fr;
        }

        .login-card::after {
          display: none;
        }
      }

      @media (max-width: 640px) {
        .login-page {
          padding: var(--space-4);
        }

        .login-page__theme-toggle {
          top: var(--space-4);
          right: var(--space-4);
        }
      }
    `,
  ],
})
export class AdminLoginPage {
  private readonly fb = inject(FormBuilder);
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly themeService = inject(ThemeService);

  protected readonly submitting = signal(false);
  protected readonly errorMessage = signal('');
  protected readonly currentTheme = this.themeService.currentTheme;
  protected readonly themeToggleLabel = computed(() =>
    this.currentTheme() === 'dark' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro',
  );

  protected readonly form = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
  });

  protected toggleTheme(): void {
    this.themeService.toggleTheme();
  }

  protected async submit(): Promise<void> {
    if (this.form.invalid || this.submitting()) {
      this.form.markAllAsTouched();
      return;
    }

    this.submitting.set(true);
    this.errorMessage.set('');

    try {
      await this.authService.loginAsAdmin(this.form.getRawValue());
      await this.router.navigate(['/admin/dashboard']);
    } catch (error) {
      const backendMessage =
        error instanceof HttpErrorResponse
          ? error.error?.detail ?? 'No se pudo iniciar sesión. Verifica tus credenciales.'
          : error instanceof Error
            ? error.message
            : 'No se pudo iniciar sesión. Verifica tus credenciales.';

      this.errorMessage.set(localizeBackendMessage(String(backendMessage)));
    } finally {
      this.submitting.set(false);
    }
  }
}

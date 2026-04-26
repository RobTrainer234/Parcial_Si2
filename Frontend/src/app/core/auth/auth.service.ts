import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { buildApiUrl } from '../config/api.config';
import { LoginRequest, LoginResponse, StoredSession, UserProfile } from './auth.models';

const SESSION_STORAGE_KEY = 'si2.admin.session';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);

  private readonly sessionSignal = signal<StoredSession | null>(this.restoreSession());
  private readonly loadingProfileSignal = signal(false);

  readonly session = computed(() => this.sessionSignal());
  readonly currentUser = computed(() => this.sessionSignal()?.user ?? null);
  readonly isAuthenticated = computed(() => !!this.sessionSignal()?.access_token);
  readonly isAdmin = computed(() => this.currentUser()?.role === 'ADMINISTRADOR');

  getToken(): string | null {
    return this.sessionSignal()?.access_token ?? null;
  }

  async loginAsAdmin(payload: LoginRequest): Promise<UserProfile> {
    const response = await firstValueFrom(
      this.http.post<LoginResponse>(buildApiUrl('/auth/login'), payload),
    );

    if (response.role !== 'ADMINISTRADOR' || response.user.role !== 'ADMINISTRADOR') {
      this.clearSession();
      throw new Error('Solo los usuarios administradores pueden ingresar al panel de taller.');
    }

    const session: StoredSession = {
      access_token: response.access_token,
      token_type: response.token_type,
      user: response.user,
    };

    this.setSession(session);
    return response.user;
  }

  async ensureUserLoaded(): Promise<UserProfile | null> {
    const currentSession = this.sessionSignal();
    if (!currentSession?.access_token) {
      return null;
    }

    if (this.loadingProfileSignal()) {
      return this.currentUser();
    }

    this.loadingProfileSignal.set(true);
    try {
      const profile = await firstValueFrom(
        this.http.get<UserProfile>(buildApiUrl('/auth/me')),
      );

      this.setSession({
        ...currentSession,
        user: profile,
      });

      return profile;
    } catch {
      this.clearSession();
      return null;
    } finally {
      this.loadingProfileSignal.set(false);
    }
  }

  logout(): void {
    this.clearSession();
  }

  private setSession(session: StoredSession): void {
    this.sessionSignal.set(session);
    localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
  }

  private clearSession(): void {
    this.sessionSignal.set(null);
    localStorage.removeItem(SESSION_STORAGE_KEY);
  }

  private restoreSession(): StoredSession | null {
    const rawSession = localStorage.getItem(SESSION_STORAGE_KEY);
    if (!rawSession) {
      return null;
    }

    try {
      return JSON.parse(rawSession) as StoredSession;
    } catch {
      localStorage.removeItem(SESSION_STORAGE_KEY);
      return null;
    }
  }
}

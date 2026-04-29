import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { buildApiUrl } from '../config/api.config';
import { LoginRequest, LoginResponse, StoredSession, UserProfile } from './auth.models';
import { TokenStorageService } from './token-storage.service';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly tokenStorage = inject(TokenStorageService);

  private readonly sessionSignal = signal<StoredSession | null>(this.tokenStorage.restoreSession());
  private readonly loadingProfileSignal = signal(false);

  readonly session = computed(() => this.sessionSignal());
  readonly currentUser = computed(() => this.sessionSignal()?.user ?? null);

  async login(payload: LoginRequest): Promise<UserProfile> {
    const response = await firstValueFrom(
      this.http.post<LoginResponse>(buildApiUrl('/auth/login'), payload),
    );

    if (
      !response ||
      !response.user ||
      !response.access_token ||
      !response.token_type
    ) {
      throw new Error(
        'No se pudo iniciar sesion. Verifica la conexion con el servidor.',
      );
    }

    const resolvedRole = this.resolveRole(response.user, response.role);
    if (resolvedRole !== 'ADMINISTRADOR') {
      this.clearSession();
      throw new Error('Solo los usuarios administradores pueden ingresar al panel de taller.');
    }

    const normalizedUser: UserProfile = {
      ...response.user,
      role: resolvedRole,
      tipo_usuario: response.user.tipo_usuario ?? resolvedRole,
    };

    const session: StoredSession = {
      access_token: response.access_token,
      token_type: response.token_type,
      user: normalizedUser,
    };

    this.setSession(session);
    return normalizedUser;
  }

  async loginAsAdmin(payload: LoginRequest): Promise<UserProfile> {
    return this.login(payload);
  }

  async getMe(): Promise<UserProfile | null> {
    return this.refreshCurrentUser();
  }

  async refreshCurrentUser(): Promise<UserProfile | null> {
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
      const resolvedRole = this.resolveRole(profile, profile.role);
      const normalizedUser: UserProfile = {
        ...profile,
        role: resolvedRole,
        tipo_usuario: profile.tipo_usuario ?? resolvedRole,
      };

      this.setSession({
        ...currentSession,
        user: normalizedUser,
      });

      return normalizedUser;
    } catch {
      this.clearSession();
      return null;
    } finally {
      this.loadingProfileSignal.set(false);
    }
  }

  async ensureUserLoaded(): Promise<UserProfile | null> {
    const currentUser = this.currentUser();
    if (currentUser) {
      return currentUser;
    }
    return this.refreshCurrentUser();
  }

  getToken(): string | null {
    return this.sessionSignal()?.access_token ?? this.tokenStorage.getToken();
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  getCurrentUser(): UserProfile | null {
    return this.currentUser();
  }

  isAdmin(): boolean {
    return this.resolveRole(this.currentUser(), this.currentUser()?.role) === 'ADMINISTRADOR';
  }

  logout(): void {
    this.clearSession();
  }

  private setSession(session: StoredSession): void {
    this.sessionSignal.set(session);
    this.tokenStorage.saveToken(session.access_token);
    this.tokenStorage.saveCurrentUser(session.user);
  }

  private clearSession(): void {
    this.sessionSignal.set(null);
    this.tokenStorage.clearAll();
  }

  private resolveRole(user: UserProfile | null | undefined, fallbackRole?: string): string {
    return user?.role ?? user?.tipo_usuario ?? fallbackRole ?? '';
  }
}

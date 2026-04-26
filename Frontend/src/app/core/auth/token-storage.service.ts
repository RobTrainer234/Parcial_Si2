import { Injectable } from '@angular/core';

import { StoredSession, UserProfile } from './auth.models';

const ACCESS_TOKEN_KEY = 'si2_access_token';
const CURRENT_USER_KEY = 'si2_current_user';
const LEGACY_SESSION_KEY = 'si2.admin.session';

@Injectable({ providedIn: 'root' })
export class TokenStorageService {
  saveToken(token: string): void {
    localStorage.setItem(ACCESS_TOKEN_KEY, token);
  }

  getToken(): string | null {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  }

  clearToken(): void {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
  }

  saveCurrentUser(user: UserProfile): void {
    localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(user));
  }

  getCurrentUser(): UserProfile | null {
    const raw = localStorage.getItem(CURRENT_USER_KEY);
    if (!raw) {
      return null;
    }

    try {
      return JSON.parse(raw) as UserProfile;
    } catch {
      localStorage.removeItem(CURRENT_USER_KEY);
      return null;
    }
  }

  clearCurrentUser(): void {
    localStorage.removeItem(CURRENT_USER_KEY);
  }

  clearAll(): void {
    this.clearToken();
    this.clearCurrentUser();
    localStorage.removeItem(LEGACY_SESSION_KEY);
  }

  restoreSession(): StoredSession | null {
    const token = this.getToken();
    const user = this.getCurrentUser();
    if (token && user) {
      return {
        access_token: token,
        token_type: 'bearer',
        user,
      };
    }

    const legacyRaw = localStorage.getItem(LEGACY_SESSION_KEY);
    if (!legacyRaw) {
      return null;
    }

    try {
      const legacySession = JSON.parse(legacyRaw) as StoredSession;
      if (legacySession.access_token && legacySession.user) {
        this.saveToken(legacySession.access_token);
        this.saveCurrentUser(legacySession.user);
        localStorage.removeItem(LEGACY_SESSION_KEY);
        return {
          access_token: legacySession.access_token,
          token_type: legacySession.token_type ?? 'bearer',
          user: legacySession.user,
        };
      }
    } catch {
      localStorage.removeItem(LEGACY_SESSION_KEY);
    }

    return null;
  }
}

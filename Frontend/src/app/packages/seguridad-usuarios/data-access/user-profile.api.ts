import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { buildApiUrl } from '../../../core/config/api.config';
import { ProfileMeResponse, ProfileUpdateRequest } from './user-profile.models';

@Injectable({ providedIn: 'root' })
export class UserProfileApi {
  private readonly http = inject(HttpClient);

  getProfile(): Observable<ProfileMeResponse> {
    return this.http.get<ProfileMeResponse>(buildApiUrl('/profile/me'));
  }

  updateProfile(payload: ProfileUpdateRequest): Observable<ProfileMeResponse> {
    return this.http.patch<ProfileMeResponse>(buildApiUrl('/profile/me'), payload);
  }
}

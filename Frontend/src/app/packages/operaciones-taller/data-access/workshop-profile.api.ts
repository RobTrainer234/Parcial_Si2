import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';

import { buildApiUrl } from '../../../core/config/api.config';
import {
  WorkshopMediaFileResponse,
  WorkshopProfileResponse,
  WorkshopProfileUpdateRequest,
} from './workshop-profile.models';

@Injectable({ providedIn: 'root' })
export class WorkshopProfileApi {
  private readonly http = inject(HttpClient);

  getProfile() {
    return this.http.get<WorkshopProfileResponse>(buildApiUrl('/workshop/profile'));
  }

  updateProfile(payload: WorkshopProfileUpdateRequest) {
    return this.http.put<WorkshopProfileResponse>(
      buildApiUrl('/workshop/profile'),
      payload,
    );
  }

  listMedia() {
    return this.http.get<WorkshopMediaFileResponse[]>(
      buildApiUrl('/workshop/profile/media'),
    );
  }

  uploadMedia(
    tipoArchivo: 'IMAGEN_TALLER' | 'CERTIFICADO_TECNICO',
    file: File,
    descripcion?: string | null,
  ) {
    const formData = new FormData();
    formData.append('tipo_archivo', tipoArchivo);
    formData.append('file', file);
    if (descripcion?.trim()) {
      formData.append('descripcion', descripcion.trim());
    }

    return this.http.post<WorkshopMediaFileResponse>(
      buildApiUrl('/workshop/profile/media'),
      formData,
    );
  }

  deactivateMedia(fileId: number) {
    return this.http.patch<WorkshopMediaFileResponse>(
      buildApiUrl(`/workshop/profile/media/${fileId}/deactivate`),
      {},
    );
  }
}

export interface WorkshopConfiguredSpecialty {
  id_especialidad: number;
  nombre: string;
  activo: boolean;
}

export interface WorkshopMediaFileResponse {
  id_taller_archivo: number;
  tipo_archivo: string;
  nombre_archivo: string;
  url_archivo: string;
  mime_type: string | null;
  tamano_bytes: number | null;
  fecha_registro: string;
  descripcion: string | null;
  activo: boolean;
}

export interface WorkshopProfileUpdateRequest {
  nombre_comercial: string;
  descripcion: string | null;
  latitud: number;
  longitud: number;
  direccion: string | null;
  ciudad: string | null;
  zona: string | null;
  referencia: string | null;
  radio_accion_km: number;
  specialty_ids: number[];
  acepta_seguro_propio: boolean;
}

export interface WorkshopProfileResponse {
  workshop_id: number;
  nombre_comercial: string;
  descripcion: string | null;
  latitud: string | number;
  longitud: string | number;
  direccion: string | null;
  ciudad: string | null;
  zona: string | null;
  referencia: string | null;
  radio_accion_km: string | number;
  activo: boolean;
  acepta_seguro_propio: boolean;
  specialties: WorkshopConfiguredSpecialty[];
  imagenes_taller: WorkshopMediaFileResponse[];
  certificados_tecnicos: WorkshopMediaFileResponse[];
}

export interface WorkshopMediaUploadRequest {
  tipo_archivo: 'IMAGEN_TALLER' | 'CERTIFICADO_TECNICO';
  descripcion?: string | null;
  file: File;
}

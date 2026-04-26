export interface StaffSpecialtyResponse {
  id_especialidad: number;
  nombre: string;
  anios_experiencia: number;
  certificacion_url: string | null;
}

export interface WorkshopStaffSummary {
  operario_id: number;
  persona_id: number;
  nombre_completo: string;
  ci: string;
  email: string;
  telefono: string | null;
  estado_disponibilidad: string;
  activo: boolean;
  specialties: StaffSpecialtyResponse[];
  registered_at: string | null;
}

export interface StaffSpecialtyInput {
  id_especialidad: number;
  anios_experiencia: number;
  certificacion_url?: string | null;
}

export interface WorkshopStaffCreateRequest {
  nombre: string;
  apellido: string;
  ci: string;
  email: string;
  password: string;
  telefono?: string | null;
  direccion?: string | null;
  specialties: StaffSpecialtyInput[];
}

export type StaffAvailabilityStatus =
  | 'DISPONIBLE'
  | 'EN_SERVICIO'
  | 'NO_DISPONIBLE'
  | 'BAJA';

export interface WorkshopStaffAvailabilityUpdateRequest {
  new_status: StaffAvailabilityStatus;
  reason?: string | null;
}

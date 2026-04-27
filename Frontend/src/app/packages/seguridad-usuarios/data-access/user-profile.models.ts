import { UserProfile } from '../../../core/auth/auth.models';

export interface PersonaProfile {
  nombre: string;
  apellido: string;
  ci: string;
  telefono?: string | null;
  direccion?: string | null;
}

export interface ProfileMeResponse {
  persona: PersonaProfile;
  user: UserProfile;
}

export interface ProfileUpdateRequest {
  nombre?: string | null;
  apellido?: string | null;
  telefono?: string | null;
  direccion?: string | null;
}

export interface ActorContext {
  cliente_persona_id: number | null;
  administrador_persona_id: number | null;
  operario_id: number | null;
  taller_id: number | null;
  taller_ids: number[] | null;
}

export interface UserProfile {
  user_id: number;
  persona_id: number;
  role?: string;
  tipo_usuario?: string;
  email: string;
  phone: string | null;
  actor_context: ActorContext;
  home_hint: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  role: string;
  user: UserProfile;
  actor_context: ActorContext;
  home_hint: string;
}

export interface StoredSession {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

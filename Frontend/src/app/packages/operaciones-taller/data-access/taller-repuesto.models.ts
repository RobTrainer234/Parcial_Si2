export interface TallerRepuestoResponse {
  id_taller_repuesto: number;
  id_taller: number;
  nombre: string;
  descripcion: string | null;
  precio_unitario: number | string;
  activo: boolean;
  created_at?: string | null;
}

export interface TallerRepuestoCreateRequest {
  nombre: string;
  descripcion?: string | null;
  precio_unitario: number | string;
}

export interface TallerRepuestoUpdateRequest {
  nombre?: string | null;
  descripcion?: string | null;
  precio_unitario?: number | string | null;
  activo?: boolean | null;
}

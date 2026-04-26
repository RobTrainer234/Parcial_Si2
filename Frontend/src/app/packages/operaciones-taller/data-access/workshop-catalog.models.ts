export interface WorkshopCatalogServiceResponse {
  catalog_id: number;
  workshop_id: number;
  id_especialidad: number;
  especialidad_nombre: string;
  nombre: string;
  descripcion: string | null;
  precio_base_min: string | number;
  precio_base_max: string | number;
  incluye_repuestos_basicos: boolean;
  activo: boolean;
}

export interface WorkshopCatalogServiceCreateRequest {
  id_especialidad: number;
  nombre: string;
  descripcion: string | null;
  precio_base_min: number;
  precio_base_max: number;
  incluye_repuestos_basicos: boolean;
}

export interface WorkshopCatalogServiceUpdateRequest {
  id_especialidad?: number;
  nombre?: string;
  descripcion?: string | null;
  precio_base_min?: number;
  precio_base_max?: number;
  incluye_repuestos_basicos?: boolean;
  activo?: boolean;
}

export interface WorkshopSpecialtyOption {
  id_especialidad: number;
  nombre: string;
}

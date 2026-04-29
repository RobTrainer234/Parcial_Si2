const BACKEND_MESSAGE_MAP = new Map<string, string>([
  [
    'An active hiring request already exists for this workshop.',
    'Ya existe una solicitud activa para este taller.',
  ],
  [
    'No active matchmaking request.',
    'No hay una solicitud activa en este momento.',
  ],
  [
    'Top workshop candidate selected and request created.',
    'Se selecciono un taller compatible y se envio la solicitud.',
  ],
  [
    'Active matchmaking request found.',
    'Hay una solicitud activa en curso.',
  ],
  [
    'Incident is not eligible for matchmaking.',
    'El incidente aun no esta listo para buscar taller.',
  ],
  [
    'Incident requires manual review before matchmaking.',
    'El incidente requiere revision antes de buscar taller.',
  ],
  [
    'Triage AI provider is not configured.',
    'El diagnostico automatico no esta configurado.',
  ],
  [
    'Triage AI provider quota is exhausted or billing is unavailable.',
    'El proveedor de diagnostico no tiene cuota disponible en este momento.',
  ],
  [
    'Triage AI returned an invalid response.',
    'No se pudo interpretar la respuesta del diagnostico automatico.',
  ],
  [
    'Triage AI provider blocked the request. Check API key, network, or client headers.',
    'No se pudo completar el diagnostico automatico en este momento.',
  ],
  [
    'No active catalog service matches the detected specialty.',
    'No existe un servicio activo en el catalogo para la especialidad detectada.',
  ],
  [
    'Configure CU26 catalog before accepting.',
    'Configura el catalogo del taller antes de aceptar esta solicitud.',
  ],
  [
    'No longer waiting assignment.',
    'El servicio ya no esta en espera de asignacion.',
  ],
  [
    'Candidate not found for this workshop.',
    'El operario no pertenece a este taller.',
  ],
  [
    'Not currently available.',
    'El operario seleccionado ya no esta disponible.',
  ],
  [
    'Does not match the detected specialty.',
    'El operario no cubre la especialidad detectada.',
  ],
  [
    'Not eligible for operario assignment.',
    'Actualiza la lista e intenta nuevamente.',
  ],
  [
    'Workshop request accepted and service created.',
    'Solicitud aceptada. Servicio creado correctamente.',
  ],
  [
    'The request is no longer pending.',
    'La solicitud ya no esta pendiente.',
  ],
  [
    'Service assigned successfully.',
    'Operario asignado correctamente.',
  ],
  [
    'No pending requests.',
    'No hay solicitudes pendientes.',
  ],
]);

const STATUS_LABEL_MAP = new Map<string, string>([
  ['REPORTADO', 'Reportado'],
  ['EN_TRIAJE', 'En diagnostico'],
  ['DIAGNOSTICADO', 'Diagnosticado'],
  ['EN_MATCHMAKING', 'En busqueda de taller'],
  ['PENDIENTE', 'Pendiente'],
  ['ACEPTADA', 'Aceptada'],
  ['RECHAZADA', 'Rechazada'],
  ['EXPIRADA', 'Expirada'],
  ['EN_PROCESO', 'En proceso'],
  ['EN_ESPERA_ASIGNACION', 'En espera de asignacion'],
  ['ASIGNADO', 'Asignado'],
  ['EN_SERVICIO', 'En servicio'],
  ['EN_CAMINO', 'En camino'],
  ['EN_SITIO', 'En sitio'],
  ['EN_DIAGNOSTICO_FISICO', 'Diagnostico fisico'],
  ['EN_REPARACION', 'En reparacion'],
  ['ESPERANDO_REPUESTOS', 'Esperando repuestos'],
  ['COMPLETADO_PENDIENTE_CONFIRMACION', 'Pendiente de confirmacion'],
  ['FINALIZADO_PENDIENTE_PAGO', 'Pendiente de pago'],
  ['PAGADO', 'Pagado'],
  ['CONFIRMADO', 'Confirmado'],
  ['ANULADO', 'Anulado'],
  ['BAJA', 'Baja'],
  ['DISPONIBLE', 'Disponible'],
  ['NO_DISPONIBLE', 'No disponible'],
  ['FALLIDA', 'Fallida'],
]);

export function localizeBackendMessage(raw: string | null | undefined): string {
  const value = String(raw ?? '').trim();
  if (!value) {
    return '';
  }

  const exact = BACKEND_MESSAGE_MAP.get(value);
  if (exact) {
    return exact;
  }

  const normalized = value.toLowerCase();
  if (normalized.includes('manual review')) {
    return 'El incidente requiere revision antes de continuar.';
  }
  if (normalized.includes('active hiring request')) {
    return 'Ya existe una solicitud activa para este taller.';
  }
  if (normalized.includes('no active matchmaking request')) {
    return 'No hay una solicitud activa en este momento.';
  }
  if (normalized.includes('top workshop candidate selected')) {
    return 'Se selecciono un taller compatible y se envio la solicitud.';
  }
  if (normalized.includes('provider quota') || normalized.includes('billing is unavailable')) {
    return 'El proveedor de diagnostico no tiene cuota disponible en este momento.';
  }
  if (normalized.includes('workshop request accepted and service created')) {
    return 'Solicitud aceptada. Servicio creado correctamente.';
  }
  if (normalized.includes('the request is no longer pending')) {
    return 'La solicitud ya no esta pendiente.';
  }
  if (normalized.includes('service assigned successfully')) {
    return 'Operario asignado correctamente.';
  }
  if (normalized.includes('no pending requests')) {
    return 'No hay solicitudes pendientes.';
  }
  if (normalized.includes('triage ai provider is not configured')) {
    return 'El diagnostico automatico no esta configurado.';
  }
  if (normalized.includes('triage ai returned an invalid response')) {
    return 'No se pudo interpretar la respuesta del diagnostico automatico.';
  }

  return value;
}

export function formatLocalDateTime(
  value: string | Date | null | undefined,
): string {
  if (!value) {
    return 'Fecha no disponible';
  }

  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  const day = String(date.getDate()).padStart(2, '0');
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const year = date.getFullYear();
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  return `${day}/${month}/${year} ${hours}:${minutes}`;
}

export function localizeStatusLabel(raw: string | null | undefined): string {
  const value = String(raw ?? '').trim();
  if (!value) {
    return 'Sin estado';
  }

  const exact = STATUS_LABEL_MAP.get(value.toUpperCase());
  if (exact) {
    return exact;
  }

  if (/^[A-Z0-9_]+$/.test(value) || value.includes('_')) {
    const humanized = value
      .toLowerCase()
      .split('_')
      .filter(Boolean)
      .join(' ');
    return humanized.charAt(0).toUpperCase() + humanized.slice(1);
  }

  return value;
}

String localizeBackendMessage(String? raw) {
  final value = raw?.trim() ?? '';
  if (value.isEmpty) {
    return '';
  }

  switch (value) {
    case 'An active hiring request already exists for this workshop.':
      return 'Ya existe una solicitud activa para este taller.';
    case 'No active matchmaking request.':
      return 'No hay una solicitud activa en este momento.';
    case 'Top workshop candidate selected and request created.':
      return 'Se selecciono un taller compatible y se envio la solicitud.';
    case 'Active matchmaking request found.':
      return 'Hay una solicitud activa en curso.';
    case 'Incident is not eligible for matchmaking.':
      return 'El incidente aun no esta listo para buscar taller.';
    case 'Incident requires manual review before matchmaking.':
      return 'El incidente requiere revision antes de buscar taller.';
    case 'Triage AI provider is not configured.':
      return 'El diagnostico automatico no esta configurado.';
    case 'Triage AI provider quota is exhausted or billing is unavailable.':
      return 'El proveedor de diagnostico no tiene cuota disponible en este momento.';
    case 'Triage AI returned an invalid response.':
      return 'No se pudo interpretar la respuesta del diagnostico automatico.';
    case 'Triage AI provider blocked the request. Check API key, network, or client headers.':
      return 'No se pudo completar el diagnostico automatico en este momento.';
    case 'Assigned service not found.':
      return 'No se encontro el servicio asignado.';
    case 'Service is not in a valid state for the structured profile.':
      return 'El servicio no esta en un estado valido para esta accion.';
    case 'Incident is not in a compatible state for the structured profile.':
      return 'El incidente no esta en un estado compatible para esta accion.';
    case 'AI triage result is not ready for this service.':
      return 'El diagnostico de IA todavia no esta listo para este servicio.';
    case 'Incident still requires manual review before operario briefing.':
      return 'El incidente requiere revision antes de continuar con el operario.';
    case 'Structured profile must be acknowledged before navigation starts.':
      return 'Primero debes revisar el perfil tecnico del servicio.';
    case 'Service is not ready to start navigation.':
      return 'El servicio no esta listo para iniciar la ruta.';
    case 'Incident destination coordinates are not available.':
      return 'La ubicacion del incidente no esta disponible.';
    case 'Route provider could not build a navigation route.':
      return 'No se pudo calcular la ruta al incidente.';
    case 'Service is not in a navigation-compatible state.':
      return 'El servicio no esta en un estado valido para navegacion.';
    case 'Service is not in a progress-compatible state.':
      return 'El servicio no esta en un estado valido para esta accion.';
    case 'Requested service state transition is not allowed.':
      return 'El servicio no esta en un estado valido para esta accion.';
    case 'Navigation started successfully.':
      return 'Ruta iniciada correctamente.';
    case 'Navigation route created successfully.':
      return 'Ruta calculada correctamente.';
    case 'Service location updated successfully.':
      return 'Ubicacion enviada correctamente.';
    case 'Operario has arrived on site.':
      return 'Se registro la llegada al lugar.';
    case 'Service progress updated successfully.':
      return 'Estado del servicio actualizado correctamente.';
    case 'Service is not in a repair-compatible state for the repair report.':
      return 'El servicio no esta listo para registrar el cierre tecnico.';
    case 'Repair report saved successfully.':
      return 'Informe tecnico guardado correctamente.';
    case 'Repair report could not be persisted.':
      return 'No se pudo guardar el informe tecnico.';
    case 'Final evidence images could not be stored.':
      return 'No se pudieron guardar las evidencias finales.';
    case 'Client service not found.':
      return 'No se encontró el servicio.';
    case 'Service is not awaiting client finalization.':
      return 'El servicio no está pendiente de confirmación del cliente.';
    case 'Repair report must exist before client finalization.':
      return 'El informe técnico todavía no está disponible.';
    case 'Service finalization confirmed successfully.':
      return 'Resolución confirmada correctamente.';
    case 'Service finalization rejected and returned to repair.':
      return 'Se registró tu inconformidad y el servicio volvió a revisión.';
    case 'Service finalization was already confirmed.':
      return 'La resolución ya fue confirmada.';
    case 'Finalization confirmation could not be persisted.':
      return 'No se pudo validar la resolución.';
    case 'Finalization rejection could not be persisted.':
      return 'No se pudo validar la resolución.';
    case 'motivo is required when rejecting finalization.':
      return 'Debes ingresar el motivo de inconformidad.';
    case 'Service is not ready for payment.':
      return 'El servicio no está pendiente de pago.';
    case 'Payment already confirmed.':
      return 'El pago ya fue confirmado.';
    case 'Cash payment registered successfully.':
      return 'Pago en efectivo registrado correctamente.';
    case 'Payment could not be persisted.':
      return 'No se pudo registrar el pago.';
    case 'Service total amount is not available for payment.':
      return 'No se pudo obtener el monto del servicio.';
    case 'Service total amount is invalid for payment.':
      return 'No se pudo obtener el monto del servicio.';
    case 'Payment method not found.':
      return 'No se encontró el método de pago.';
    case 'Payment method is inactive.':
      return 'El método de pago seleccionado no está disponible.';
    case 'Service must be paid before it can be rated.':
      return 'Debes pagar el servicio antes de calificar.';
    case 'Rating could not be persisted.':
      return 'No se pudo registrar la calificación.';
    case 'Rating created successfully.':
      return 'Calificación registrada correctamente.';
    case 'Rating updated successfully.':
      return 'Calificación actualizada correctamente.';
    case 'Rating conflicts with an existing submission.':
      return 'Este servicio ya fue calificado.';
    case 'Target workshop does not match this service.':
      return 'El destino de la calificación no corresponde a este servicio.';
    case 'Service does not have an assigned operario to rate.':
      return 'Este servicio no tiene un operario asignado para calificar.';
    case 'Target persona does not match the assigned operario.':
      return 'El destino de la calificación no corresponde al operario asignado.';
    case 'target_type must be TALLER or PERSONA.':
      return 'Debes seleccionar un destino de calificación válido.';
    default:
      return value;
  }
}

String localizeStatusLabel(String? raw) {
  final value = raw?.trim() ?? '';
  if (value.isEmpty) {
    return '-';
  }

  switch (value.toUpperCase()) {
    case 'REPORTADO':
      return 'Reportado';
    case 'EN_TRIAJE':
      return 'En diagnostico';
    case 'DIAGNOSTICADO':
      return 'Diagnosticado';
    case 'EN_MATCHMAKING':
      return 'En busqueda de taller';
    case 'PENDIENTE':
      return 'Pendiente';
    case 'ACEPTADA':
      return 'Aceptada';
    case 'RECHAZADA':
      return 'Rechazada';
    case 'EXPIRADA':
      return 'Expirada';
    case 'EN_PROCESO':
      return 'En proceso';
    case 'EN_ESPERA_ASIGNACION':
      return 'En espera de asignacion';
    case 'ASIGNADO':
      return 'Asignado';
    case 'EN_SERVICIO':
      return 'En servicio';
    case 'EN_CAMINO':
      return 'Operario en camino';
    case 'EN_SITIO':
      return 'Operario en el lugar';
    case 'EN_DIAGNOSTICO_FISICO':
      return 'Diagnostico en curso';
    case 'EN_REPARACION':
      return 'Reparacion en curso';
    case 'ESPERANDO_REPUESTOS':
      return 'Esperando repuestos';
    case 'COMPLETADO_PENDIENTE_CONFIRMACION':
      return 'Pendiente de confirmacion';
    case 'FINALIZADO_PENDIENTE_PAGO':
      return 'Pendiente de pago';
    case 'PAGADO':
      return 'Pagado';
    case 'CONFIRMADO':
      return 'Confirmado';
    case 'ANULADO':
      return 'Anulado';
    case 'FALLIDA':
      return 'Fallida';
    case 'BAJA':
      return 'Baja';
    default:
      return _humanizeCode(value);
  }
}

String localizePaymentStatusMessage(String raw) {
  switch (raw.toUpperCase()) {
    case 'PENDIENTE':
      return 'Pago pendiente de confirmacion.';
    case 'RECHAZADO':
      return 'El pago fue rechazado. Puedes intentar nuevamente.';
    case 'ANULADO':
      return 'El pago fue anulado. Puedes iniciar un nuevo pago.';
    case 'CONFIRMADO':
      return 'Pago confirmado.';
    default:
      return localizeStatusLabel(raw);
  }
}

String _humanizeCode(String value) {
  final looksLikeCode =
      RegExp(r'^[A-Z0-9_]+$').hasMatch(value) || value.contains('_');
  if (!looksLikeCode) {
    return value;
  }

  final words = value
      .toLowerCase()
      .split('_')
      .where((part) => part.isNotEmpty)
      .toList();
  if (words.isEmpty) {
    return value;
  }

  final sentence = words.join(' ');
  return sentence[0].toUpperCase() + sentence.substring(1);
}

String localizeSpecialtyLabel(String? raw) {
  final value = raw?.trim() ?? '';
  if (value.isEmpty) {
    return '-';
  }

  switch (value.toUpperCase()) {
    case 'MECANICA_GENERAL':
    case 'MECANICA GENERAL':
      return 'Mecánica general';
    case 'DIAGNOSTICO_GENERAL':
    case 'DIAGNOSTICO GENERAL':
      return 'Diagnóstico general';
    case 'BATERIA':
      return 'Batería';
    case 'GRUA':
      return 'Grúa';
    case 'LLANTAS':
      return 'Llantas';
    case 'ELECTRICIDAD':
      return 'Electricidad';
    case 'AIRE ACONDICIONADO':
      return 'Aire acondicionado';
    case 'MECANICA':
    case 'MECÁNICA':
      return 'Mecánica';
    default:
      return _humanizeCode(value);
  }
}

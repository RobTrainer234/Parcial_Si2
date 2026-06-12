enum OfflineIncidentSyncStatus {
  pendienteSync,
  sincronizando,
  sincronizado,
  errorSync;

  String get value {
    switch (this) {
      case OfflineIncidentSyncStatus.pendienteSync:
        return 'PENDIENTE_SYNC';
      case OfflineIncidentSyncStatus.sincronizando:
        return 'SINCRONIZANDO';
      case OfflineIncidentSyncStatus.sincronizado:
        return 'SINCRONIZADO';
      case OfflineIncidentSyncStatus.errorSync:
        return 'ERROR_SYNC';
    }
  }

  static OfflineIncidentSyncStatus fromValue(String? value) {
    switch (value) {
      case 'SINCRONIZANDO':
        return OfflineIncidentSyncStatus.sincronizando;
      case 'SINCRONIZADO':
        return OfflineIncidentSyncStatus.sincronizado;
      case 'ERROR_SYNC':
        return OfflineIncidentSyncStatus.errorSync;
      case 'PENDIENTE_SYNC':
      default:
        return OfflineIncidentSyncStatus.pendienteSync;
    }
  }
}

class OfflineIncidentQueueItem {
  final String localUuid;
  final int clientPersonaId;
  final int vehicleId;
  final String description;
  final int specialtyId;
  final String specialtyLabel;
  final double latitud;
  final double longitud;
  final List<String> photoPaths;
  final String? audioPath;
  final OfflineIncidentSyncStatus status;
  final DateTime createdAtLocal;
  final String? lastError;
  final int? serverIncidentId;

  const OfflineIncidentQueueItem({
    required this.localUuid,
    required this.clientPersonaId,
    required this.vehicleId,
    required this.description,
    required this.specialtyId,
    required this.specialtyLabel,
    required this.latitud,
    required this.longitud,
    required this.photoPaths,
    required this.audioPath,
    required this.status,
    required this.createdAtLocal,
    this.lastError,
    this.serverIncidentId,
  });

  bool get isSynced => status == OfflineIncidentSyncStatus.sincronizado;

  Map<String, dynamic> toJson() {
    return {
      'local_uuid': localUuid,
      'client_persona_id': clientPersonaId,
      'vehicle_id': vehicleId,
      'description': description,
      'specialty_id': specialtyId,
      'specialty_label': specialtyLabel,
      'latitud': latitud,
      'longitud': longitud,
      'photo_paths': photoPaths,
      'audio_path': audioPath,
      'status': status.value,
      'created_at_local': createdAtLocal.toIso8601String(),
      'last_error': lastError,
      'server_incident_id': serverIncidentId,
    };
  }

  factory OfflineIncidentQueueItem.fromJson(Map<String, dynamic> json) {
    final rawPhotoPaths = json['photo_paths'] as List<dynamic>? ?? const [];
    return OfflineIncidentQueueItem(
      localUuid: json['local_uuid'] as String? ?? '',
      clientPersonaId: json['client_persona_id'] as int? ?? 0,
      vehicleId: json['vehicle_id'] as int? ?? 0,
      description: json['description'] as String? ?? '',
      specialtyId: json['specialty_id'] as int? ?? 0,
      specialtyLabel:
          json['specialty_label'] as String? ?? 'Diagnostico general',
      latitud: _parseDouble(json['latitud']),
      longitud: _parseDouble(json['longitud']),
      photoPaths: rawPhotoPaths.map((item) => item.toString()).toList(),
      audioPath: json['audio_path'] as String?,
      status: OfflineIncidentSyncStatus.fromValue(json['status'] as String?),
      createdAtLocal:
          DateTime.tryParse(json['created_at_local'] as String? ?? '') ??
          DateTime.now(),
      lastError: json['last_error'] as String?,
      serverIncidentId: json['server_incident_id'] as int?,
    );
  }

  OfflineIncidentQueueItem copyWith({
    OfflineIncidentSyncStatus? status,
    String? lastError,
    bool clearLastError = false,
    int? serverIncidentId,
    bool clearServerIncidentId = false,
  }) {
    return OfflineIncidentQueueItem(
      localUuid: localUuid,
      clientPersonaId: clientPersonaId,
      vehicleId: vehicleId,
      description: description,
      specialtyId: specialtyId,
      specialtyLabel: specialtyLabel,
      latitud: latitud,
      longitud: longitud,
      photoPaths: photoPaths,
      audioPath: audioPath,
      status: status ?? this.status,
      createdAtLocal: createdAtLocal,
      lastError: clearLastError ? null : (lastError ?? this.lastError),
      serverIncidentId: clearServerIncidentId
          ? null
          : (serverIncidentId ?? this.serverIncidentId),
    );
  }

  static double _parseDouble(dynamic value) {
    if (value is num) return value.toDouble();
    if (value is String) return double.tryParse(value) ?? 0;
    return 0;
  }
}

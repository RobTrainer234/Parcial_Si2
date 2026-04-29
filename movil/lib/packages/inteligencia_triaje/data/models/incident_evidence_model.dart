class IncidentEvidenceModel {
  final int? evidenceId;
  final String? type;
  final String? fileUrl;
  final String? mimeType;
  final int? sizeBytes;

  const IncidentEvidenceModel({
    this.evidenceId,
    this.type,
    this.fileUrl,
    this.mimeType,
    this.sizeBytes,
  });

  factory IncidentEvidenceModel.fromJson(Map<String, dynamic> json) {
    return IncidentEvidenceModel(
      evidenceId: json['id_evidencia'] as int?,
      type: json['tipo_evidencia'] as String?,
      fileUrl: json['url_archivo'] as String?,
      mimeType: json['mime_type'] as String?,
      sizeBytes: json['tamano_bytes'] as int?,
    );
  }
}

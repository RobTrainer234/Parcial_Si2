class ActorContextModel {
  final int? clientePersonaId;
  final int? administradorPersonaId;
  final int? operarioId;
  final int? tallerId;
  final List<int>? tallerIds;

  const ActorContextModel({
    this.clientePersonaId,
    this.administradorPersonaId,
    this.operarioId,
    this.tallerId,
    this.tallerIds,
  });

  factory ActorContextModel.fromJson(Map<String, dynamic> json) {
    final rawIds = json['taller_ids'];
    return ActorContextModel(
      clientePersonaId: json['cliente_persona_id'] as int?,
      administradorPersonaId: json['administrador_persona_id'] as int?,
      operarioId: json['operario_id'] as int?,
      tallerId: json['taller_id'] as int?,
      tallerIds: rawIds != null ? (rawIds as List<dynamic>).cast<int>() : null,
    );
  }
}

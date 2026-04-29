class ActorContextModel {
  final int? clientePersonaId;
  final int? administradorPersonaId;
  final int? operarioId;
  final int? tallerId;

  const ActorContextModel({
    this.clientePersonaId,
    this.administradorPersonaId,
    this.operarioId,
    this.tallerId,
  });

  factory ActorContextModel.fromJson(Map<String, dynamic> json) {
    return ActorContextModel(
      clientePersonaId: json['cliente_persona_id'] as int?,
      administradorPersonaId: json['administrador_persona_id'] as int?,
      operarioId: json['operario_id'] as int?,
      tallerId: json['taller_id'] as int?,
    );
  }
}

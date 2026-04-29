import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/network/api_exception.dart';
import '../../../../core/routing/app_routes.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/app_page_scaffold.dart';
import '../../../../core/widgets/app_primary_button.dart';
import '../../data/models/profile_me_model.dart';
import '../../data/models/profile_update_request_model.dart';
import '../../data/models/vehicle_model.dart';
import '../../data/models/vehicle_upsert_request_model.dart';
import '../controllers/profile_controller.dart';

class ProfilePage extends ConsumerWidget {
  const ProfilePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profileState = ref.watch(profileControllerProvider);

    return AppPageScaffold(
      label: 'CUENTA',
      title: 'Perfil Cliente',
      subtitle: 'Consulta y actualiza tu información.',
      actions: IconButton(
        tooltip: 'Volver al inicio',
        icon: const Icon(Icons.arrow_back_rounded),
        onPressed: () {
          if (Navigator.of(context).canPop()) {
            context.pop();
          } else {
            context.go(AppRoutes.clientHome);
          }
        },
      ),
      child: profileState.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => _ProfileError(
          error: e,
          onRetry: () => ref.read(profileControllerProvider.notifier).refresh(),
        ),
        data: (profile) => _ProfileContent(profile: profile),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Profile content
// ---------------------------------------------------------------------------

class _ProfileContent extends ConsumerWidget {
  const _ProfileContent({required this.profile});
  final ProfileMeModel profile;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);

    return RefreshIndicator(
      onRefresh: () => ref.read(profileControllerProvider.notifier).refresh(),
      child: ListView(
        children: [
          // --- Personal data ---
          _SectionLabel(title: 'Datos personales'),
          const SizedBox(height: 12),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _InfoRow(label: 'Nombre', value: '${profile.persona.nombre} ${profile.persona.apellido}'),
                _InfoRow(label: 'CI', value: profile.persona.ci),
                _InfoRow(label: 'Teléfono', value: profile.persona.telefono ?? '—'),
                _InfoRow(label: 'Dirección', value: profile.persona.direccion ?? '—'),
                _InfoRow(label: 'Correo', value: profile.user.email),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    onPressed: () => _showEditProfile(context, ref),
                    icon: const Icon(Icons.edit_outlined, size: 18),
                    label: const Text('Editar datos'),
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),

          // --- Vehicles ---
          Row(
            children: [
              Expanded(child: _SectionLabel(title: 'Vehículos')),
              TextButton.icon(
                onPressed: () => _showVehicleForm(context, ref, null),
                icon: const Icon(Icons.add_rounded, size: 18),
                label: const Text('Agregar'),
              ),
            ],
          ),
          const SizedBox(height: 12),

          if (profile.vehicles.isEmpty)
            AppCard(
              child: Column(
                children: [
                  Icon(Icons.directions_car_outlined,
                      size: 40, color: theme.colorScheme.onSurfaceVariant),
                  const SizedBox(height: 12),
                  Text(
                    'No tienes vehículos registrados.',
                    style: theme.textTheme.bodyMedium,
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  AppPrimaryButton(
                    label: 'Agregar vehículo',
                    icon: Icons.add_rounded,
                    onPressed: () => _showVehicleForm(context, ref, null),
                  ),
                ],
              ),
            )
          else
            ...profile.vehicles.map(
              (v) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: _VehicleCard(
                  vehicle: v,
                  onEdit: () => _showVehicleForm(context, ref, v),
                  onDelete: () => _confirmDelete(context, ref, v),
                ),
              ),
            ),

          const SizedBox(height: 16),
          AppPrimaryButton(
            label: 'Ir al inicio',
            onPressed: () => context.go(AppRoutes.clientHome),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  // --- Edit profile bottom sheet ---

  void _showEditProfile(BuildContext context, WidgetRef ref) {
    final nombreCtrl = TextEditingController(text: profile.persona.nombre);
    final apellidoCtrl = TextEditingController(text: profile.persona.apellido);
    final telefonoCtrl = TextEditingController(text: profile.persona.telefono ?? '');
    final direccionCtrl = TextEditingController(text: profile.persona.direccion ?? '');
    final formKey = GlobalKey<FormState>();

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (ctx) {
        bool saving = false;
        return StatefulBuilder(
          builder: (ctx, setSheetState) {
            return Padding(
              padding: EdgeInsets.fromLTRB(
                20, 24, 20, MediaQuery.of(ctx).viewInsets.bottom + 24,
              ),
              child: Form(
                key: formKey,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text('Editar datos personales',
                        style: Theme.of(ctx).textTheme.titleLarge),
                    const SizedBox(height: 20),
                    TextFormField(
                      controller: nombreCtrl,
                      decoration: const InputDecoration(labelText: 'Nombre'),
                      textCapitalization: TextCapitalization.words,
                      maxLength: 100,
                      validator: (v) {
                        if (v == null || v.trim().isEmpty) return 'Requerido';
                        if (v.trim().length > 100) return 'Máximo 100 caracteres';
                        return null;
                      },
                      enabled: !saving,
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: apellidoCtrl,
                      decoration: const InputDecoration(labelText: 'Apellido'),
                      textCapitalization: TextCapitalization.words,
                      maxLength: 100,
                      validator: (v) {
                        if (v == null || v.trim().isEmpty) return 'Requerido';
                        if (v.trim().length > 100) return 'Máximo 100 caracteres';
                        return null;
                      },
                      enabled: !saving,
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: telefonoCtrl,
                      decoration: const InputDecoration(labelText: 'Teléfono (opcional)'),
                      keyboardType: TextInputType.phone,
                      maxLength: 20,
                      validator: (v) {
                        if (v != null && v.trim().length > 20) return 'Máximo 20 caracteres';
                        return null;
                      },
                      enabled: !saving,
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: direccionCtrl,
                      decoration: const InputDecoration(labelText: 'Dirección (opcional)'),
                      maxLength: 2000,
                      validator: (v) {
                        if (v != null && v.trim().length > 2000) return 'Máximo 2000 caracteres';
                        return null;
                      },
                      enabled: !saving,
                    ),
                    const SizedBox(height: 20),
                    AppPrimaryButton(
                      label: 'Guardar cambios',
                      isLoading: saving,
                      onPressed: saving
                          ? null
                          : () async {
                              if (!formKey.currentState!.validate()) return;
                              final n = nombreCtrl.text.trim();
                              final a = apellidoCtrl.text.trim();
                              final t = telefonoCtrl.text.trim();
                              final d = direccionCtrl.text.trim();

                              final origTel = profile.persona.telefono ?? '';
                              final origDir = profile.persona.direccion ?? '';

                              final request = ProfileUpdateRequestModel(
                                nombre: n != profile.persona.nombre ? n : null,
                                apellido: a != profile.persona.apellido ? a : null,
                                telefono: (t != origTel && t.isNotEmpty) ? t : null,
                                clearTelefono: t.isEmpty && origTel.isNotEmpty,
                                direccion: (d != origDir && d.isNotEmpty) ? d : null,
                                clearDireccion: d.isEmpty && origDir.isNotEmpty,
                              );

                              if (!request.hasChanges) {
                                if (ctx.mounted) Navigator.pop(ctx);
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(content: Text('No hay cambios para guardar.')),
                                );
                                return;
                              }

                              setSheetState(() => saving = true);
                              try {
                                await ref
                                    .read(profileControllerProvider.notifier)
                                    .updateProfile(request);
                                if (ctx.mounted) Navigator.pop(ctx);
                                if (context.mounted) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    const SnackBar(content: Text('Perfil actualizado correctamente.')),
                                  );
                                }
                              } catch (e) {
                                setSheetState(() => saving = false);
                                if (ctx.mounted) {
                                  ScaffoldMessenger.of(ctx).showSnackBar(
                                    SnackBar(
                                      content: Text(_mapProfileError(e)),
                                      backgroundColor: Theme.of(ctx).colorScheme.error,
                                    ),
                                  );
                                }
                              }
                            },
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  // --- Vehicle form bottom sheet ---

  void _showVehicleForm(BuildContext context, WidgetRef ref, VehicleModel? vehicle) {
    final isEdit = vehicle != null;
    final placaCtrl = TextEditingController(text: vehicle?.placa ?? '');
    final anioCtrl = TextEditingController(text: vehicle?.anio.toString() ?? '');
    final marcaCtrl = TextEditingController(text: vehicle?.marcaNombre ?? '');
    final modeloCtrl = TextEditingController(text: vehicle?.modeloNombre ?? '');
    final colorCtrl = TextEditingController(text: vehicle?.colorNombre ?? '');
    final formKey = GlobalKey<FormState>();

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (ctx) {
        bool saving = false;
        return StatefulBuilder(
          builder: (ctx, setSheetState) {
            return Padding(
              padding: EdgeInsets.fromLTRB(
                20, 24, 20, MediaQuery.of(ctx).viewInsets.bottom + 24,
              ),
              child: Form(
                key: formKey,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      isEdit ? 'Editar vehículo' : 'Agregar vehículo',
                      style: Theme.of(ctx).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 20),
                    TextFormField(
                      controller: placaCtrl,
                      decoration: const InputDecoration(labelText: 'Placa'),
                      textCapitalization: TextCapitalization.characters,
                      enabled: !saving,
                      validator: (v) {
                        if (v == null || v.trim().isEmpty) return 'Requerido';
                        if (v.trim().length < 3) return 'Mínimo 3 caracteres';
                        if (v.trim().length > 15) return 'Máximo 15 caracteres';
                        return null;
                      },
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: anioCtrl,
                      decoration: const InputDecoration(labelText: 'Año'),
                      keyboardType: TextInputType.number,
                      enabled: !saving,
                      validator: (v) {
                        if (v == null || v.trim().isEmpty) return 'Requerido';
                        final y = int.tryParse(v.trim());
                        if (y == null || y < 1900 || y > 2100) return 'Entre 1900 y 2100';
                        return null;
                      },
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: marcaCtrl,
                      decoration: const InputDecoration(labelText: 'Marca'),
                      textCapitalization: TextCapitalization.words,
                      maxLength: 50,
                      enabled: !saving,
                      validator: (v) {
                        if (v == null || v.trim().isEmpty) return 'Requerido';
                        if (v.trim().length > 50) return 'Máximo 50 caracteres';
                        return null;
                      },
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: modeloCtrl,
                      decoration: const InputDecoration(labelText: 'Modelo'),
                      textCapitalization: TextCapitalization.words,
                      maxLength: 50,
                      enabled: !saving,
                      validator: (v) {
                        if (v == null || v.trim().isEmpty) return 'Requerido';
                        if (v.trim().length > 50) return 'Máximo 50 caracteres';
                        return null;
                      },
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: colorCtrl,
                      decoration: const InputDecoration(labelText: 'Color'),
                      textCapitalization: TextCapitalization.words,
                      maxLength: 30,
                      enabled: !saving,
                      validator: (v) {
                        if (v == null || v.trim().isEmpty) return 'Requerido';
                        if (v.trim().length > 30) return 'Máximo 30 caracteres';
                        return null;
                      },
                    ),
                    const SizedBox(height: 20),
                    AppPrimaryButton(
                      label: isEdit ? 'Guardar cambios' : 'Agregar vehículo',
                      isLoading: saving,
                      onPressed: saving
                          ? null
                          : () async {
                              if (!formKey.currentState!.validate()) return;
                              setSheetState(() => saving = true);
                              try {
                                if (isEdit) {
                                  final patch = <String, dynamic>{};
                                  final p = placaCtrl.text.trim().toUpperCase();
                                  final a = int.parse(anioCtrl.text.trim());
                                  final m = marcaCtrl.text.trim();
                                  final mo = modeloCtrl.text.trim();
                                  final c = colorCtrl.text.trim();
                                  if (p != vehicle.placa) patch['placa'] = p;
                                  if (a != vehicle.anio) patch['anio'] = a;
                                  if (m != vehicle.marcaNombre) patch['marca_nombre'] = m;
                                  if (mo != vehicle.modeloNombre) patch['modelo_nombre'] = mo;
                                  if (c != vehicle.colorNombre) patch['color_nombre'] = c;

                                  if (patch.isEmpty) {
                                    if (ctx.mounted) Navigator.pop(ctx);
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      const SnackBar(content: Text('No hay cambios para guardar.')),
                                    );
                                    return;
                                  }
                                  await ref
                                      .read(profileControllerProvider.notifier)
                                      .updateVehicle(vehicle.idVehiculo, patch);
                                } else {
                                  final request = VehicleUpsertRequestModel(
                                    placa: placaCtrl.text.trim().toUpperCase(),
                                    anio: int.parse(anioCtrl.text.trim()),
                                    marcaNombre: marcaCtrl.text.trim(),
                                    modeloNombre: modeloCtrl.text.trim(),
                                    colorNombre: colorCtrl.text.trim(),
                                  );
                                  await ref
                                      .read(profileControllerProvider.notifier)
                                      .createVehicle(request);
                                }

                                if (ctx.mounted) Navigator.pop(ctx);
                                if (context.mounted) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(
                                      content: Text(
                                        isEdit
                                            ? 'Vehículo actualizado correctamente.'
                                            : 'Vehículo agregado correctamente.',
                                      ),
                                    ),
                                  );
                                }
                              } catch (e) {
                                setSheetState(() => saving = false);
                                if (ctx.mounted) {
                                  ScaffoldMessenger.of(ctx).showSnackBar(
                                    SnackBar(
                                      content: Text(_mapVehicleError(e)),
                                      backgroundColor: Theme.of(ctx).colorScheme.error,
                                    ),
                                  );
                                }
                              }
                            },
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  // --- Delete confirmation ---

  void _confirmDelete(BuildContext context, WidgetRef ref, VehicleModel vehicle) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('¿Eliminar vehículo?'),
        content: Text(
          'Esta acción quitará ${vehicle.marcaNombre} ${vehicle.modeloNombre} (${vehicle.placa}) de tu perfil.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancelar'),
          ),
          TextButton(
            onPressed: () async {
              Navigator.pop(ctx);
              try {
                await ref
                    .read(profileControllerProvider.notifier)
                    .deleteVehicle(vehicle.idVehiculo);
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Vehículo eliminado.')),
                  );
                }
              } catch (e) {
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(_mapVehicleError(e)),
                      backgroundColor: Theme.of(context).colorScheme.error,
                    ),
                  );
                }
              }
            },
            child: Text(
              'Eliminar',
              style: TextStyle(color: Theme.of(ctx).colorScheme.error),
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Error mapper helpers
// ---------------------------------------------------------------------------

String _mapProfileError(Object e) {
  if (e is ApiException) {
    if (e.statusCode == 409) return 'El teléfono ya está registrado en otra cuenta.';
    if (e.statusCode == 422 || e.statusCode == 400) return 'Revisa los datos ingresados.';
    if (e.statusCode == 401 || e.statusCode == 403) return 'Tu sesión expiró. Inicia sesión nuevamente.';
    if (e.statusCode != null && e.statusCode! >= 500) return 'No se pudo actualizar el perfil por un problema del servidor.';
  }
  return 'No se pudo conectar con el servidor. Revisa tu conexión.';
}

String _mapVehicleError(Object e) {
  if (e is ApiException) {
    final d = e.details?.toString().toLowerCase() ?? '';
    if (e.statusCode == 409) {
      if (d.contains('placa') || d.contains('plate')) return 'Esa placa ya está registrada.';
      if (d.contains('registros') || d.contains('referenced')) {
        return 'No se puede eliminar este vehículo porque ya tiene registros asociados.';
      }
      return 'Conflicto con datos existentes.';
    }
    if (e.statusCode == 422 || e.statusCode == 400) return 'Revisa los datos ingresados.';
    if (e.statusCode == 404) return 'No se encontró la información solicitada.';
    if (e.statusCode == 401 || e.statusCode == 403) return 'Tu sesión expiró. Inicia sesión nuevamente.';
    if (e.statusCode != null && e.statusCode! >= 500) return 'Ocurrió un problema del servidor.';
  }
  return 'No se pudo conectar con el servidor. Revisa tu conexión.';
}

// ---------------------------------------------------------------------------
// Private widgets
// ---------------------------------------------------------------------------

class _ProfileError extends StatelessWidget {
  const _ProfileError({required this.error, required this.onRetry});
  final Object error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.error_outline_rounded, size: 48, color: theme.colorScheme.error),
          const SizedBox(height: 16),
          Text(_mapProfileError(error), textAlign: TextAlign.center, style: theme.textTheme.bodyMedium),
          const SizedBox(height: 16),
          OutlinedButton(onPressed: onRetry, child: const Text('Reintentar')),
        ],
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel({required this.title});
  final String title;

  @override
  Widget build(BuildContext context) {
    return Text(
      title,
      style: Theme.of(context).textTheme.titleMedium?.copyWith(
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 90,
            child: Text(label, style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
          ),
          Expanded(child: Text(value, style: theme.textTheme.bodyMedium)),
        ],
      ),
    );
  }
}

class _VehicleCard extends StatelessWidget {
  const _VehicleCard({
    required this.vehicle,
    required this.onEdit,
    required this.onDelete,
  });

  final VehicleModel vehicle;
  final VoidCallback onEdit;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return AppCard(
      child: Row(
        children: [
          CircleAvatar(
            radius: 22,
            backgroundColor: theme.colorScheme.primary.withValues(alpha: 0.12),
            foregroundColor: theme.colorScheme.primary,
            child: const Icon(Icons.directions_car_rounded, size: 22),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${vehicle.marcaNombre} ${vehicle.modeloNombre}',
                  style: theme.textTheme.titleMedium,
                ),
                const SizedBox(height: 4),
                Text(
                  '${vehicle.placa}  •  ${vehicle.anio}  •  ${vehicle.colorNombre}',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
          IconButton(
            tooltip: 'Editar',
            icon: const Icon(Icons.edit_outlined, size: 20),
            onPressed: onEdit,
          ),
          IconButton(
            tooltip: 'Eliminar',
            icon: Icon(Icons.delete_outline_rounded, size: 20, color: theme.colorScheme.error),
            onPressed: onDelete,
          ),
        ],
      ),
    );
  }
}

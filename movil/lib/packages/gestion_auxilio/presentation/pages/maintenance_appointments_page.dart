import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/app_page_scaffold.dart';
import '../../../seguridad_usuarios/presentation/controllers/profile_controller.dart';
import '../../data/models/maintenance_appointment_model.dart';
import '../../data/repositories/client_history_repository.dart';

final maintenanceAppointmentsProvider = FutureProvider<List<MaintenanceAppointmentModel>>((ref) {
  return ref.watch(clientHistoryRepositoryProvider).getAppointments();
});

class MaintenanceAppointmentsPage extends ConsumerWidget {
  const MaintenanceAppointmentsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final appointments = ref.watch(maintenanceAppointmentsProvider);
    return AppPageScaffold(
      label: 'MANTENIMIENTO',
      title: 'Mantenimiento preventivo',
      subtitle: 'Programa revisiones sin esperar a una emergencia.',
      actions: IconButton(
        onPressed: () => _openCreateDialog(context, ref),
        icon: const Icon(Icons.add_circle_outline),
      ),
      child: appointments.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => Center(child: FilledButton(onPressed: () => ref.invalidate(maintenanceAppointmentsProvider), child: const Text('Reintentar'))),
        data: (items) => items.isEmpty
            ? Center(child: FilledButton.icon(onPressed: () => _openCreateDialog(context, ref), icon: const Icon(Icons.add), label: const Text('Programar mantenimiento')))
            : RefreshIndicator(
                onRefresh: () async => ref.refresh(maintenanceAppointmentsProvider.future),
                child: ListView.separated(
                  itemCount: items.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 12),
                  itemBuilder: (context, index) => _AppointmentCard(
                    item: items[index],
                    onCancel: items[index].status == 'PENDIENTE' || items[index].status == 'CONFIRMADA'
                        ? () async {
                            await ref.read(clientHistoryRepositoryProvider).cancelAppointment(items[index].appointmentId);
                            ref.invalidate(maintenanceAppointmentsProvider);
                          }
                        : null,
                  ),
                ),
              ),
      ),
    );
  }

  Future<void> _openCreateDialog(BuildContext context, WidgetRef ref) async {
    final profile = ref.read(profileControllerProvider).valueOrNull;
    if (profile == null || profile.vehicles.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Registra un vehículo antes de programar mantenimiento.')));
      return;
    }
    final workshops = await ref.read(clientHistoryRepositoryProvider).getMaintenanceWorkshops();
    if (!context.mounted) return;
    if (workshops.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('No hay talleres disponibles.')));
      return;
    }
    var vehicleId = profile.vehicles.first.idVehiculo;
    var workshopId = workshops.first.workshopId;
    var date = DateTime.now().add(const Duration(days: 1));
    final reason = TextEditingController();
    final saved = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (_, setState) => AlertDialog(
          title: const Text('Nueva cita'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              DropdownButtonFormField<int>(initialValue: vehicleId, items: profile.vehicles.map((v) => DropdownMenuItem(value: v.idVehiculo, child: Text('${v.marcaNombre} ${v.modeloNombre} - ${v.placa}'))).toList(), onChanged: (value) => setState(() => vehicleId = value!)),
              DropdownButtonFormField<int>(initialValue: workshopId, items: workshops.map((w) => DropdownMenuItem(value: w.workshopId, child: Text(w.city == null ? w.workshopName : '${w.workshopName} (${w.city})'))).toList(), onChanged: (value) => setState(() => workshopId = value!)),
              const SizedBox(height: 12),
              ListTile(title: const Text('Fecha de la cita'), subtitle: Text('${date.day}/${date.month}/${date.year}'), trailing: const Icon(Icons.calendar_today), onTap: () async { final selected = await showDatePicker(context: dialogContext, firstDate: DateTime.now(), lastDate: DateTime.now().add(const Duration(days: 365)), initialDate: date); if (selected != null) setState(() => date = selected.add(const Duration(hours: 9))); }),
              TextField(controller: reason, decoration: const InputDecoration(labelText: 'Motivo (opcional)')),
            ]),
          ),
          actions: [TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('Cancelar')), FilledButton(onPressed: () => Navigator.pop(dialogContext, true), child: const Text('Programar'))],
        ),
      ),
    );
    if (saved == true) {
      await ref.read(clientHistoryRepositoryProvider).createAppointment(vehicleId: vehicleId, workshopId: workshopId, scheduledAt: date, reason: reason.text);
      ref.invalidate(maintenanceAppointmentsProvider);
    }
    reason.dispose();
  }
}

class _AppointmentCard extends StatelessWidget {
  const _AppointmentCard({required this.item, this.onCancel});
  final MaintenanceAppointmentModel item;
  final Future<void> Function()? onCancel;
  @override
  Widget build(BuildContext context) => AppCard(
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [const Icon(Icons.event_available_outlined), const SizedBox(width: 10), Expanded(child: Text(item.workshopName, style: Theme.of(context).textTheme.titleMedium)), Chip(label: Text(item.status))]),
      const SizedBox(height: 8), Text(item.vehicleLabel), Text('${item.scheduledAt.day.toString().padLeft(2, '0')}/${item.scheduledAt.month.toString().padLeft(2, '0')}/${item.scheduledAt.year} ${item.scheduledAt.hour.toString().padLeft(2, '0')}:${item.scheduledAt.minute.toString().padLeft(2, '0')}'), if (item.reason != null) Text(item.reason!),
      if (onCancel != null) Align(alignment: Alignment.centerRight, child: TextButton(onPressed: onCancel, child: const Text('Cancelar cita'))),
    ]),
  );
}

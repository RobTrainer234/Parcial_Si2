import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/app_page_scaffold.dart';
import '../../data/models/client_service_history_model.dart';
import '../../data/repositories/client_history_repository.dart';

final clientServiceHistoryProvider = FutureProvider<List<ClientServiceHistoryModel>>((ref) {
  return ref.watch(clientHistoryRepositoryProvider).getServiceHistory();
});

class ClientServiceHistoryPage extends ConsumerWidget {
  const ClientServiceHistoryPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final history = ref.watch(clientServiceHistoryProvider);
    return AppPageScaffold(
      label: 'HISTORIAL',
      title: 'Mis servicios',
      subtitle: 'Consulta asistencias pasadas, pagos y calificaciones.',
      child: history.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => Center(
          child: FilledButton(
            onPressed: () => ref.invalidate(clientServiceHistoryProvider),
            child: const Text('Reintentar'),
          ),
        ),
        data: (items) => items.isEmpty
            ? const Center(child: Text('Todavía no tienes servicios registrados.'))
            : RefreshIndicator(
                onRefresh: () async => ref.refresh(clientServiceHistoryProvider.future),
                child: ListView.separated(
                  itemCount: items.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 12),
                  itemBuilder: (context, index) => _HistoryCard(item: items[index]),
                ),
              ),
      ),
    );
  }
}

class _HistoryCard extends StatelessWidget {
  const _HistoryCard({required this.item});
  final ClientServiceHistoryModel item;

  @override
  Widget build(BuildContext context) {
    final date = item.completedAt ?? item.createdAt;
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.build_circle_outlined),
              const SizedBox(width: 10),
              Expanded(child: Text(item.workshopName, style: Theme.of(context).textTheme.titleMedium)),
              Chip(label: Text(item.serviceState.replaceAll('_', ' '))),
            ],
          ),
          const SizedBox(height: 10),
          Text(item.vehicleLabel),
          Text('${date.day.toString().padLeft(2, '0')}/${date.month.toString().padLeft(2, '0')}/${date.year}'),
          if (item.finalAmount != null) Text('Total: BOB ${item.finalAmount!.toStringAsFixed(2)}'),
          if (item.rating != null) Row(children: [const Icon(Icons.star, color: Colors.amber, size: 18), Text('${item.rating}/5')]),
        ],
      ),
    );
  }
}

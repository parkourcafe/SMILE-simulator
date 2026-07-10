import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../api/models.dart';
import '../../providers/generation_flow.dart';
import '../../providers/providers.dart';
import '../privacy/photo_deletion_ui.dart';

class HistoryScreen extends ConsumerWidget {
  const HistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final history = ref.watch(historyProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('История')),
      body: RefreshIndicator(
        onRefresh: () => ref.refresh(historyProvider.future),
        child: history.when(
          data: (items) => ListView.separated(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 32),
            itemCount: items.isEmpty ? 1 : items.length,
            separatorBuilder: (_, __) => const Divider(height: 1),
            itemBuilder: (context, index) {
              if (items.isEmpty) return const _EmptyHistory();
              final generation = items[index];
              return ListTile(
                leading: const Icon(Icons.auto_awesome_outlined),
                title: const Text('Визуализация улыбки'),
                subtitle: Text(_statusLabel(generation.status)),
                onTap: generation.status == GenerationStatus.completed
                    ? () => context.push('/result/${generation.id}')
                    : null,
                trailing: IconButton(
                  tooltip: 'Удалить фото',
                  icon: const Icon(Icons.delete_outline),
                  onPressed: () => _delete(context, ref, generation),
                ),
              );
            },
          ),
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (_, __) => ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            children: const [
              SizedBox(height: 120),
              Center(child: Text('Не удалось загрузить историю. Потяните вниз.')),
            ],
          ),
        ),
      ),
    );
  }

  String _statusLabel(GenerationStatus status) => switch (status) {
        GenerationStatus.pending => 'Ожидает обработки',
        GenerationStatus.processing => 'Создаётся',
        GenerationStatus.completed => 'Готово',
        GenerationStatus.failed => 'Не удалось создать',
      };

  Future<void> _delete(
    BuildContext context,
    WidgetRef ref,
    Generation generation,
  ) async {
    final confirmed = await confirmPhotoDeletion(context);
    if (!confirmed || !context.mounted) return;

    try {
      final receipt = await ref.read(apiClientProvider).deleteGeneration(generation.id);
      if (!context.mounted) return;
      final flow = ref.read(generationFlowProvider);
      if (flow.generation?.id == generation.id) {
        ref.read(generationFlowProvider.notifier).reset();
      }
      ref.invalidate(historyProvider);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(photoDeletionMessage(receipt))),
        );
      }
    } catch (_) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Не удалось подтвердить удаление. Повторите позже.')),
        );
      }
    }
  }
}

class _EmptyHistory extends StatelessWidget {
  const _EmptyHistory();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.only(top: 120),
      child: Column(
        children: [
          Icon(Icons.photo_library_outlined, size: 44),
          SizedBox(height: 12),
          Text('Сохранённых визуализаций пока нет.'),
        ],
      ),
    );
  }
}

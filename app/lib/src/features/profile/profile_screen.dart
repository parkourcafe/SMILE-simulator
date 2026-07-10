import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../api/models.dart';
import '../../providers/generation_flow.dart';
import '../../providers/providers.dart';

class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  bool _deleting = false;

  Future<void> _deleteAllPhotos() async {
    final confirmed = await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Удалить все фото?'),
            content: const Text(
              'Все исходные фото, визуализации и технические маски будут удалены. Учётная запись и ранее отправленные заявки останутся.',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: const Text('Отмена'),
              ),
              TextButton.icon(
                style: TextButton.styleFrom(
                  foregroundColor: Theme.of(context).colorScheme.error,
                ),
                onPressed: () => Navigator.pop(context, true),
                icon: const Icon(Icons.delete_outline),
                label: const Text('Удалить все'),
              ),
            ],
          ),
        ) ??
        false;
    if (!confirmed || !mounted) return;

    setState(() => _deleting = true);
    try {
      final summary = await ref.read(apiClientProvider).deleteAllGenerationPhotos();
      if (!mounted) return;
      ref.read(generationFlowProvider.notifier).reset();
      ref.invalidate(historyProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(_summaryMessage(summary))),
        );
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Не удалось подтвердить удаление. Повторите позже.')),
        );
      }
    } finally {
      if (mounted) setState(() => _deleting = false);
    }
  }

  String _summaryMessage(PhotoDeletionSummary summary) {
    if (summary.failed > 0) {
      return 'Часть запросов не подтверждена. Повторите удаление позже.';
    }
    if (summary.pending > 0) {
      return 'Фото скрыты. Удаление из хранилища будет повторено автоматически.';
    }
    if (summary.requested == 0) return 'Фото для удаления не найдены.';
    return 'Все фото удалены.';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Профиль')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
        children: [
          Text('Данные и приватность', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          const Text(
            'Фото удаляются из закрытого хранилища. Минимальная запись без изображения может сохраняться для аудита удаления и связи с заявкой.',
          ),
          const SizedBox(height: 16),
          OutlinedButton.icon(
            style: OutlinedButton.styleFrom(
              foregroundColor: Theme.of(context).colorScheme.error,
            ),
            onPressed: _deleting ? null : _deleteAllPhotos,
            icon: _deleting
                ? const SizedBox.square(
                    dimension: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.delete_sweep_outlined),
            label: Text(_deleting ? 'Удаляем…' : 'Удалить все фото'),
          ),
          const SizedBox(height: 28),
          Text('Сеанс', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          FilledButton.icon(
            icon: const Icon(Icons.logout),
            label: const Text('Выйти'),
            onPressed: () async {
              await ref.read(authServiceProvider).signOut();
              if (context.mounted) context.go('/login');
            },
          ),
        ],
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../providers/entitlements.dart';
import '../../providers/providers.dart';

/// Home: primary upload CTA, remaining-generations counter, recent results.
class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final history = ref.watch(historyProvider);
    final entitlementLoad = ref.watch(entitlementsSyncProvider);
    final entitlements = ref.watch(entitlementsProvider);
    final canStart = entitlementLoad.hasValue && entitlements.canGenerate;
    return Scaffold(
      appBar: AppBar(
        title: const Text('AI Smile Simulator'),
        actions: [
          IconButton(
            icon: const Icon(Icons.person_outline),
            onPressed: () => context.push('/profile'),
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: entitlementLoad.when(
                  data: (_) => Text(
                    'Доступно визуализаций: ${entitlements.totalRemaining}',
                  ),
                  loading: () => const LinearProgressIndicator(),
                  error: (_, __) => Row(
                    children: [
                      const Expanded(
                        child: Text('Не удалось проверить доступный баланс'),
                      ),
                      IconButton(
                        tooltip: 'Повторить',
                        icon: const Icon(Icons.refresh),
                        onPressed: () => ref.invalidate(entitlementsSyncProvider),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 24),
            FilledButton.icon(
              icon: const Icon(Icons.camera_alt_outlined),
              label: const Text('Примерить новую улыбку'),
              onPressed: entitlementLoad.hasValue
                  ? () => context.push(canStart ? '/upload' : '/paywall')
                  : null,
            ),
            const SizedBox(height: 24),
            Text('Последние результаты', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Expanded(
              child: history.when(
                data: (items) => items.isEmpty
                    ? const Center(child: Text('Результатов пока нет'))
                    : ListView.separated(
                        itemCount: items.length,
                        separatorBuilder: (_, __) => const Divider(),
                        itemBuilder: (_, i) => ListTile(
                          title: Text('Визуализация ${items[i].id.substring(0, 8)}'),
                          subtitle: Text(items[i].status.name),
                          onTap: () => context.push('/result/${items[i].id}'),
                        ),
                      ),
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (_, __) => const Center(
                  child: Text('Не удалось загрузить историю'),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

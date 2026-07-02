import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../providers/providers.dart';

/// Home: primary upload CTA, remaining-generations counter, recent results.
class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final history = ref.watch(historyProvider);
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
            // TODO(phase-3): show real remaining count from packs/free tier.
            const Card(
              child: Padding(
                padding: EdgeInsets.all(16),
                child: Text('0 of 1 free generation used'),
              ),
            ),
            const SizedBox(height: 24),
            FilledButton.icon(
              icon: const Icon(Icons.camera_alt_outlined),
              label: const Text('Try a new smile'),
              onPressed: () => context.push('/upload'),
            ),
            const SizedBox(height: 24),
            Text('Recent', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Expanded(
              child: history.when(
                data: (items) => items.isEmpty
                    ? const Center(child: Text('No generations yet'))
                    : ListView.separated(
                        itemCount: items.length,
                        separatorBuilder: (_, __) => const Divider(),
                        itemBuilder: (_, i) => ListTile(
                          title: Text('Generation ${items[i].id.substring(0, 8)}'),
                          subtitle: Text(items[i].status.name),
                          onTap: () => context.push('/result/${items[i].id}'),
                        ),
                      ),
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (e, _) => Center(child: Text('Could not load history\n$e')),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

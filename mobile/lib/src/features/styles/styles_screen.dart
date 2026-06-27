import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../providers/providers.dart';

/// Style selector grid. Premium styles are locked until the user has a pack.
class StylesScreen extends ConsumerWidget {
  const StylesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final styles = ref.watch(stylesProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Choose a style')),
      body: styles.when(
        data: (items) => GridView.builder(
          padding: const EdgeInsets.all(16),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 2,
            childAspectRatio: 0.85,
            crossAxisSpacing: 12,
            mainAxisSpacing: 12,
          ),
          itemCount: items.length,
          itemBuilder: (_, i) {
            final s = items[i];
            return InkWell(
              // TODO(phase-3): if s.isPremium and no pack -> route to /paywall.
              onTap: () => context.push('/generating'),
              child: Card(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Expanded(
                      child: Container(
                        color: Colors.teal.withOpacity(0.1),
                        child: s.isPremium
                            ? const Icon(Icons.lock_outline)
                            : const Icon(Icons.face_retouching_natural),
                      ),
                    ),
                    Padding(
                      padding: const EdgeInsets.all(8),
                      child: Text(s.nameRu, textAlign: TextAlign.center),
                    ),
                  ],
                ),
              ),
            );
          },
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Could not load styles\n$e')),
      ),
    );
  }
}

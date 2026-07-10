import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../providers/entitlements.dart';
import '../../providers/generation_flow.dart';
import '../../providers/providers.dart';

/// Style selector grid. Premium styles are locked until the user has a pack.
class StylesScreen extends ConsumerWidget {
  const StylesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final styles = ref.watch(stylesProvider);
    final entitlementLoad = ref.watch(entitlementsSyncProvider);
    final entitlements = ref.watch(entitlementsProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Выберите стиль')),
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
            final premiumLocked = s.isPremium && entitlements.packRemaining <= 0;
            return InkWell(
              onTap: entitlementLoad.hasValue
                  ? () {
                      if (!entitlements.canGenerate || premiumLocked) {
                        context.push('/paywall');
                        return;
                      }
                      ref.read(generationFlowProvider.notifier).setStyle(s);
                      context.push('/generating');
                    }
                  : null,
              child: Card(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Expanded(
                      child: Container(
                        color: Colors.teal.withValues(alpha: 0.1),
                        child: premiumLocked
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
        error: (_, __) => const Center(child: Text('Не удалось загрузить стили')),
      ),
    );
  }
}

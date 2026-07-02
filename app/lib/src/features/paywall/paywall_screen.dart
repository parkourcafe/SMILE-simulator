import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/providers.dart';

/// Paywall: pack cards (149 / 499 / 899 ₽). Triggered at peak emotion (after result).
class PaywallScreen extends ConsumerWidget {
  const PaywallScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final packs = ref.watch(packsProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Get more generations')),
      body: packs.when(
        data: (items) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            for (final p in items)
              Card(
                child: ListTile(
                  title: Text(p.title),
                  subtitle: Text('${p.generationsTotal} generations'),
                  trailing: Text(
                    '${p.priceAmount.toStringAsFixed(0)} ${p.priceCurrency}',
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                  // TODO(phase-3): call ApiClient.purchase -> open checkout URL.
                  onTap: () {},
                ),
              ),
          ],
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Could not load packs\n$e')),
      ),
    );
  }
}

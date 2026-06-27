import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../providers/providers.dart';

/// Result screen: before/after slider + actions.
///
/// UX rules (CLAUDE.md):
///  - "Find a clinic" present on EVERY result screen (visible, not aggressive).
///  - Free results are watermarked; "Remove watermark" routes to the paywall.
///  - Paywall appears here (peak emotion), never before generation.
///  - Medical disclaimer shown on every result screen.
class ResultScreen extends ConsumerWidget {
  const ResultScreen({super.key, required this.generationId});

  final String generationId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final api = ref.watch(apiClientProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Your new smile')),
      body: FutureBuilder(
        future: api.getGeneration(generationId),
        builder: (context, snap) {
          if (!snap.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          final gen = snap.data!;
          return Column(
            children: [
              // TODO(phase-1): draggable before/after divider over the two images.
              Expanded(
                child: Container(
                  color: Colors.black12,
                  alignment: Alignment.center,
                  child: const Text('Before / After slider'),
                ),
              ),
              if (gen.hasWatermark)
                TextButton(
                  onPressed: () => context.push('/paywall'),
                  child: const Text('Remove watermark — get more'),
                ),
              Padding(
                padding: const EdgeInsets.all(16),
                child: Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  alignment: WrapAlignment.center,
                  children: [
                    _action(Icons.save_alt, 'Save', () {}),
                    _action(Icons.share, 'Share', () {}),
                    _action(Icons.refresh, 'Retry', () => context.push('/styles')),
                    FilledButton.icon(
                      icon: const Icon(Icons.location_on_outlined),
                      label: const Text('Find a clinic'),
                      onPressed: () => context.push('/clinics'),
                    ),
                  ],
                ),
              ),
              const Padding(
                padding: EdgeInsets.fromLTRB(16, 0, 16, 16),
                child: Text(
                  'Visualization only — not medical advice.',
                  style: TextStyle(fontSize: 12, color: Colors.black54),
                  textAlign: TextAlign.center,
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _action(IconData icon, String label, VoidCallback onTap) =>
      OutlinedButton.icon(icon: Icon(icon), label: Text(label), onPressed: onTap);
}

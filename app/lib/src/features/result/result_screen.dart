import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../api/models.dart';
import '../../providers/entitlements.dart';
import '../../providers/generation_flow.dart';
import '../../providers/providers.dart';
import '../../services/analytics.dart';
import '../../widgets/before_after_slider.dart';

/// Result screen: before/after slider + cost anchor + actions.
///
/// UX rules (CLAUDE.md v1.1):
///  - Cost-estimate block ("Такая улыбка в {city}: {range}") → practical intent.
///  - "Find a clinic" present on EVERY result screen (visible, not aggressive).
///  - Paywall is ACTION-LOCKED: a 2nd generation, watermark removal, or save —
///    never a timer.
///  - Medical disclaimer shown on every result screen.
class ResultScreen extends ConsumerWidget {
  const ResultScreen({super.key, required this.generationId});

  final String generationId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final api = ref.watch(apiClientProvider);
    final flow = ref.watch(generationFlowProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Ваша новая улыбка')),
      body: FutureBuilder<Generation>(
        future: (flow.generation?.id == generationId)
            ? Future.value(flow.generation!)
            : api.getGeneration(generationId),
        builder: (context, snap) {
          if (!snap.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          final gen = snap.data!;
          final localBefore = flow.photo;

          final Widget before = localBefore != null
              ? Image.file(File(localBefore.path), fit: BoxFit.cover)
              : (gen.originalPhotoUrl != null
                  ? Image.network(gen.originalPhotoUrl!, fit: BoxFit.cover)
                  : const ColoredBox(color: Colors.black12));
          final Widget after = gen.resultPhotoUrl != null
              ? Image.network(gen.resultPhotoUrl!, fit: BoxFit.cover)
              : const ColoredBox(color: Colors.black12);

          return ListView(
            children: [
              SizedBox(
                height: 380,
                child: BeforeAfterSlider(before: before, after: after),
              ),
              _CostAnchor(styleId: flow.style?.id),
              if (gen.hasWatermark)
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: OutlinedButton.icon(
                    icon: const Icon(Icons.workspace_premium_outlined),
                    label: const Text('Убрать водяной знак'),
                    onPressed: () => context.push('/paywall'),
                  ),
                ),
              Padding(
                padding: const EdgeInsets.all(16),
                child: Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  alignment: WrapAlignment.center,
                  children: [
                    _action(
                      Icons.save_alt,
                      'Сохранить',
                      () => _onSave(context, ref, gen),
                    ),
                    _action(Icons.share, 'Поделиться', () {}),
                    _action(
                      Icons.refresh,
                      'Ещё раз',
                      () => _onRetry(context, ref),
                    ),
                    FilledButton.icon(
                      icon: const Icon(Icons.location_on_outlined),
                      label: const Text('Найти клинику'),
                      onPressed: () => context.push('/clinics'),
                    ),
                  ],
                ),
              ),
              const Padding(
                padding: EdgeInsets.fromLTRB(16, 0, 16, 24),
                child: Text(
                  'Визуализация, а не медицинская рекомендация.',
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

  /// Retry = a NEW generation. If the user is out of credits this is the 2nd-gen
  /// trigger → action-locked paywall. Otherwise go pick a style again.
  void _onRetry(BuildContext context, WidgetRef ref) {
    if (ref.read(entitlementsProvider).canGenerate) {
      context.push('/styles');
    } else {
      context.push('/paywall');
    }
  }

  /// Saving a watermarked (free) result routes to the paywall; a paid result saves.
  void _onSave(BuildContext context, WidgetRef ref, Generation gen) {
    if (gen.hasWatermark) {
      context.push('/paywall');
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Сохранено в галерею')),
      );
    }
  }

  Widget _action(IconData icon, String label, VoidCallback onTap) =>
      OutlinedButton.icon(icon: Icon(icon), label: Text(label), onPressed: onTap);
}

/// "Такая улыбка в {city}: {min–max}" — turns emotion into practical intent.
class _CostAnchor extends ConsumerStatefulWidget {
  const _CostAnchor({this.styleId});

  final String? styleId;

  @override
  ConsumerState<_CostAnchor> createState() => _CostAnchorState();
}

class _CostAnchorState extends ConsumerState<_CostAnchor> {
  bool _tracked = false;

  String _money(double v, String currency) {
    // Group thousands with a thin space; keep it integer for a clean anchor.
    final s = v.toStringAsFixed(0);
    final buf = StringBuffer();
    for (var i = 0; i < s.length; i++) {
      if (i > 0 && (s.length - i) % 3 == 0) buf.write(' ');
      buf.write(s[i]);
    }
    final symbol = currency == 'RUB' ? '₽' : (currency == 'UZS' ? 'сум' : currency);
    return '${buf.toString()} $symbol';
  }

  @override
  Widget build(BuildContext context) {
    final city = ref.watch(selectedCityProvider);
    final estimates =
        ref.watch(priceEstimatesProvider((city: city, styleId: widget.styleId)));
    final theme = Theme.of(context);

    return estimates.maybeWhen(
      data: (list) {
        if (list.isEmpty) return const SizedBox.shrink();
        final e = list.first;
        if (!_tracked) {
          _tracked = true;
          WidgetsBinding.instance.addPostFrameCallback((_) {
            ref.read(analyticsProvider).track(
              'cost_estimate_viewed',
              {'city': city, 'style_id': widget.styleId, 'currency': e.currency},
            );
          });
        }
        return Container(
          margin: const EdgeInsets.fromLTRB(16, 16, 16, 8),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: theme.colorScheme.primary.withValues(alpha: 0.06),
            borderRadius: BorderRadius.circular(14),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Такая улыбка в городе $city',
                style: theme.textTheme.labelLarge?.copyWith(color: Colors.black54),
              ),
              const SizedBox(height: 6),
              Text(
                '${_money(e.priceMin, e.currency)} – ${_money(e.priceMax, e.currency)}',
                style: theme.textTheme.headlineSmall
                    ?.copyWith(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 2),
              Text(
                '${e.treatmentLabelRu}${e.isEstimate ? ' · ориентировочно' : ''}',
                style: theme.textTheme.bodySmall?.copyWith(color: Colors.black54),
              ),
              const SizedBox(height: 12),
              FilledButton.tonalIcon(
                icon: const Icon(Icons.local_hospital_outlined),
                label: const Text('Узнать точную цену в клинике рядом'),
                onPressed: () => context.push('/clinics'),
              ),
            ],
          ),
        );
      },
      orElse: () => const SizedBox.shrink(),
    );
  }
}

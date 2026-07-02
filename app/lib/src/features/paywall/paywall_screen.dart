import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../api/models.dart';
import '../../providers/entitlements.dart';
import '../../providers/providers.dart';

/// Action-locked paywall (v1.1). Multi-page: value proposition → plans.
/// Reached only on an explicit action (2nd generation, remove watermark, save) —
/// never on a timer (CLAUDE.md UX rule; benchmark 16.5% vs 2.1%).
class PaywallScreen extends ConsumerStatefulWidget {
  const PaywallScreen({super.key});

  @override
  ConsumerState<PaywallScreen> createState() => _PaywallScreenState();
}

class _PaywallScreenState extends ConsumerState<PaywallScreen> {
  final _controller = PageController();
  int _page = 0;
  bool _purchasing = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _purchase(PackOption pack) async {
    setState(() => _purchasing = true);
    try {
      final api = ref.read(apiClientProvider);
      // In mock mode the server auto-succeeds and activates the pack; we mirror the
      // credit grant locally so the UI unlocks immediately.
      await api.purchase(packType: pack.packType, provider: 'yookassa');
      ref.read(entitlementsProvider.notifier).grantPack(pack.generationsTotal);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Пакет «${pack.title}» активирован')),
      );
      context.pop();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('Не удалось купить: $e')));
    } finally {
      if (mounted) setState(() => _purchasing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Больше улыбок')),
      body: PageView(
        controller: _controller,
        onPageChanged: (i) => setState(() => _page = i),
        children: [
          _ValuePage(onContinue: () {
            _controller.animateToPage(
              1,
              duration: const Duration(milliseconds: 300),
              curve: Curves.easeOut,
            );
          }),
          _PlansPage(purchasing: _purchasing, onBuy: _purchase),
        ],
      ),
      bottomNavigationBar: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: List.generate(
            2,
            (i) => AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              margin: const EdgeInsets.symmetric(horizontal: 4),
              width: i == _page ? 20 : 8,
              height: 8,
              decoration: BoxDecoration(
                color: i == _page ? Colors.black87 : Colors.black26,
                borderRadius: BorderRadius.circular(4),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _ValuePage extends StatelessWidget {
  const _ValuePage({required this.onContinue});

  final VoidCallback onContinue;

  static const _benefits = <(IconData, String)>[
    (Icons.hd_outlined, 'Без водяного знака — сохраняй и делись'),
    (Icons.style_outlined, 'Все стили: виниры, голливудская улыбка'),
    (Icons.bolt_outlined, 'Больше генераций — примерь разные варианты'),
    (Icons.favorite_border, 'Покажи будущую улыбку друзьям'),
  ];

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Spacer(),
          Text('Твоя улыбка заслуживает большего',
              style: theme.textTheme.headlineSmall
                  ?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 20),
          for (final (icon, text) in _benefits)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Row(
                children: [
                  Icon(icon, color: theme.colorScheme.primary),
                  const SizedBox(width: 12),
                  Expanded(child: Text(text, style: theme.textTheme.bodyLarge)),
                ],
              ),
            ),
          const Spacer(),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: onContinue,
              child: const Text('Выбрать пакет'),
            ),
          ),
        ],
      ),
    );
  }
}

class _PlansPage extends ConsumerWidget {
  const _PlansPage({required this.purchasing, required this.onBuy});

  final bool purchasing;
  final void Function(PackOption) onBuy;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final packs = ref.watch(packsProvider);
    return packs.when(
      data: (items) => ListView(
        padding: const EdgeInsets.all(16),
        children: [
          for (final p in items)
            Card(
              child: ListTile(
                title: Text(p.title),
                subtitle: Text('${p.generationsTotal} генераций'),
                trailing: Text(
                  '${p.priceAmount.toStringAsFixed(0)} ${p.priceCurrency}',
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                onTap: purchasing ? null : () => onBuy(p),
              ),
            ),
          if (purchasing)
            const Padding(
              padding: EdgeInsets.all(16),
              child: Center(child: CircularProgressIndicator()),
            ),
        ],
      ),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('Не удалось загрузить пакеты\n$e')),
    );
  }
}

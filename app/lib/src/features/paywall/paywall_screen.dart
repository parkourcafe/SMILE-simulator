import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:uuid/uuid.dart';

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

class _PaywallScreenState extends ConsumerState<PaywallScreen>
    with WidgetsBindingObserver {
  final _controller = PageController();
  final _idempotencyKeys = <String, String>{};
  int _page = 0;
  bool _purchasing = false;
  bool _checkingPayment = false;
  String? _pendingPaymentId;
  String? _pendingPackType;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _controller.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && _pendingPaymentId != null) {
      _checkPayment();
    }
  }

  Future<bool> _refreshEntitlementsAndClose() async {
    ref.invalidate(entitlementsSyncProvider);
    try {
      await ref.read(entitlementsSyncProvider.future);
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Оплата подтверждена, но баланс пока не обновился. Проверьте ещё раз.',
            ),
          ),
        );
      }
      return false;
    }
    if (!mounted) return false;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Оплата подтверждена. Пакет активирован.')),
    );
    context.pop();
    return true;
  }

  Future<void> _checkPayment() async {
    final paymentId = _pendingPaymentId;
    if (paymentId == null || _checkingPayment) return;
    setState(() => _checkingPayment = true);
    try {
      final status = await ref.read(apiClientProvider).paymentStatus(paymentId);
      if (status.isCompleted) {
        final refreshed = await _refreshEntitlementsAndClose();
        if (refreshed) {
          _pendingPaymentId = null;
          _pendingPackType = null;
        }
      } else if (status.isFailed) {
        if (_pendingPackType != null) _idempotencyKeys.remove(_pendingPackType);
        _pendingPaymentId = null;
        _pendingPackType = null;
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Платёж не прошёл. Попробуйте снова.')),
          );
        }
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Не удалось проверить платёж.')),
        );
      }
    } finally {
      if (mounted) setState(() => _checkingPayment = false);
    }
  }

  Future<void> _purchase(PackOption pack) async {
    setState(() => _purchasing = true);
    try {
      final api = ref.read(apiClientProvider);
      final key = _idempotencyKeys.putIfAbsent(
        pack.packType,
        () => const Uuid().v4(),
      );
      final receipt = await api.purchase(
        packType: pack.packType,
        provider: 'yookassa',
        idempotencyKey: key,
      );
      if (receipt.isCompleted) {
        await _refreshEntitlementsAndClose();
        return;
      }
      if (receipt.isFailed || receipt.paymentUrl == null) {
        _idempotencyKeys.remove(pack.packType);
        throw StateError('payment_not_available');
      }
      final opened = await launchUrl(
        Uri.parse(receipt.paymentUrl!),
        mode: LaunchMode.externalApplication,
      );
      if (!opened) throw StateError('payment_url_not_opened');
      _pendingPaymentId = receipt.paymentId;
      _pendingPackType = pack.packType;
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Завершите оплату в открывшемся окне, затем вернитесь.'),
          ),
        );
      }
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Не удалось начать оплату. Повторите позже.')),
      );
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
          _PlansPage(
            purchasing: _purchasing,
            checkingPayment: _checkingPayment,
            hasPendingPayment: _pendingPaymentId != null,
            onBuy: _purchase,
            onCheckPayment: _checkPayment,
          ),
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
  const _PlansPage({
    required this.purchasing,
    required this.checkingPayment,
    required this.hasPendingPayment,
    required this.onBuy,
    required this.onCheckPayment,
  });

  final bool purchasing;
  final bool checkingPayment;
  final bool hasPendingPayment;
  final void Function(PackOption) onBuy;
  final VoidCallback onCheckPayment;

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
                onTap: (purchasing || hasPendingPayment) ? null : () => onBuy(p),
              ),
            ),
          if (purchasing)
            const Padding(
              padding: EdgeInsets.all(16),
              child: Center(child: CircularProgressIndicator()),
            ),
          if (hasPendingPayment)
            TextButton.icon(
              onPressed: checkingPayment ? null : onCheckPayment,
              icon: checkingPayment
                  ? const SizedBox.square(
                      dimension: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.refresh),
              label: const Text('Проверить оплату'),
            ),
        ],
      ),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (_, __) => const Center(child: Text('Не удалось загрузить пакеты')),
    );
  }
}

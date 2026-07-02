import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../providers/generation_flow.dart';

/// Generation theater (v1.1): the 5–15s wait is a selling moment, not a spinner.
///
/// Staged messages ("Анализируем улыбку → Подбираем форму → Выравниваем тон")
/// plus a social-proof line keep the user engaged and raise perceived value while
/// the server pipeline runs. When the generation finishes we route to the result.
class GeneratingScreen extends ConsumerStatefulWidget {
  const GeneratingScreen({super.key});

  @override
  ConsumerState<GeneratingScreen> createState() => _GeneratingScreenState();
}

class _GeneratingScreenState extends ConsumerState<GeneratingScreen> {
  // Staged "theater" copy (RU primary, per CLAUDE.md UX rules).
  static const _stages = <String>[
    'Анализируем вашу улыбку…',
    'Определяем форму губ и зубов…',
    'Подбираем идеальную форму…',
    'Выравниваем оттенок и блики…',
    'Финальная отрисовка…',
  ];

  Timer? _stageTimer;
  int _stage = 0;

  @override
  void initState() {
    super.initState();
    _stageTimer = Timer.periodic(const Duration(milliseconds: 2200), (_) {
      if (!mounted) return;
      setState(() => _stage = (_stage + 1) % _stages.length);
    });
    WidgetsBinding.instance.addPostFrameCallback((_) => _start());
  }

  @override
  void dispose() {
    _stageTimer?.cancel();
    super.dispose();
  }

  Future<void> _start() async {
    final id = await ref.read(generationFlowProvider.notifier).run();
    if (!mounted) return;
    if (id != null && ref.read(generationFlowProvider).error == null) {
      context.go('/result/$id');
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(generationFlowProvider);
    final theme = Theme.of(context);

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: state.error != null
                ? _ErrorView(message: state.error!)
                : Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const SizedBox(
                        width: 72,
                        height: 72,
                        child: CircularProgressIndicator(strokeWidth: 5),
                      ),
                      const SizedBox(height: 32),
                      AnimatedSwitcher(
                        duration: const Duration(milliseconds: 400),
                        child: Text(
                          _stages[_stage],
                          key: ValueKey(_stage),
                          textAlign: TextAlign.center,
                          style: theme.textTheme.titleMedium,
                        ),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        'Обычно занимает 5–15 секунд',
                        style: theme.textTheme.bodySmall
                            ?.copyWith(color: Colors.black54),
                      ),
                      const SizedBox(height: 40),
                      _SocialProof(theme: theme),
                    ],
                  ),
          ),
        ),
      ),
    );
  }
}

class _SocialProof extends StatelessWidget {
  const _SocialProof({required this.theme});

  final ThemeData theme;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: theme.colorScheme.primary.withOpacity(0.08),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.people_alt_outlined, size: 18),
          const SizedBox(width: 8),
          Flexible(
            child: Text(
              'Более 12 000 улыбок уже создано',
              style: theme.textTheme.bodySmall,
            ),
          ),
        ],
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const Icon(Icons.error_outline, size: 48, color: Colors.redAccent),
        const SizedBox(height: 16),
        Text(message, textAlign: TextAlign.center),
        const SizedBox(height: 8),
        const Text(
          'Попробуйте другое фото — анфас, хорошее освещение.',
          style: TextStyle(color: Colors.black54),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 24),
        Builder(
          builder: (context) => FilledButton(
            onPressed: () => GoRouter.of(context).go('/home'),
            child: const Text('На главную'),
          ),
        ),
      ],
    );
  }
}

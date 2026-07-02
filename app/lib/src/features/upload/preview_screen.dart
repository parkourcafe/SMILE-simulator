import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../providers/generation_flow.dart';
import '../../providers/providers.dart';
import '../../services/analytics.dart';
import 'precheck.dart';

/// Preview + live photo pre-check (v1.1). Runs the advisory on-device checks on
/// the captured/selected image and gates "Continue" until they pass. Real MediaPipe
/// detection is pluggable via [faceProbeProvider]; server validation stays
/// authoritative during generation.
class PreviewScreen extends ConsumerStatefulWidget {
  const PreviewScreen({super.key});

  @override
  ConsumerState<PreviewScreen> createState() => _PreviewScreenState();
}

class _PreviewScreenState extends ConsumerState<PreviewScreen> {
  PreCheckResult? _result;
  bool _checking = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _runCheck());
  }

  Future<void> _runCheck() async {
    final photo = ref.read(generationFlowProvider).photo;
    if (photo == null) {
      setState(() => _checking = false);
      return;
    }
    final probe = ref.read(faceProbeProvider);
    final result = await probe.evaluate(photo);
    if (!mounted) return;
    if (!result.passed) {
      ref.read(analyticsProvider).track(
        'precheck_blocked',
        {'reasons': result.blockingReasons},
      );
    }
    setState(() {
      _result = result;
      _checking = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final photo = ref.watch(generationFlowProvider).photo;
    final result = _result;
    final canContinue = result?.passed ?? false;

    return Scaffold(
      appBar: AppBar(title: const Text('Проверка фото')),
      body: photo == null
          ? const Center(child: Text('Фото не выбрано'))
          : Column(
              children: [
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(16),
                      child: Image.file(File(photo.path), fit: BoxFit.cover),
                    ),
                  ),
                ),
                if (_checking)
                  const Padding(
                    padding: EdgeInsets.all(12),
                    child: LinearProgressIndicator(),
                  )
                else if (result != null)
                  _CheckList(result: result),
                Padding(
                  padding: const EdgeInsets.all(20),
                  child: Row(
                    children: [
                      Expanded(
                        child: OutlinedButton(
                          onPressed: () => context.go('/upload'),
                          child: const Text('Переснять'),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: FilledButton(
                          onPressed:
                              canContinue ? () => context.push('/styles') : null,
                          child: const Text('Продолжить'),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
    );
  }
}

class _CheckList extends StatelessWidget {
  const _CheckList({required this.result});

  final PreCheckResult result;

  static const _labelsRu = {
    PreCheckId.face: 'Лицо анфас',
    PreCheckId.mouth: 'Видно зубы',
    PreCheckId.light: 'Освещение',
    PreCheckId.sharpness: 'Резкость',
    PreCheckId.distance: 'Расстояние',
  };

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        children: [
          for (final item in result.items)
            Row(
              children: [
                Icon(
                  item.ok ? Icons.check_circle : Icons.error_outline,
                  size: 18,
                  color: item.ok ? Colors.green : Colors.orange,
                ),
                const SizedBox(width: 8),
                Text(_labelsRu[item.id] ?? item.id.name),
                const Spacer(),
                if (!item.ok)
                  Flexible(
                    child: Text(
                      item.hintRu,
                      textAlign: TextAlign.right,
                      style: const TextStyle(color: Colors.orange, fontSize: 12),
                    ),
                  ),
              ],
            ),
        ],
      ),
    );
  }
}

import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../providers/generation_flow.dart';
import '../../providers/providers.dart';
import '../../services/analytics.dart';
import 'precheck.dart';

const photoConsentVersion = 'photo-beta-2026-07-10';
final _privacyUri = Uri.parse('https://www.zubilook.com/privacy.html?lang=ru');
final _termsUri = Uri.parse('https://www.zubilook.com/terms.html?lang=ru');

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
  bool _consentGiven = false;
  bool _recordingConsent = false;
  String? _consentError;

  @override
  void initState() {
    super.initState();
    _consentGiven = ref.read(generationFlowProvider).photoConsent != null;
    WidgetsBinding.instance.addPostFrameCallback((_) => _runCheck());
  }

  Future<void> _openDocument(Uri uri) async {
    var opened = false;
    try {
      opened = await launchUrl(uri, mode: LaunchMode.externalApplication);
    } catch (_) {
      opened = false;
    }
    if (!opened && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Не удалось открыть документ')),
      );
    }
  }

  Future<void> _continue() async {
    if (!_consentGiven || _recordingConsent) return;
    setState(() {
      _recordingConsent = true;
      _consentError = null;
    });
    try {
      final notifier = ref.read(generationFlowProvider.notifier);
      final existing = ref.read(generationFlowProvider).photoConsent;
      if (existing?.consentVersion != photoConsentVersion) {
        await notifier.recordPhotoConsent(
          consentVersion: photoConsentVersion,
          consentLocale: 'ru',
        );
      }
      if (mounted) context.push('/styles');
    } catch (_) {
      if (mounted) {
        setState(() {
          _consentError = 'Не удалось зафиксировать согласие. Фото не загружено.';
        });
      }
    } finally {
      if (mounted) setState(() => _recordingConsent = false);
    }
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
    final canContinue =
        (result?.passed ?? false) && _consentGiven && !_recordingConsent;

    return Scaffold(
      appBar: AppBar(title: const Text('Проверка фото')),
      body: photo == null
          ? const Center(child: Text('Фото не выбрано'))
          : SafeArea(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 20),
                children: [
                  AspectRatio(
                    aspectRatio: 4 / 5,
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(8),
                      child: ColoredBox(
                        color: Colors.black,
                        child: Image.file(File(photo.path), fit: BoxFit.contain),
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  if (_checking)
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: 12),
                      child: LinearProgressIndicator(),
                    )
                  else if (result != null)
                    _CheckList(result: result),
                  const SizedBox(height: 12),
                  DecoratedBox(
                    decoration: BoxDecoration(
                      border: Border.all(
                        color: Theme.of(context).colorScheme.outlineVariant,
                      ),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(4, 8, 10, 8),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Checkbox(
                            value: _consentGiven,
                            onChanged: _recordingConsent
                                ? null
                                : (value) {
                                    final accepted = value ?? false;
                                    setState(() {
                                      _consentGiven = accepted;
                                      _consentError = null;
                                    });
                                    if (!accepted) {
                                      ref
                                          .read(generationFlowProvider.notifier)
                                          .clearPhotoConsent();
                                    }
                                  },
                          ),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text(
                                  'Я разрешаю загрузить и обработать это фото для создания AI-визуализации улыбки, включая хранение в Supabase и обработку через Fal.ai. Это не медицинская рекомендация.',
                                ),
                                Wrap(
                                  spacing: 4,
                                  children: [
                                    TextButton(
                                      onPressed: () => _openDocument(_privacyUri),
                                      child: const Text('Политика'),
                                    ),
                                    TextButton(
                                      onPressed: () => _openDocument(_termsUri),
                                      child: const Text('Соглашение'),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  if (_consentError != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: Text(
                        _consentError!,
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.error,
                        ),
                      ),
                    ),
                  const SizedBox(height: 20),
                  Row(
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
                          onPressed: canContinue ? _continue : null,
                          child: _recordingConsent
                              ? const SizedBox.square(
                                  dimension: 20,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Text('Продолжить'),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
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

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:uuid/uuid.dart';

import '../../features/auth/auth_service.dart';
import '../../providers/providers.dart';

const leadConsentVersion = 'lead-beta-2026-07-10';
final _privacyUri = Uri.parse('https://www.zubilook.com/privacy.html?lang=ru');

/// Creates one idempotent clinic lead for the selected completed generation.
class LeadFormScreen extends ConsumerStatefulWidget {
  const LeadFormScreen({
    super.key,
    required this.clinicId,
    required this.generationId,
  });

  final String clinicId;
  final String generationId;

  @override
  ConsumerState<LeadFormScreen> createState() => _LeadFormScreenState();
}

class _LeadFormScreenState extends ConsumerState<LeadFormScreen> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _phone = TextEditingController();
  final _idempotencyKey = const Uuid().v4();
  String? _preferredTime;
  String? _errorMessage;
  bool _consentGiven = false;
  bool _submitting = false;

  @override
  void initState() {
    super.initState();
    _phone.text = ref.read(authServiceProvider).phone ?? '';
  }

  @override
  void dispose() {
    _name.dispose();
    _phone.dispose();
    super.dispose();
  }

  String? _validateName(String? value) {
    final name = (value ?? '').trim();
    if (name.isEmpty) return 'Введите имя';
    if (name.length > 120) return 'Не более 120 символов';
    return null;
  }

  Future<void> _openPrivacyPolicy() async {
    var opened = false;
    try {
      opened = await launchUrl(_privacyUri, mode: LaunchMode.externalApplication);
    } catch (_) {
      opened = false;
    }
    if (!opened && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Не удалось открыть политику конфиденциальности')),
      );
    }
  }

  Future<void> _submit() async {
    FocusScope.of(context).unfocus();
    final valid = _formKey.currentState?.validate() ?? false;
    if (!valid || !_consentGiven || widget.generationId.isEmpty) {
      setState(() {
        _errorMessage = widget.generationId.isEmpty
            ? 'Не выбрана визуализация.'
            : (!_consentGiven ? 'Нужно подтвердить согласие на передачу данных.' : null);
      });
      return;
    }

    setState(() {
      _submitting = true;
      _errorMessage = null;
    });
    try {
      await ref.read(apiClientProvider).submitLead(
            clinicId: widget.clinicId,
            generationId: widget.generationId,
            name: _name.text.trim(),
            phone: normalizePhone(_phone.text),
            preferredTime: _preferredTime,
            consentGiven: true,
            consentVersion: leadConsentVersion,
            consentLocale: 'ru',
            idempotencyKey: _idempotencyKey,
          );
      if (mounted) context.go('/lead/sent');
    } on DioException catch (error) {
      if (mounted) {
        setState(() => _errorMessage = _messageFor(error.response?.statusCode));
      }
    } catch (_) {
      if (mounted) {
        setState(() => _errorMessage = 'Не удалось отправить заявку. Повторите позже.');
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  String _messageFor(int? statusCode) {
    return switch (statusCode) {
      404 => 'Клиника или визуализация больше недоступна.',
      409 => 'Эта визуализация уже отправлена или ещё не готова.',
      401 => 'Сессия завершилась. Войдите снова.',
      _ => 'Не удалось отправить заявку. Повторите позже.',
    };
  }

  @override
  Widget build(BuildContext context) {
    final unavailable = widget.generationId.isEmpty;

    return Scaffold(
      appBar: AppBar(title: const Text('Заявка в клинику')),
      body: SafeArea(
        child: Form(
          key: _formKey,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
            children: [
              Text(
                'Контактные данные',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 6),
              const Text('Клиника использует их только для связи по консультации.'),
              const SizedBox(height: 20),
              TextFormField(
                controller: _name,
                textInputAction: TextInputAction.next,
                autofillHints: const [AutofillHints.name],
                decoration: const InputDecoration(labelText: 'Имя'),
                validator: _validateName,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _phone,
                keyboardType: TextInputType.phone,
                textInputAction: TextInputAction.next,
                autofillHints: const [AutofillHints.telephoneNumber],
                decoration: const InputDecoration(
                  labelText: 'Телефон',
                  hintText: '+7 999 123-45-67',
                ),
                validator: validateInternationalPhone,
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                initialValue: _preferredTime,
                decoration: const InputDecoration(labelText: 'Удобное время'),
                items: const [
                  DropdownMenuItem(value: 'morning', child: Text('Утро')),
                  DropdownMenuItem(value: 'afternoon', child: Text('День')),
                  DropdownMenuItem(value: 'evening', child: Text('Вечер')),
                ],
                onChanged: (value) => setState(() => _preferredTime = value),
              ),
              const SizedBox(height: 20),
              DecoratedBox(
                decoration: BoxDecoration(
                  border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(6, 10, 12, 10),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Checkbox(
                        value: _consentGiven,
                        onChanged: _submitting
                            ? null
                            : (value) => setState(() => _consentGiven = value ?? false),
                      ),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'Я согласен(на) передать выбранной клинике имя, телефон, исходное фото и AI-визуализацию для связи по вопросу консультации.',
                            ),
                            TextButton.icon(
                              onPressed: _openPrivacyPolicy,
                              icon: const Icon(Icons.open_in_new, size: 18),
                              label: const Text('Политика конфиденциальности'),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              if (_errorMessage != null) ...[
                const SizedBox(height: 12),
                Text(
                  _errorMessage!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ],
              const SizedBox(height: 20),
              FilledButton.icon(
                onPressed: (_submitting || unavailable) ? null : _submit,
                icon: _submitting
                    ? const SizedBox.square(
                        dimension: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.send_outlined),
                label: Text(_submitting ? 'Отправляем…' : 'Отправить заявку'),
              ),
              if (unavailable) ...[
                const SizedBox(height: 12),
                OutlinedButton(
                  onPressed: () => context.go('/history'),
                  child: const Text('Выбрать визуализацию'),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

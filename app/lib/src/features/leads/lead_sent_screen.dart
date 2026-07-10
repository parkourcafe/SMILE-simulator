import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// Confirmation shown only after the backend accepts the lead.
class LeadSentScreen extends StatelessWidget {
  const LeadSentScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Заявка принята')),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.check_circle_outline,
                size: 56,
                color: Theme.of(context).colorScheme.primary,
              ),
              const SizedBox(height: 16),
              Text(
                'Заявка принята',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 8),
              const Text(
                'Мы сохранили заявку и передадим её выбранной клинике. Время ответа зависит от клиники.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              FilledButton(
                onPressed: () => context.go('/home'),
                child: const Text('Готово'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

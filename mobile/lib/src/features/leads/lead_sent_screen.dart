import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// Request sent
class LeadSentScreen extends StatelessWidget {
  const LeadSentScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Request sent')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text('Request sent'),
            const SizedBox(height: 16),
            const Text('Clinic will contact you within 24 hours.'),
            const SizedBox(height: 16),
            FilledButton(onPressed: () => context.go('/home'), child: const Text('Done')),
          ],
        ),
      ),
    );
  }
}

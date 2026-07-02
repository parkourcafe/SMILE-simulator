import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// Find a clinic
class ClinicsScreen extends StatelessWidget {
  const ClinicsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Find a clinic')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text('Find a clinic'),
            const SizedBox(height: 16),
            FilledButton(onPressed: () => context.go('/lead/demo'), child: const Text('Book consultation')),
          ],
        ),
      ),
    );
  }
}

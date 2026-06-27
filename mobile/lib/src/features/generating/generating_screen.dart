import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// Generating…
class GeneratingScreen extends StatelessWidget {
  const GeneratingScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Generating…')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text('Generating…'),
            const SizedBox(height: 16),
            const CircularProgressIndicator(),
            const SizedBox(height: 16),
            FilledButton(onPressed: () => context.go('/result/demo'), child: const Text('See result (demo)')),
          ],
        ),
      ),
    );
  }
}

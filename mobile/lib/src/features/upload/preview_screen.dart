import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// Preview
class PreviewScreen extends StatelessWidget {
  const PreviewScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Preview')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text('Preview'),
            const SizedBox(height: 16),
            FilledButton(onPressed: () => context.go('/styles'), child: const Text('Continue')),
          ],
        ),
      ),
    );
  }
}

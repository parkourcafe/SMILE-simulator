import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// History
class HistoryScreen extends StatelessWidget {
  const HistoryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('History')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text('History'),
            const SizedBox(height: 16),
            FilledButton(onPressed: () => context.go('/home'), child: const Text('Back')),
          ],
        ),
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// Onboarding
class OnboardingScreen extends StatelessWidget {
  const OnboardingScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Onboarding')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text('Onboarding'),
            const SizedBox(height: 16),
            FilledButton(onPressed: () => context.go('/login'), child: const Text('Get started')),
          ],
        ),
      ),
    );
  }
}

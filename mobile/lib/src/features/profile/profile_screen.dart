import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// Profile
class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Profile')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text('Profile'),
            const SizedBox(height: 16),
            FilledButton(onPressed: () => context.go('/home'), child: const Text('Back')),
          ],
        ),
      ),
    );
  }
}

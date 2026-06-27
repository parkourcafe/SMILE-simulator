import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// Login
class LoginScreen extends StatelessWidget {
  const LoginScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Login')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text('Login'),
            const SizedBox(height: 16),
            FilledButton(onPressed: () => context.go('/verify'), child: const Text('Send code')),
          ],
        ),
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// Upload photo
class UploadScreen extends StatelessWidget {
  const UploadScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Upload photo')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text('Upload photo'),
            const SizedBox(height: 16),
            FilledButton(onPressed: () => context.go('/preview'), child: const Text('Continue')),
          ],
        ),
      ),
    );
  }
}

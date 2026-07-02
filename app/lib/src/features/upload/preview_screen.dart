import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../providers/generation_flow.dart';

/// Preview the cropped photo before choosing a style.
/// (Server-side face validation happens during generation — architecture §13.)
class PreviewScreen extends ConsumerWidget {
  const PreviewScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final photo = ref.watch(generationFlowProvider).photo;
    return Scaffold(
      appBar: AppBar(title: const Text('Preview')),
      body: photo == null
          ? const Center(child: Text('No photo selected'))
          : Column(
              children: [
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(16),
                      child: Image.file(File(photo.path), fit: BoxFit.cover),
                    ),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.all(20),
                  child: Row(
                    children: [
                      Expanded(
                        child: OutlinedButton(
                          onPressed: () => context.go('/upload'),
                          child: const Text('Retake'),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: FilledButton(
                          onPressed: () => context.push('/styles'),
                          child: const Text('Continue'),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
    );
  }
}

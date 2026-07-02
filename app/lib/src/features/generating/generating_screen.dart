import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../providers/generation_flow.dart';

/// Kicks off upload + generation, shows a loading state, and routes to the result.
/// (~5–15s; CLAUDE.md.)
class GeneratingScreen extends ConsumerStatefulWidget {
  const GeneratingScreen({super.key});

  @override
  ConsumerState<GeneratingScreen> createState() => _GeneratingScreenState();
}

class _GeneratingScreenState extends ConsumerState<GeneratingScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _start());
  }

  Future<void> _start() async {
    final id = await ref.read(generationFlowProvider.notifier).run();
    if (!mounted) return;
    if (id != null && ref.read(generationFlowProvider).error == null) {
      context.go('/result/$id');
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(generationFlowProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Creating your smile…')),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              if (state.error != null) ...[
                const Icon(Icons.error_outline, size: 48, color: Colors.redAccent),
                const SizedBox(height: 16),
                Text(state.error!, textAlign: TextAlign.center),
                const SizedBox(height: 24),
                FilledButton(
                  onPressed: () => context.go('/home'),
                  child: const Text('Back home'),
                ),
              ] else ...[
                const CircularProgressIndicator(),
                const SizedBox(height: 24),
                Text('Status: ${state.generation?.status.name ?? 'starting'}'),
                const SizedBox(height: 8),
                const Text(
                  'This usually takes 5–15 seconds.',
                  style: TextStyle(color: Colors.black54),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

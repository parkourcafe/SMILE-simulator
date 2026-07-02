import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../../providers/generation_flow.dart';

/// Upload: camera or gallery, with the photo guidelines hint (CLAUDE.md UX rule).
class UploadScreen extends ConsumerWidget {
  const UploadScreen({super.key});

  Future<void> _pick(BuildContext context, WidgetRef ref, ImageSource source) async {
    final picker = ImagePicker();
    final file = await picker.pickImage(source: source, maxWidth: 2048, imageQuality: 92);
    if (file == null) return;
    ref.read(generationFlowProvider.notifier).setPhoto(file);
    if (context.mounted) context.push('/preview');
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(title: const Text('Загрузите селфи')),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Card(
              child: Padding(
                padding: EdgeInsets.all(16),
                child: Text(
                  'Анфас к камере. Слегка приоткройте рот. Хорошее освещение.',
                  textAlign: TextAlign.center,
                ),
              ),
            ),
            const SizedBox(height: 32),
            FilledButton.icon(
              icon: const Icon(Icons.camera_alt_outlined),
              label: const Text('Сделать фото'),
              onPressed: () => _pick(context, ref, ImageSource.camera),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              icon: const Icon(Icons.photo_library_outlined),
              label: const Text('Выбрать из галереи'),
              onPressed: () => _pick(context, ref, ImageSource.gallery),
            ),
          ],
        ),
      ),
    );
  }
}

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../api/models.dart';
import 'entitlements.dart';
import 'providers.dart';

/// Holds the in-progress generation flow: picked photo → style → result.
class GenerationFlowState {
  const GenerationFlowState({
    this.photo,
    this.style,
    this.generation,
    this.busy = false,
    this.error,
  });

  final XFile? photo;
  final Style? style;
  final Generation? generation;
  final bool busy;
  final String? error;

  GenerationFlowState copyWith({
    XFile? photo,
    Style? style,
    Generation? generation,
    bool? busy,
    String? error,
    bool clearError = false,
  }) {
    return GenerationFlowState(
      photo: photo ?? this.photo,
      style: style ?? this.style,
      generation: generation ?? this.generation,
      busy: busy ?? this.busy,
      error: clearError ? null : (error ?? this.error),
    );
  }
}

class GenerationFlow extends StateNotifier<GenerationFlowState> {
  GenerationFlow(this._ref) : super(const GenerationFlowState());

  final Ref _ref;

  void setPhoto(XFile photo) =>
      state = state.copyWith(photo: photo, clearError: true);

  void setStyle(Style style) => state = state.copyWith(style: style);

  void reset() => state = const GenerationFlowState();

  /// Upload the selfie to private Storage, start generation, and poll to completion.
  /// Returns the generation id, or null on error.
  Future<String?> run() async {
    final photo = state.photo;
    final style = state.style;
    if (photo == null || style == null) {
      state = state.copyWith(error: 'Pick a photo and a style first.');
      return null;
    }

    state = state.copyWith(busy: true, clearError: true);
    try {
      final api = _ref.read(apiClientProvider);
      final path = await _uploadPhoto(photo);
      var gen = await api.startGeneration(styleId: style.id, originalPhotoPath: path);

      // Poll until terminal (architecture §4.2).
      await for (final g in api.pollGeneration(gen.id)) {
        gen = g;
        state = state.copyWith(generation: g);
        if (g.isTerminal) break;
      }

      state = state.copyWith(busy: false, generation: gen);
      if (gen.status == GenerationStatus.failed) {
        state = state.copyWith(error: gen.errorMessage ?? 'Generation failed.');
      } else if (gen.status == GenerationStatus.completed) {
        // A successful generation spends one credit (free tier first). This is what
        // makes the NEXT attempt action-lock into the paywall.
        _ref.read(entitlementsProvider.notifier).consumeOne();
      }
      return gen.id;
    } catch (e) {
      state = state.copyWith(busy: false, error: e.toString());
      return null;
    }
  }

  Future<String> _uploadPhoto(XFile photo) async {
    final client = Supabase.instance.client;
    final userId = client.auth.currentUser?.id ?? 'anon';
    final bytes = await photo.readAsBytes();
    final path = '$userId/${DateTime.now().millisecondsSinceEpoch}_original.png';
    await client.storage.from('photos').uploadBinary(
          path,
          bytes,
          fileOptions: const FileOptions(contentType: 'image/png', upsert: true),
        );
    return path;
  }
}

final generationFlowProvider =
    StateNotifierProvider<GenerationFlow, GenerationFlowState>(
  (ref) => GenerationFlow(ref),
);

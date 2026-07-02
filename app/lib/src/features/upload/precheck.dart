import 'package:image_picker/image_picker.dart';

/// Live photo pre-check (v1.1). On-device, ADVISORY — the server stays the
/// authoritative validator (CLAUDE.md ML Pipeline / Architecture v1.1).
///
/// The five checks and their RU hints mirror the CLAUDE.md table exactly. The
/// shutter / "continue" button is gated until every check passes; each failing
/// check fires `precheck_blocked(reason)`.
///
/// Detection backend is pluggable via [FaceProbe]. The default
/// [AdvisoryFaceProbe] passes (so the mock journey is never blocked); wiring a
/// real detector (google_mlkit_face_detection over a `camera` preview stream, or
/// a MediaPipe Flutter plugin) is the remaining native-integration step — a
/// heavy-dependency decision, tracked in BLOCKERS.md.
enum PreCheckId { face, mouth, light, sharpness, distance }

class PreCheckItem {
  const PreCheckItem({required this.id, required this.ok, required this.hintRu});

  final PreCheckId id;
  final bool ok;
  final String hintRu;
}

class PreCheckResult {
  const PreCheckResult(this.items);

  final List<PreCheckItem> items;

  bool get passed => items.every((i) => i.ok);

  /// Reasons (check ids) that are currently blocking, for `precheck_blocked`.
  List<String> get blockingReasons =>
      items.where((i) => !i.ok).map((i) => i.id.name).toList();

  /// The first RU hint to surface to the user (highest-priority failing check).
  String? get primaryHintRu {
    for (final i in items) {
      if (!i.ok) return i.hintRu;
    }
    return null;
  }
}

/// RU hints per check (CLAUDE.md ML Pipeline → Live Pre-Check table).
const Map<PreCheckId, String> preCheckHintsRu = {
  PreCheckId.face: 'Повернитесь к камере анфас',
  PreCheckId.mouth: 'Улыбнитесь, покажите зубы',
  PreCheckId.light: 'Нужно больше света',
  PreCheckId.sharpness: 'Держите телефон ровно',
  PreCheckId.distance: 'Подойдите ближе / отойдите',
};

abstract class FaceProbe {
  /// Evaluate a captured/selected image. Real implementations inspect the frame;
  /// the advisory default assumes a valid frame.
  Future<PreCheckResult> evaluate(XFile image);
}

/// Default probe: every check passes. Keeps the mock journey unblocked while the
/// real on-device detector is not yet wired. Replace in DI for production.
class AdvisoryFaceProbe implements FaceProbe {
  const AdvisoryFaceProbe();

  @override
  Future<PreCheckResult> evaluate(XFile image) async {
    return PreCheckResult([
      for (final id in PreCheckId.values)
        PreCheckItem(id: id, ok: true, hintRu: preCheckHintsRu[id]!),
    ]);
  }
}

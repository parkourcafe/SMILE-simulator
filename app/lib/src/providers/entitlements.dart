import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Local entitlement state driving the ACTION-LOCKED paywall (v1.1 UX rule).
///
/// The paywall must fire only on explicit actions — a 2nd generation attempt,
/// watermark removal, or save — never on a timer. Screens read [canGenerate] to
/// decide whether to start a generation or route to `/paywall`.
///
/// Free tier = 1 generation (CLAUDE.md locked decision). This is a client-side
/// mirror for UX gating; the server enforces the real limit (quota service).
class Entitlements {
  const Entitlements({this.freeRemaining = 0, this.packRemaining = 0});

  final int freeRemaining;
  final int packRemaining;

  int get totalRemaining => freeRemaining + packRemaining;
  bool get canGenerate => totalRemaining > 0;

  Entitlements copyWith({int? freeRemaining, int? packRemaining}) => Entitlements(
        freeRemaining: freeRemaining ?? this.freeRemaining,
        packRemaining: packRemaining ?? this.packRemaining,
      );
}

class EntitlementsNotifier extends StateNotifier<Entitlements> {
  EntitlementsNotifier() : super(const Entitlements());

  /// Spend one generation — pack credits first, then the free tier.
  void consumeOne() {
    if (state.packRemaining > 0) {
      state = state.copyWith(packRemaining: state.packRemaining - 1);
    } else if (state.freeRemaining > 0) {
      state = state.copyWith(freeRemaining: state.freeRemaining - 1);
    }
  }

  void replace({required int freeRemaining, required int packRemaining}) {
    state = Entitlements(
      freeRemaining: freeRemaining,
      packRemaining: packRemaining,
    );
  }
}

final entitlementsProvider =
    StateNotifierProvider<EntitlementsNotifier, Entitlements>(
  (ref) => EntitlementsNotifier(),
);

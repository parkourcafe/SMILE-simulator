import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Thin analytics facade (Mixpanel is the locked provider — CLAUDE.md Tech Stack).
///
/// The real Mixpanel SDK is wired behind a token in Phase 5; until then this logs
/// events to the console so the event contract (Architecture §9) can be built and
/// verified. Event names match the spec, including the v1.1 additions:
/// `cost_estimate_viewed`, `branded_result_sent`, `precheck_blocked`.
abstract class Analytics {
  void track(String event, [Map<String, Object?> props]);
}

class ConsoleAnalytics implements Analytics {
  const ConsoleAnalytics();

  @override
  void track(String event, [Map<String, Object?> props = const {}]) {
    // TODO(SELENA): replace with Mixpanel.track once MIXPANEL_TOKEN is provided.
    if (kDebugMode) {
      debugPrint('[analytics] $event ${props.isEmpty ? '' : props}');
    }
  }
}

final analyticsProvider = Provider<Analytics>((ref) => const ConsoleAnalytics());

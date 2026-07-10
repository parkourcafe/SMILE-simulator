import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../api/models.dart';
import '../features/auth/auth_service.dart';
import '../features/upload/precheck.dart';

/// Phone-auth session. Without compile-time Supabase config this uses the explicit
/// local OTP flow; production builds use Supabase sessions.
final authServiceProvider = ChangeNotifierProvider<AuthService>((ref) => AuthService());

/// Phone currently waiting for OTP verification. Kept out of URLs and logs.
final pendingOtpPhoneProvider = StateProvider<String?>((ref) => null);

/// Single API client instance.
final apiClientProvider = Provider<ApiClient>((ref) {
  final auth = ref.watch(authServiceProvider);
  return ApiClient(accessTokenProvider: () => auth.accessToken);
});

/// On-device photo pre-check backend (advisory; server stays authoritative).
final faceProbeProvider = Provider<FaceProbe>((ref) => const AdvisoryFaceProbe());

/// Whether the user is currently signed in.
final isAuthedProvider = Provider<bool>((ref) {
  return ref.watch(authServiceProvider).isSignedIn;
});

/// Available dental styles (loaded for the style selector).
final stylesProvider = FutureProvider<List<Style>>((ref) {
  return ref.watch(apiClientProvider).listStyles();
});

/// User's generation history.
final historyProvider = FutureProvider<List<Generation>>((ref) {
  return ref.watch(apiClientProvider).history();
});

/// Purchasable packs for the paywall.
final packsProvider = FutureProvider<List<PackOption>>((ref) {
  return ref.watch(apiClientProvider).availablePacks();
});

/// User's city, used for the result-screen cost anchor. Defaults to Moscow until
/// we read it from the profile / geolocation.
final selectedCityProvider = StateProvider<String>((ref) => 'Moscow');

/// Cost-estimate ranges for the anchor block, keyed by "city|styleId".
final priceEstimatesProvider =
    FutureProvider.family<List<PriceEstimate>, ({String city, String? styleId})>(
  (ref, key) {
    return ref
        .watch(apiClientProvider)
        .priceEstimates(city: key.city, styleId: key.styleId);
  },
);

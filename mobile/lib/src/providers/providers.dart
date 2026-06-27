import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../api/api_client.dart';
import '../api/models.dart';

/// Single API client instance.
final apiClientProvider = Provider<ApiClient>((ref) => ApiClient());

/// Auth state stream from Supabase (drives router redirects).
final authStateProvider = StreamProvider<AuthState>(
  (ref) => Supabase.instance.client.auth.onAuthStateChange,
);

/// Whether the user is currently signed in.
final isAuthedProvider = Provider<bool>((ref) {
  return Supabase.instance.client.auth.currentSession != null;
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

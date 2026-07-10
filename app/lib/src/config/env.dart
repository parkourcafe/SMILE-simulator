/// Compile-time configuration, injected via `--dart-define`.
///
/// The inference provider key lives ONLY on the server — never here.
class Env {
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000/v1',
  );

  static const String supabaseUrl = String.fromEnvironment('SUPABASE_URL');

  static const String supabasePublishableKey =
      String.fromEnvironment('SUPABASE_PUBLISHABLE_KEY');

  // Temporary compatibility alias for existing local scripts.
  static const String supabaseAnonKey = String.fromEnvironment('SUPABASE_ANON_KEY');

  static String get supabasePublicKey =>
      supabasePublishableKey.isNotEmpty ? supabasePublishableKey : supabaseAnonKey;

  static bool get isConfigured =>
      supabaseUrl.isNotEmpty && supabasePublicKey.isNotEmpty;
}

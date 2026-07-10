import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../config/env.dart';

const mockOtpCode = '000000';
const mockBearerToken = 'mock-dev-token';

String normalizePhone(String value) =>
    value.trim().replaceAll(RegExp(r'[\s().-]'), '');

String? validateInternationalPhone(String? value) {
  final phone = normalizePhone(value ?? '');
  if (!RegExp(r'^\+[1-9]\d{7,14}$').hasMatch(phone)) {
    return 'Введите номер в международном формате';
  }
  return null;
}

String? validateOtpCode(String? value) {
  if (!RegExp(r'^\d{6}$').hasMatch((value ?? '').trim())) {
    return 'Введите 6 цифр';
  }
  return null;
}

String maskPhone(String phone) {
  if (phone.length <= 7) return phone;
  return '${phone.substring(0, phone.length - 7)} ••• ${phone.substring(phone.length - 4)}';
}

/// Supabase phone auth with a deterministic, credential-free local mode.
///
/// Local mode exists only when no public Supabase configuration is compiled into
/// the app. Production builds use Supabase and never accept the local OTP.
class AuthService extends ChangeNotifier {
  AuthService({SupabaseClient? client, bool? mockMode}) {
    _mockMode = mockMode ?? !Env.isConfigured;
    _client = client ?? (_mockMode ? null : Supabase.instance.client);
    if (!_mockMode) {
      if (_client == null) {
        throw StateError('Supabase client is required outside mock mode.');
      }
      _subscription = _client!.auth.onAuthStateChange.listen((_) {
        notifyListeners();
      });
    }
  }

  late final bool _mockMode;
  SupabaseClient? _client;
  StreamSubscription<AuthState>? _subscription;
  String? _mockPhone;
  bool _mockSignedIn = false;

  bool get isMockMode => _mockMode;

  bool get isSignedIn {
    if (_mockMode) return _mockSignedIn;
    final session = _client!.auth.currentSession;
    return session != null && !session.isExpired;
  }

  String? get accessToken {
    if (_mockMode) return _mockSignedIn ? mockBearerToken : null;
    return _client!.auth.currentSession?.accessToken;
  }

  Future<void> requestOtp(String rawPhone) async {
    final phone = normalizePhone(rawPhone);
    if (validateInternationalPhone(phone) != null) {
      throw const FormatException('invalid_phone');
    }
    if (_mockMode) {
      _mockPhone = phone;
      return;
    }
    await _client!.auth.signInWithOtp(phone: phone, shouldCreateUser: true);
  }

  Future<bool> verifyOtp({required String rawPhone, required String token}) async {
    final phone = normalizePhone(rawPhone);
    if (_mockMode) {
      _mockSignedIn = _mockPhone == phone && token.trim() == mockOtpCode;
      notifyListeners();
      return _mockSignedIn;
    }
    final response = await _client!.auth.verifyOTP(
      type: OtpType.sms,
      phone: phone,
      token: token.trim(),
    );
    notifyListeners();
    return response.session != null;
  }

  Future<void> signOut() async {
    if (_mockMode) {
      _mockPhone = null;
      _mockSignedIn = false;
      notifyListeners();
      return;
    }
    await _client!.auth.signOut();
    notifyListeners();
  }

  @override
  void dispose() {
    final subscription = _subscription;
    if (subscription != null) unawaited(subscription.cancel());
    super.dispose();
  }
}

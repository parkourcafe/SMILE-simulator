import 'package:flutter_test/flutter_test.dart';
import 'package:smile_simulator/src/features/auth/auth_service.dart';

void main() {
  group('phone input', () {
    test('normalizes common formatting', () {
      expect(normalizePhone(' +998 (90) 123-45-67 '), '+998901234567');
    });

    test('requires E.164-like international format', () {
      expect(validateInternationalPhone('+79991234567'), isNull);
      expect(validateInternationalPhone('+998901234567'), isNull);
      expect(validateInternationalPhone('89991234567'), isNotNull);
      expect(validateInternationalPhone('+0123'), isNotNull);
      expect(validateInternationalPhone('+7abc'), isNotNull);
    });

    test('requires a six-digit OTP', () {
      expect(validateOtpCode('123456'), isNull);
      expect(validateOtpCode('12345'), isNotNull);
      expect(validateOtpCode('12345a'), isNotNull);
    });
  });

  test('local auth accepts only the requested phone and explicit mock code', () async {
    final service = AuthService(mockMode: true);
    await service.requestOtp('+79991234567');

    expect(
      await service.verifyOtp(rawPhone: '+79991234567', token: '111111'),
      isFalse,
    );
    expect(
      await service.verifyOtp(rawPhone: '+79990000000', token: mockOtpCode),
      isFalse,
    );
    expect(
      await service.verifyOtp(rawPhone: '+79991234567', token: mockOtpCode),
      isTrue,
    );
    expect(service.isSignedIn, isTrue);
    expect(service.accessToken, mockBearerToken);

    await service.signOut();
    expect(service.isSignedIn, isFalse);
    expect(service.accessToken, isNull);
    service.dispose();
  });

  test('local auth rejects malformed phone before creating a challenge', () async {
    final service = AuthService(mockMode: true);
    await expectLater(service.requestOtp('not-a-phone'), throwsFormatException);
    service.dispose();
  });
}

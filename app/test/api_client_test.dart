import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smile_simulator/src/api/api_client.dart';

class _RecordingAdapter implements HttpClientAdapter {
  late RequestOptions request;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    request = options;
    return ResponseBody.fromString(
      jsonEncode({
        'id': '57adb7eb-9b14-4cc8-b977-bc7a39b07553',
        'clinic_id': '4df30f8b-844e-454a-a677-c703a5ad89d2',
        'status': 'notified',
      }),
      201,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  test('submitLead sends consent and a stable idempotency key', () async {
    final adapter = _RecordingAdapter();
    final dio = Dio(BaseOptions(baseUrl: 'https://api.example.test/v1'));
    dio.httpClientAdapter = adapter;
    final client = ApiClient(
      dio: dio,
      accessTokenProvider: () => 'access-token',
    );

    final receipt = await client.submitLead(
      clinicId: '4df30f8b-844e-454a-a677-c703a5ad89d2',
      generationId: '394553b3-9110-44ec-8f2b-6a8bcf3dc778',
      name: 'Selena',
      phone: '+998901234567',
      preferredTime: 'afternoon',
      consentGiven: true,
      consentVersion: 'lead-beta-2026-07-10',
      consentLocale: 'ru',
      idempotencyKey: 'c4b18df0-9d1f-4ba6-9fdc-2c4c99041af1',
    );

    expect(adapter.request.path, '/api/leads');
    expect(adapter.request.headers['Authorization'], 'Bearer access-token');
    expect(
      adapter.request.headers['Idempotency-Key'],
      'c4b18df0-9d1f-4ba6-9fdc-2c4c99041af1',
    );
    expect(adapter.request.data, {
      'clinic_id': '4df30f8b-844e-454a-a677-c703a5ad89d2',
      'generation_id': '394553b3-9110-44ec-8f2b-6a8bcf3dc778',
      'name': 'Selena',
      'phone': '+998901234567',
      'preferred_time': 'afternoon',
      'consent_given': true,
      'consent_version': 'lead-beta-2026-07-10',
      'consent_locale': 'ru',
    });
    expect(receipt.id, '57adb7eb-9b14-4cc8-b977-bc7a39b07553');
    expect(receipt.clinicId, '4df30f8b-844e-454a-a677-c703a5ad89d2');
    expect(receipt.status, 'notified');
  });
}

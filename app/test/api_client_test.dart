import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smile_simulator/src/api/api_client.dart';

class _RecordingAdapter implements HttpClientAdapter {
  _RecordingAdapter({required this.body, this.statusCode = 200});

  final Map<String, dynamic> body;
  final int statusCode;
  late RequestOptions request;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    request = options;
    return ResponseBody.fromString(
      jsonEncode(body),
      statusCode,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  test('createPhotoConsent requests a server-issued upload path', () async {
    final adapter = _RecordingAdapter(
      statusCode: 201,
      body: {
        'id': '10000000-0000-0000-0000-000000000001',
        'consent_version': 'photo-beta-2026-07-10',
        'consent_locale': 'ru',
        'consented_at': '2026-07-10T08:00:00Z',
        'upload_path':
            '00000000-0000-0000-0000-000000000001/10000000-0000-0000-0000-000000000001_original',
      },
    );
    final dio = Dio(BaseOptions(baseUrl: 'https://api.example.test/v1'));
    dio.httpClientAdapter = adapter;
    final client = ApiClient(dio: dio);

    final receipt = await client.createPhotoConsent(
      consentGiven: true,
      consentVersion: 'photo-beta-2026-07-10',
      consentLocale: 'ru',
    );

    expect(adapter.request.path, '/api/photo-consents');
    expect(adapter.request.data, {
      'consent_given': true,
      'consent_version': 'photo-beta-2026-07-10',
      'consent_locale': 'ru',
    });
    expect(receipt.id, '10000000-0000-0000-0000-000000000001');
    expect(receipt.consentedAt.toUtc(), DateTime.utc(2026, 7, 10, 8));
  });

  test('startGeneration binds the photo path to its consent receipt', () async {
    final adapter = _RecordingAdapter(
      statusCode: 202,
      body: {
        'id': '20000000-0000-0000-0000-000000000001',
        'status': 'pending',
      },
    );
    final dio = Dio(BaseOptions(baseUrl: 'https://api.example.test/v1'));
    dio.httpClientAdapter = adapter;
    final client = ApiClient(dio: dio);

    await client.startGeneration(
      styleId: '30000000-0000-0000-0000-000000000001',
      photoConsentId: '10000000-0000-0000-0000-000000000001',
      originalPhotoPath:
          '00000000-0000-0000-0000-000000000001/10000000-0000-0000-0000-000000000001_original',
    );

    expect(adapter.request.path, '/api/generate');
    expect(adapter.request.data, {
      'style_id': '30000000-0000-0000-0000-000000000001',
      'photo_consent_id': '10000000-0000-0000-0000-000000000001',
      'original_photo_path':
          '00000000-0000-0000-0000-000000000001/10000000-0000-0000-0000-000000000001_original',
    });
  });

  test('purchase sends idempotency and does not infer local activation', () async {
    final adapter = _RecordingAdapter(
      body: {
        'payment_id': '10000000-0000-0000-0000-000000000001',
        'status': 'pending',
        'payment_url': 'https://yoomoney.ru/checkout/1',
      },
    );
    final dio = Dio(BaseOptions(baseUrl: 'https://api.example.test/v1'));
    dio.httpClientAdapter = adapter;
    final client = ApiClient(dio: dio);

    final receipt = await client.purchase(
      packType: 'mini',
      provider: 'yookassa',
      idempotencyKey: '20000000-0000-0000-0000-000000000001',
    );

    expect(adapter.request.path, '/api/packs/purchase');
    expect(
      adapter.request.headers['Idempotency-Key'],
      '20000000-0000-0000-0000-000000000001',
    );
    expect(adapter.request.data, {
      'pack_type': 'mini',
      'provider': 'yookassa',
    });
    expect(receipt.status, 'pending');
    expect(receipt.isCompleted, isFalse);
    expect(receipt.paymentUrl, 'https://yoomoney.ru/checkout/1');
  });

  test('entitlements and payment status are server authoritative', () async {
    final entitlementAdapter = _RecordingAdapter(
      body: {'free_remaining': 0, 'pack_remaining': 17},
    );
    final entitlementDio = Dio(BaseOptions(baseUrl: 'https://api.example.test/v1'));
    entitlementDio.httpClientAdapter = entitlementAdapter;
    final entitlementClient = ApiClient(dio: entitlementDio);

    final entitlements = await entitlementClient.entitlements();
    expect(entitlements.freeRemaining, 0);
    expect(entitlements.packRemaining, 17);
    expect(entitlementAdapter.request.path, '/api/packs/entitlements');

    final statusAdapter = _RecordingAdapter(
      body: {
        'payment_id': '10000000-0000-0000-0000-000000000001',
        'status': 'completed',
        'pack_id': '30000000-0000-0000-0000-000000000001',
      },
    );
    final statusDio = Dio(BaseOptions(baseUrl: 'https://api.example.test/v1'));
    statusDio.httpClientAdapter = statusAdapter;
    final statusClient = ApiClient(dio: statusDio);

    final status = await statusClient.paymentStatus(
      '10000000-0000-0000-0000-000000000001',
    );
    expect(status.isCompleted, isTrue);
    expect(status.packId, '30000000-0000-0000-0000-000000000001');
    expect(
      statusAdapter.request.path,
      '/api/packs/payments/10000000-0000-0000-0000-000000000001',
    );
  });

  test('submitLead sends consent and a stable idempotency key', () async {
    final adapter = _RecordingAdapter(
      statusCode: 201,
      body: {
        'id': '57adb7eb-9b14-4cc8-b977-bc7a39b07553',
        'clinic_id': '4df30f8b-844e-454a-a677-c703a5ad89d2',
        'status': 'notified',
      },
    );
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

  test('deleteGeneration returns a verified pending receipt', () async {
    final adapter = _RecordingAdapter(
      body: {
        'generation_id': '394553b3-9110-44ec-8f2b-6a8bcf3dc778',
        'status': 'pending',
        'object_count': 3,
      },
    );
    final dio = Dio(BaseOptions(baseUrl: 'https://api.example.test/v1'));
    dio.httpClientAdapter = adapter;
    final client = ApiClient(dio: dio);

    final receipt = await client.deleteGeneration(
      '394553b3-9110-44ec-8f2b-6a8bcf3dc778',
    );

    expect(adapter.request.method, 'DELETE');
    expect(
      adapter.request.path,
      '/api/generate/394553b3-9110-44ec-8f2b-6a8bcf3dc778',
    );
    expect(receipt.isPending, isTrue);
    expect(receipt.objectCount, 3);
  });

  test('deleteAllGenerationPhotos parses partial outcomes', () async {
    final adapter = _RecordingAdapter(
      body: {
        'requested': 4,
        'deleted': 2,
        'pending': 1,
        'failed': 1,
        'objects_requested': 12,
      },
    );
    final dio = Dio(BaseOptions(baseUrl: 'https://api.example.test/v1'));
    dio.httpClientAdapter = adapter;
    final client = ApiClient(dio: dio);

    final summary = await client.deleteAllGenerationPhotos();

    expect(adapter.request.method, 'DELETE');
    expect(adapter.request.path, '/api/generate');
    expect(summary.requested, 4);
    expect(summary.deleted, 2);
    expect(summary.pending, 1);
    expect(summary.failed, 1);
    expect(summary.objectsRequested, 12);
  });
}

import 'package:dio/dio.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../config/env.dart';
import 'models.dart';

/// Typed client for the API gateway. Attaches the Supabase JWT to every request.
///
/// The generative inference API is NEVER called from the client — only these
/// gateway endpoints (CLAUDE.md critical rule).
class ApiClient {
  ApiClient([Dio? dio]) : _dio = dio ?? Dio(BaseOptions(baseUrl: Env.apiBaseUrl)) {
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          final token = Supabase.instance.client.auth.currentSession?.accessToken;
          if (token != null) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          handler.next(options);
        },
      ),
    );
  }

  final Dio _dio;

  // --- Styles ---------------------------------------------------------------
  Future<List<Style>> listStyles() async {
    final resp = await _dio.get('/api/styles');
    return (resp.data as List)
        .map((e) => Style.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  // --- Generation -----------------------------------------------------------
  /// Start a generation. The photo is uploaded directly to Storage first; pass its
  /// object path here (architecture §10.3).
  Future<Generation> startGeneration({
    required String styleId,
    required String originalPhotoPath,
  }) async {
    final resp = await _dio.post('/api/generate', data: {
      'style_id': styleId,
      'original_photo_path': originalPhotoPath,
    });
    return Generation.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<Generation> getGeneration(String id) async {
    final resp = await _dio.get('/api/generate/$id');
    return Generation.fromJson(resp.data as Map<String, dynamic>);
  }

  /// Poll until the generation reaches a terminal state (architecture §4.2).
  Stream<Generation> pollGeneration(
    String id, {
    Duration interval = const Duration(seconds: 2),
    int maxAttempts = 30,
  }) async* {
    for (var i = 0; i < maxAttempts; i++) {
      final gen = await getGeneration(id);
      yield gen;
      if (gen.isTerminal) return;
      await Future<void>.delayed(interval);
    }
  }

  Future<List<Generation>> history() async {
    final resp = await _dio.get('/api/generate/history');
    return (resp.data['items'] as List)
        .map((e) => Generation.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  // --- Packs ----------------------------------------------------------------
  Future<List<PackOption>> availablePacks({String currency = 'RUB'}) async {
    final resp = await _dio.get('/api/packs/available',
        queryParameters: {'currency': currency});
    return (resp.data as List)
        .map((e) => PackOption.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<String?> purchase({required String packType, required String provider}) async {
    final resp = await _dio.post('/api/packs/purchase',
        data: {'pack_type': packType, 'provider': provider});
    return resp.data['payment_url'] as String?;
  }

  // --- Price estimates (cost anchor) ---------------------------------------
  Future<List<PriceEstimate>> priceEstimates({String? city, String? styleId}) async {
    final resp = await _dio.get('/api/price-estimates', queryParameters: {
      if (city != null) 'city': city,
      if (styleId != null) 'style_id': styleId,
    });
    return (resp.data as List)
        .map((e) => PriceEstimate.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  // --- Clinics & leads ------------------------------------------------------
  Future<List<Clinic>> clinics({String? city, double? lat, double? lng}) async {
    final resp = await _dio.get('/api/clinics', queryParameters: {
      if (city != null) 'city': city,
      if (lat != null) 'lat': lat,
      if (lng != null) 'lng': lng,
    });
    return (resp.data as List)
        .map((e) => Clinic.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<void> submitLead({
    required String clinicId,
    required String generationId,
    required String name,
    required String phone,
    String? preferredTime,
  }) async {
    await _dio.post('/api/leads', data: {
      'clinic_id': clinicId,
      'generation_id': generationId,
      'name': name,
      'phone': phone,
      'preferred_time': preferredTime,
    });
  }
}

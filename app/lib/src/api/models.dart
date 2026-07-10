/// DTOs mirroring the API gateway responses (see backend/app/schemas.py).
library;

class Style {
  final String id;
  final String name;
  final String nameRu;
  final String? thumbnailUrl;
  final bool isPremium;

  Style({
    required this.id,
    required this.name,
    required this.nameRu,
    this.thumbnailUrl,
    this.isPremium = false,
  });

  factory Style.fromJson(Map<String, dynamic> j) => Style(
        id: j['id'] as String,
        name: j['name'] as String,
        nameRu: j['name_ru'] as String,
        thumbnailUrl: j['thumbnail_url'] as String?,
        isPremium: j['is_premium'] as bool? ?? false,
      );
}

enum GenerationStatus { pending, processing, completed, failed }

GenerationStatus _statusFrom(String s) =>
    GenerationStatus.values.firstWhere(
      (e) => e.name == s,
      orElse: () => GenerationStatus.pending,
    );

class Generation {
  final String id;
  final GenerationStatus status;
  final String? originalPhotoUrl;
  final String? resultPhotoUrl;
  final bool hasWatermark;
  final double? qualityScore;
  final String? errorMessage;

  Generation({
    required this.id,
    required this.status,
    this.originalPhotoUrl,
    this.resultPhotoUrl,
    this.hasWatermark = false,
    this.qualityScore,
    this.errorMessage,
  });

  bool get isTerminal =>
      status == GenerationStatus.completed || status == GenerationStatus.failed;

  factory Generation.fromJson(Map<String, dynamic> j) => Generation(
        id: j['id'] as String,
        status: _statusFrom(j['status'] as String),
        originalPhotoUrl: j['original_photo_url'] as String?,
        resultPhotoUrl: j['result_photo_url'] as String?,
        hasWatermark: j['has_watermark'] as bool? ?? false,
        qualityScore: (j['quality_score'] as num?)?.toDouble(),
        errorMessage: j['error_message'] as String?,
      );
}

class PackOption {
  final String packType;
  final int generationsTotal;
  final double priceAmount;
  final String priceCurrency;
  final String title;

  PackOption({
    required this.packType,
    required this.generationsTotal,
    required this.priceAmount,
    required this.priceCurrency,
    required this.title,
  });

  factory PackOption.fromJson(Map<String, dynamic> j) => PackOption(
        packType: j['pack_type'] as String,
        generationsTotal: j['generations_total'] as int,
        priceAmount: (j['price_amount'] as num).toDouble(),
        priceCurrency: j['price_currency'] as String,
        title: j['title'] as String,
      );
}

class PriceEstimate {
  final String id;
  final String city;
  final String? styleId;
  final String treatmentLabel;
  final String treatmentLabelRu;
  final double priceMin;
  final double priceMax;
  final String currency;
  final bool isEstimate;

  PriceEstimate({
    required this.id,
    required this.city,
    this.styleId,
    required this.treatmentLabel,
    required this.treatmentLabelRu,
    required this.priceMin,
    required this.priceMax,
    required this.currency,
    this.isEstimate = true,
  });

  factory PriceEstimate.fromJson(Map<String, dynamic> j) => PriceEstimate(
        id: j['id'] as String,
        city: j['city'] as String,
        styleId: j['style_id'] as String?,
        treatmentLabel: j['treatment_label'] as String,
        treatmentLabelRu: j['treatment_label_ru'] as String,
        priceMin: (j['price_min'] as num).toDouble(),
        priceMax: (j['price_max'] as num).toDouble(),
        currency: j['currency'] as String,
        isEstimate: j['is_estimate'] as bool? ?? true,
      );
}

class Clinic {
  final String id;
  final String name;
  final String city;
  final String? address;
  final List<String> specialties;
  final double? distanceKm;

  Clinic({
    required this.id,
    required this.name,
    required this.city,
    this.address,
    this.specialties = const [],
    this.distanceKm,
  });

  factory Clinic.fromJson(Map<String, dynamic> j) => Clinic(
        id: j['id'] as String,
        name: j['name'] as String,
        city: j['city'] as String,
        address: j['address'] as String?,
        specialties:
            (j['specialties'] as List?)?.map((e) => e as String).toList() ?? const [],
        distanceKm: (j['distance_km'] as num?)?.toDouble(),
      );
}

class LeadReceipt {
  final String id;
  final String clinicId;
  final String status;

  LeadReceipt({required this.id, required this.clinicId, required this.status});

  factory LeadReceipt.fromJson(Map<String, dynamic> j) => LeadReceipt(
        id: j['id'] as String,
        clinicId: j['clinic_id'] as String,
        status: j['status'] as String,
      );
}

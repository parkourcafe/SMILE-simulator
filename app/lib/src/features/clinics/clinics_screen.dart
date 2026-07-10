import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../api/models.dart';
import '../../providers/providers.dart';

const _cities = <String, String>{
  'Moscow': 'Москва',
  'SPb': 'Санкт-Петербург',
  'Tashkent': 'Ташкент',
};

const _specialties = <String, String>{
  'veneers': 'Виниры',
  'whitening': 'Отбеливание',
  'implants': 'Имплантация',
  'orthodontics': 'Ортодонтия',
};

/// Lists only active or trial clinics returned by the authenticated API.
class ClinicsScreen extends ConsumerWidget {
  const ClinicsScreen({super.key, required this.generationId});

  final String generationId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final city = ref.watch(selectedCityProvider);
    final clinics = ref.watch(clinicsProvider(city));

    return Scaffold(
      appBar: AppBar(title: const Text('Выберите клинику')),
      body: generationId.isEmpty
          ? const _MissingGeneration()
          : RefreshIndicator(
              onRefresh: () => ref.refresh(clinicsProvider(city).future),
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
                children: [
                  DropdownButtonFormField<String>(
                    initialValue: city,
                    decoration: const InputDecoration(
                      labelText: 'Город',
                      prefixIcon: Icon(Icons.location_city_outlined),
                    ),
                    items: _cities.entries
                        .map(
                          (entry) => DropdownMenuItem(
                            value: entry.key,
                            child: Text(entry.value),
                          ),
                        )
                        .toList(),
                    onChanged: (value) {
                      if (value != null) {
                        ref.read(selectedCityProvider.notifier).state = value;
                      }
                    },
                  ),
                  const SizedBox(height: 20),
                  clinics.when(
                    data: (items) => items.isEmpty
                        ? const _EmptyClinics()
                        : Column(
                            children: [
                              for (final clinic in items) ...[
                                _ClinicCard(
                                  clinic: clinic,
                                  generationId: generationId,
                                ),
                                const SizedBox(height: 10),
                              ],
                            ],
                          ),
                    loading: () => const Padding(
                      padding: EdgeInsets.only(top: 80),
                      child: Center(child: CircularProgressIndicator()),
                    ),
                    error: (_, __) => _ClinicsError(
                      onRetry: () => ref.invalidate(clinicsProvider(city)),
                    ),
                  ),
                ],
              ),
            ),
    );
  }
}

class _ClinicCard extends StatelessWidget {
  const _ClinicCard({required this.clinic, required this.generationId});

  final Clinic clinic;
  final String generationId;

  @override
  Widget build(BuildContext context) {
    final details = clinic.specialties
        .map((value) => _specialties[value] ?? value)
        .join(' · ');
    final leadPath = Uri(
      path: '/lead/${clinic.id}',
      queryParameters: {'generationId': generationId},
    ).toString();

    return Card(
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(clinic.name, style: Theme.of(context).textTheme.titleMedium),
            if (clinic.address != null && clinic.address!.isNotEmpty) ...[
              const SizedBox(height: 6),
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.place_outlined, size: 18),
                  const SizedBox(width: 6),
                  Expanded(child: Text(clinic.address!)),
                ],
              ),
            ],
            if (details.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(details, style: Theme.of(context).textTheme.bodySmall),
            ],
            if (clinic.distanceKm != null) ...[
              const SizedBox(height: 6),
              Text('${clinic.distanceKm!.toStringAsFixed(1)} км'),
            ],
            const SizedBox(height: 14),
            FilledButton.icon(
              icon: const Icon(Icons.send_outlined),
              label: const Text('Выбрать клинику'),
              onPressed: () => context.push(leadPath),
            ),
          ],
        ),
      ),
    );
  }
}

class _MissingGeneration extends StatelessWidget {
  const _MissingGeneration();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.photo_outlined, size: 40),
            const SizedBox(height: 12),
            const Text(
              'Сначала выберите готовую визуализацию.',
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: () => context.go('/history'),
              child: const Text('Открыть историю'),
            ),
          ],
        ),
      ),
    );
  }
}

class _EmptyClinics extends StatelessWidget {
  const _EmptyClinics();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.only(top: 64),
      child: Center(
        child: Text(
          'В этом городе пока нет подтверждённых клиник-партнёров.',
          textAlign: TextAlign.center,
        ),
      ),
    );
  }
}

class _ClinicsError extends StatelessWidget {
  const _ClinicsError({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 64),
      child: Column(
        children: [
          const Text('Не удалось загрузить клиники.'),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            icon: const Icon(Icons.refresh),
            label: const Text('Повторить'),
            onPressed: onRetry,
          ),
        ],
      ),
    );
  }
}

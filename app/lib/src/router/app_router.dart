import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/auth/login_screen.dart';
import '../features/auth/otp_screen.dart';
import '../features/clinics/clinics_screen.dart';
import '../features/generating/generating_screen.dart';
import '../features/history/history_screen.dart';
import '../features/home/home_screen.dart';
import '../features/leads/lead_form_screen.dart';
import '../features/leads/lead_sent_screen.dart';
import '../features/onboarding/onboarding_screen.dart';
import '../features/paywall/paywall_screen.dart';
import '../features/profile/profile_screen.dart';
import '../features/result/result_screen.dart';
import '../features/splash/splash_screen.dart';
import '../features/styles/styles_screen.dart';
import '../features/upload/preview_screen.dart';
import '../features/upload/upload_screen.dart';
import '../providers/providers.dart';

/// All 16 routes (CLAUDE.md → Screen Map).
final appRouterProvider = Provider<GoRouter>((ref) {
  final auth = ref.read(authServiceProvider);
  final router = GoRouter(
    initialLocation: '/',
    refreshListenable: auth,
    redirect: (_, state) {
      final path = state.matchedLocation;
      final protected = const [
        '/home',
        '/upload',
        '/preview',
        '/styles',
        '/generating',
        '/result',
        '/paywall',
        '/clinics',
        '/lead',
        '/history',
        '/profile',
      ].any((prefix) => path == prefix || path.startsWith('$prefix/'));
      if (!auth.isSignedIn && protected) return '/login';
      if (auth.isSignedIn && {'/onboarding', '/login', '/verify'}.contains(path)) {
        return '/home';
      }
      return null;
    },
    routes: [
      GoRoute(path: '/', builder: (_, __) => const SplashScreen()),
      GoRoute(path: '/onboarding', builder: (_, __) => const OnboardingScreen()),
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      GoRoute(path: '/verify', builder: (_, __) => const OtpScreen()),
      GoRoute(path: '/home', builder: (_, __) => const HomeScreen()),
      GoRoute(path: '/upload', builder: (_, __) => const UploadScreen()),
      GoRoute(path: '/preview', builder: (_, __) => const PreviewScreen()),
      GoRoute(path: '/styles', builder: (_, __) => const StylesScreen()),
      GoRoute(path: '/generating', builder: (_, __) => const GeneratingScreen()),
      GoRoute(
        path: '/result/:id',
        builder: (_, s) => ResultScreen(generationId: s.pathParameters['id']!),
      ),
      GoRoute(path: '/paywall', builder: (_, __) => const PaywallScreen()),
      GoRoute(path: '/clinics', builder: (_, __) => const ClinicsScreen()),
      GoRoute(
        path: '/lead/:clinicId',
        builder: (_, s) => LeadFormScreen(clinicId: s.pathParameters['clinicId']!),
      ),
      GoRoute(path: '/lead/sent', builder: (_, __) => const LeadSentScreen()),
      GoRoute(path: '/history', builder: (_, __) => const HistoryScreen()),
      GoRoute(path: '/profile', builder: (_, __) => const ProfileScreen()),
    ],
    errorBuilder: (_, state) => Scaffold(
      body: Center(child: Text('Route not found: ${state.uri}')),
    ),
  );
  ref.onDispose(router.dispose);
  return router;
});

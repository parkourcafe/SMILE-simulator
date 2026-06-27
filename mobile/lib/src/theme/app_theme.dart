import 'package:flutter/material.dart';

/// App theme. Clean, trustworthy, "dental" palette (whites + a fresh teal accent).
class AppTheme {
  static const Color _seed = Color(0xFF00BFA6);

  static ThemeData get light => ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(seedColor: _seed),
        scaffoldBackgroundColor: const Color(0xFFFAFCFC),
        appBarTheme: const AppBarTheme(centerTitle: true, elevation: 0),
        filledButtonTheme: FilledButtonThemeData(
          style: FilledButton.styleFrom(
            minimumSize: const Size.fromHeight(52),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(14),
            ),
          ),
        ),
      );
}

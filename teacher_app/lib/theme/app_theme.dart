import 'package:flutter/material.dart';

import 'app_colors.dart';

abstract final class AppTheme {
  static const fontFamily = 'Poppins';

  static ThemeData light({required bool highContrast, required double textScale}) {
    final scheme = highContrast
        ? const ColorScheme.dark(
            primary: AppColors.highContrastAccent,
            onPrimary: Colors.black,
            secondary: AppColors.highContrastAccent,
            onSecondary: Colors.black,
            surface: AppColors.highContrastBg,
            onSurface: AppColors.highContrastFg,
            error: Color(0xFFFF6B6B),
            onError: Colors.black,
          )
        : const ColorScheme.light(
            primary: AppColors.brandDark,
            onPrimary: Colors.white,
            secondary: AppColors.sky,
            onSecondary: Colors.white,
            surface: AppColors.surface,
            onSurface: AppColors.ink,
            error: Color(0xFFB42318),
            onError: Colors.white,
          );

    final base = ThemeData(
      useMaterial3: true,
      fontFamily: highContrast ? null : fontFamily,
      colorScheme: scheme,
      scaffoldBackgroundColor: highContrast ? AppColors.highContrastBg : AppColors.cream,
      splashFactory: InkRipple.splashFactory,
      visualDensity: VisualDensity.standard,
      appBarTheme: AppBarTheme(
        elevation: 0,
        scrolledUnderElevation: 0,
        backgroundColor: highContrast ? AppColors.highContrastBg : AppColors.cream,
        foregroundColor: highContrast ? AppColors.highContrastFg : AppColors.ink,
        centerTitle: false,
        titleTextStyle: TextStyle(
          fontFamily: fontFamily,
          fontSize: 20 * textScale,
          fontWeight: FontWeight.w700,
          color: highContrast ? AppColors.highContrastFg : AppColors.ink,
        ),
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        color: highContrast ? AppColors.highContrastSoft : AppColors.surface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: BorderSide(
            color: highContrast ? AppColors.highContrastAccent : AppColors.line,
            width: highContrast ? 2 : 1,
          ),
        ),
        margin: EdgeInsets.zero,
      ),
      navigationBarTheme: NavigationBarThemeData(
        elevation: 0,
        height: 72,
        backgroundColor: highContrast ? AppColors.highContrastSoft : AppColors.navy,
        indicatorColor: highContrast ? AppColors.highContrastAccent : AppColors.brand.withValues(alpha: 0.22),
        iconTheme: WidgetStateProperty.resolveWith((states) {
          final selected = states.contains(WidgetState.selected);
          return IconThemeData(
            color: highContrast
                ? AppColors.highContrastAccent
                : (selected ? AppColors.brand : Colors.white70),
          );
        }),
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          final selected = states.contains(WidgetState.selected);
          return TextStyle(
            fontFamily: fontFamily,
            fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
            fontSize: 12 * textScale,
            color: highContrast
                ? AppColors.highContrastFg
                : (selected ? AppColors.brand : Colors.white70),
          );
        }),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size(48, 56),
          backgroundColor: highContrast ? AppColors.highContrastAccent : AppColors.brandDark,
          foregroundColor: highContrast ? Colors.black : Colors.white,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          textStyle: TextStyle(
            fontFamily: fontFamily,
            fontWeight: FontWeight.w700,
            fontSize: 16 * textScale,
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          minimumSize: const Size(48, 52),
          foregroundColor: highContrast ? AppColors.highContrastAccent : AppColors.brandDark,
          side: BorderSide(
            color: highContrast ? AppColors.highContrastAccent : AppColors.brandDark,
            width: 2,
          ),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          textStyle: TextStyle(
            fontFamily: fontFamily,
            fontWeight: FontWeight.w700,
            fontSize: 15 * textScale,
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: highContrast ? AppColors.highContrastSoft : AppColors.surface,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(color: highContrast ? AppColors.highContrastAccent : AppColors.line),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(color: highContrast ? AppColors.highContrastAccent : AppColors.line),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(
            color: highContrast ? AppColors.highContrastAccent : AppColors.brandDark,
            width: 2,
          ),
        ),
      ),
      dividerColor: highContrast ? AppColors.highContrastAccent.withValues(alpha: 0.4) : AppColors.line,
    );

    return base.copyWith(
      textTheme: _textTheme(base.textTheme, highContrast, textScale),
    );
  }

  static TextTheme _textTheme(TextTheme base, bool highContrast, double scale) {
    final color = highContrast ? AppColors.highContrastFg : AppColors.ink;
    TextStyle s(double size, FontWeight weight) => TextStyle(
          fontFamily: fontFamily,
          fontSize: size * scale,
          fontWeight: weight,
          color: color,
          height: 1.25,
        );
    return base.copyWith(
      displaySmall: s(28, FontWeight.w700),
      headlineMedium: s(24, FontWeight.w700),
      headlineSmall: s(20, FontWeight.w600),
      titleLarge: s(18, FontWeight.w600),
      titleMedium: s(16, FontWeight.w600),
      titleSmall: s(14, FontWeight.w500),
      bodyLarge: s(16, FontWeight.w400),
      bodyMedium: s(15, FontWeight.w400),
      bodySmall: s(13, FontWeight.w400),
      labelLarge: s(14, FontWeight.w600),
    );
  }
}

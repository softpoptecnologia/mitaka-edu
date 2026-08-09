import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:provider/provider.dart';

import 'screens/login_screen.dart';
import 'screens/shell_screen.dart';
import 'services/teacher_api.dart';
import 'state/app_state.dart';
import 'theme/app_theme.dart';

class MitakaTeacherApp extends StatelessWidget {
  const MitakaTeacherApp({super.key, this.api});

  final TeacherApi? api;

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => AppState(api: api)..loadPrefs(),
      child: Consumer<AppState>(
        builder: (context, state, _) {
          final textScale = state.settings.forceLargeText ? 1.22 : 1.0;
          return MaterialApp(
            title: 'Mitaka Edu',
            debugShowCheckedModeBanner: false,
            locale: const Locale('pt', 'BR'),
            supportedLocales: const [Locale('pt', 'BR')],
            localizationsDelegates: const [
              GlobalMaterialLocalizations.delegate,
              GlobalWidgetsLocalizations.delegate,
              GlobalCupertinoLocalizations.delegate,
            ],
            theme: AppTheme.light(
              highContrast: state.settings.forceHighContrast,
              textScale: textScale,
            ),
            home: state.isLoggedIn ? const ShellScreen() : const LoginScreen(),
          );
        },
      ),
    );
  }
}

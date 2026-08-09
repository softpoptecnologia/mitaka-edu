import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mitaka_teacher/app.dart';
import 'package:mitaka_teacher/services/teacher_api.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('tela de login aparece', (tester) async {
    await tester.pumpWidget(MitakaTeacherApp(api: DemoTeacherApi()));
    expect(find.text('Mitaka Edu'), findsOneWidget);
    expect(find.text('Evidências que transformam aprendizagens.'), findsOneWidget);
    expect(find.text('Entrar'), findsWidgets);
    expect(find.text('Acesso da professora. AEE, gestão e família usam o site.'), findsOneWidget);
    expect(find.text('Servidor'), findsWidgets);
    expect(find.text('Web'), findsOneWidget);
    expect(find.text('Local'), findsOneWidget);
  });

  testWidgets('hoje mostra o que fazer depois do login', (tester) async {
    await tester.pumpWidget(MitakaTeacherApp(api: DemoTeacherApi()));
    final entrar = find.widgetWithText(FilledButton, 'Entrar');
    await tester.ensureVisible(entrar);
    await tester.pumpAndSettle();
    await tester.tap(entrar);
    await tester.pumpAndSettle();
    expect(find.textContaining('Olá'), findsWidgets);
    expect(find.text('Comece por aqui'), findsOneWidget);
    expect(find.text('Hoje'), findsWidgets);
    expect(find.text('Sondagem pendente'), findsWidgets);
  });
}

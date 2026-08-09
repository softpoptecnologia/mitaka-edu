import 'package:flutter_test/flutter_test.dart';
import 'package:mitaka_teacher/app.dart';

void main() {
  testWidgets('tela de login aparece', (tester) async {
    await tester.pumpWidget(const MitakaTeacherApp());
    expect(find.text('Mitaka Atividades'), findsOneWidget);
    expect(find.text('Entrar'), findsOneWidget);
  });
}

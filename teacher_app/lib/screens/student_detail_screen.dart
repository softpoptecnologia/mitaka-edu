import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../state/app_state.dart';
import '../theme/app_colors.dart';
import '../widgets/common.dart';
import 'activity_catalog_screen.dart';
import 'activity_prepare_screen.dart';

class StudentDetailScreen extends StatelessWidget {
  const StudentDetailScreen({super.key, required this.studentId});

  final String studentId;

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final student = state.studentById(studentId);
    if (student == null) {
      return const Scaffold(body: Center(child: Text('Estudante não encontrado')));
    }
    final room = state.classroomById(student.classroomId);
    return Scaffold(
      appBar: AppBar(title: Text(student.fullName)),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 24),
        children: [
          Text('Como esta criança está agora?', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 10),
          SectionCard(
            child: Row(
              children: [
                StudentAvatar(student: student, size: 64),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(student.fullName, style: Theme.of(context).textTheme.titleLarge),
                      Text(
                        '${room?.name ?? ''} · ${room?.schoolName ?? ''}',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.muted),
                      ),
                      const SizedBox(height: 8),
                      StatusChip(status: student.status),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Text('Recursos necessários', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Text(
            'O app aplica estes apoios na atividade. Não é diagnóstico.',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.muted),
          ),
          const SizedBox(height: 12),
          if (!student.hasSupport)
            SectionCard(
              child: Text(
                'Nenhum apoio extra cadastrado. A atividade já é só toque, sem cronômetro.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            )
          else
            SectionCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (student.supportNotes.isNotEmpty) ...[
                    Text(student.supportNotes, style: Theme.of(context).textTheme.bodyMedium),
                    const SizedBox(height: 12),
                  ],
                  for (final code in student.features) ...[
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Icon(Icons.check_circle_rounded, color: AppColors.ok, size: 22),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(AccessibilityFeature.byCode(code).label, style: Theme.of(context).textTheme.titleSmall),
                              Text(
                                AccessibilityFeature.byCode(code).hint,
                                style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.muted),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                  ],
                ],
              ),
            ),
          const SizedBox(height: 20),
          FilledButton.icon(
            onPressed: () {
              final activity = state.suggestedActivityFor(student);
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => ActivityPrepareScreen(
                    activityId: activity.id,
                    preselectedStudentId: student.id,
                    initialMode: student.status == StudentStatus.pending
                        ? ActivityMode.survey
                        : ActivityMode.practice,
                  ),
                ),
              );
            },
            icon: const Icon(Icons.play_arrow_rounded),
            label: const Text('Iniciar com esta criança'),
          ),
          const SizedBox(height: 10),
          OutlinedButton(
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => ActivityCatalogScreen(standalone: true, preselectedStudentId: student.id),
              ),
            ),
            child: const Text('Escolher outro jogo'),
          ),
        ],
      ),
    );
  }
}

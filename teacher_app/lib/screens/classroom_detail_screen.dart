import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../state/app_state.dart';
import '../theme/app_colors.dart';
import '../widgets/common.dart';
import 'activity_prepare_screen.dart';
import 'student_detail_screen.dart';

class ClassroomDetailScreen extends StatelessWidget {
  const ClassroomDetailScreen({super.key, required this.classroomId});

  final String classroomId;

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final room = state.classroomById(classroomId);
    if (room == null) {
      return const Scaffold(body: Center(child: Text('Turma não encontrada')));
    }
    return Scaffold(
      appBar: AppBar(title: Text(room.name)),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 24),
        children: [
          Text(room.schoolName, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.muted)),
          const SizedBox(height: 8),
          Text(
            '${room.pendingCount} ainda sem sondagem · ${room.attentionCount} para observar de novo',
            style: Theme.of(context).textTheme.titleSmall,
          ),
          const SizedBox(height: 16),
          for (final student in room.students) ...[
            SectionCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  InkWell(
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => StudentDetailScreen(studentId: student.id)),
                    ),
                    child: Row(
                      children: [
                        StudentAvatar(student: student, size: 52),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(student.fullName, style: Theme.of(context).textTheme.titleMedium),
                              const SizedBox(height: 6),
                              Wrap(
                                spacing: 6,
                                runSpacing: 6,
                                children: [
                                  StatusChip(status: student.status),
                                  for (final code in student.features.take(2))
                                    ResourceChip(label: AccessibilityFeature.byCode(code).label, compact: true),
                                ],
                              ),
                            ],
                          ),
                        ),
                        const Icon(Icons.chevron_right_rounded, color: AppColors.muted),
                      ],
                    ),
                  ),
                  if (student.status != StudentStatus.ok) ...[
                    const SizedBox(height: 12),
                    FilledButton.tonalIcon(
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
                      label: Text(
                        student.status == StudentStatus.pending ? 'Iniciar sondagem' : 'Observar de novo',
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 10),
          ],
        ],
      ),
    );
  }
}

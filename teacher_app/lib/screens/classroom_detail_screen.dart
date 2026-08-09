import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../state/app_state.dart';
import '../theme/app_colors.dart';
import '../widgets/common.dart';
import 'student_detail_screen.dart';

class ClassroomDetailScreen extends StatelessWidget {
  const ClassroomDetailScreen({super.key, required this.classroomId});

  final String classroomId;

  @override
  Widget build(BuildContext context) {
    final room = context.watch<AppState>().classroomById(classroomId);
    if (room == null) {
      return const Scaffold(body: Center(child: Text('Turma não encontrada')));
    }
    return Scaffold(
      appBar: AppBar(title: Text(room.name)),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 24),
        children: [
          Text(room.schoolName, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.muted)),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              ResourceChip(label: '${room.okCount} regular'),
              ResourceChip(label: '${room.pendingCount} pendente'),
              ResourceChip(label: '${room.attentionCount} atenção'),
              ResourceChip(label: '${room.supportCount} com recursos'),
            ],
          ),
          const SizedBox(height: 16),
          for (final student in room.students) ...[
            InkWell(
              borderRadius: BorderRadius.circular(20),
              onTap: () => Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => StudentDetailScreen(studentId: student.id)),
              ),
              child: SectionCard(
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
                              for (final code in student.features.take(3))
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
            ),
            const SizedBox(height: 10),
          ],
        ],
      ),
    );
  }
}

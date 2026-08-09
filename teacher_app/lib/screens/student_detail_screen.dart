import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../state/app_state.dart';
import '../theme/app_colors.dart';
import '../widgets/common.dart';
import 'activity_catalog_screen.dart';

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
            'O app aplica estes recursos automaticamente na atividade. Não são diagnóstico.',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.muted),
          ),
          const SizedBox(height: 12),
          if (!student.hasSupport)
            SectionCard(
              child: Text(
                'Nenhum recurso específico cadastrado. A atividade já evita arrastar e não usa cronômetro.',
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
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => ActivityCatalogScreen(standalone: true, preselectedStudentId: student.id),
              ),
            ),
            icon: const Icon(Icons.extension_rounded),
            label: const Text('Iniciar atividade com este aluno'),
          ),
        ],
      ),
    );
  }
}

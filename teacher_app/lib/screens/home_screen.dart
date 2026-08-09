import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import '../theme/app_colors.dart';
import '../widgets/common.dart';
import 'activity_catalog_screen.dart';
import 'classroom_detail_screen.dart';
import 'student_detail_screen.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final name = state.user?.displayName.split(' ').first ?? 'professora';
    return SafeArea(
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
        children: [
          Text('Olá, $name', style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 4),
          Text(
            'Escolha uma turma ou comece uma atividade lúdica.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.muted),
          ),
          const SizedBox(height: 20),
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 1.15,
            children: [
              StatCard(
                label: 'Estudantes',
                value: '${state.studentCount}',
                icon: Icons.people_alt_rounded,
                color: AppColors.brand,
                soft: AppColors.brandSoft,
              ),
              StatCard(
                label: 'Regular',
                value: '${state.okCount}',
                icon: Icons.sentiment_satisfied_alt_rounded,
                color: AppColors.ok,
                soft: AppColors.okSoft,
              ),
              StatCard(
                label: 'Sondagem pendente',
                value: '${state.pendingCount}',
                icon: Icons.hourglass_bottom_rounded,
                color: AppColors.pending,
                soft: AppColors.pendingSoft,
              ),
              StatCard(
                label: 'Atenção',
                value: '${state.attentionCount}',
                icon: Icons.flag_rounded,
                color: AppColors.attention,
                soft: AppColors.attentionSoft,
              ),
            ],
          ),
          const SizedBox(height: 20),
          FilledButton.icon(
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const ActivityCatalogScreen(standalone: true)),
            ),
            icon: const Icon(Icons.play_arrow_rounded),
            label: const Text('Começar atividade'),
          ),
          const SizedBox(height: 20),
          Text('Minhas turmas', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 10),
          for (final room in state.classrooms) ...[
            InkWell(
              borderRadius: BorderRadius.circular(20),
              onTap: () => Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => ClassroomDetailScreen(classroomId: room.id)),
              ),
              child: SectionCard(
                child: Row(
                  children: [
                    Container(
                      width: 48,
                      height: 48,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: AppColors.brandSoft,
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: const Icon(Icons.school_rounded, color: AppColors.brand),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(room.name, style: Theme.of(context).textTheme.titleMedium),
                          Text(
                            '${room.schoolName} · ${room.students.length} estudantes',
                            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.muted),
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
          if (state.attentionStudents.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text('Estudantes em atenção', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 10),
            SectionCard(
              padding: EdgeInsets.zero,
              child: Column(
                children: [
                  for (final student in state.attentionStudents)
                    ListTile(
                      leading: StudentAvatar(student: student),
                      title: Text(student.fullName),
                      subtitle: Text(
                        state.classroomById(student.classroomId)?.name ?? '',
                        style: const TextStyle(color: AppColors.muted),
                      ),
                      trailing: const Icon(Icons.chevron_right_rounded),
                      onTap: () => Navigator.push(
                        context,
                        MaterialPageRoute(builder: (_) => StudentDetailScreen(studentId: student.id)),
                      ),
                    ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}
